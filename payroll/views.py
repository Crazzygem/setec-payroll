from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import exports
from .forms import ExtrasFormSet, PayslipExtrasForm, RunCreateForm
from .models import PayrollRun, Payslip
from .services import apply_payslip_math, generate_run, next_period, regenerate_run


def _render_run_list(request, *, form=None, modal=None, status=200):
    runs = PayrollRun.objects.annotate(
        headcount=Count('payslips'),
        gross_total=Sum('payslips__gross'),
        tax_total=Sum('payslips__salary_tax'),
        net_total=Sum('payslips__net'),
    ).order_by('-year', '-month')  # Meta.ordering is dropped on aggregate queries
    if form is None:
        year, month = next_period()
        form = RunCreateForm(initial={'year': year, 'month': str(month)})
    return render(
        request,
        'payroll/run_list.html',
        {'runs': runs, 'form': form, 'modal': modal},
        status=status,
    )


@login_required
def run_list(request):
    if request.GET.get('new'):
        return _render_run_list(request, modal='new')
    return _render_run_list(request)


@login_required
@require_POST
def run_create(request):
    form = RunCreateForm(request.POST)
    if form.is_valid():
        year = form.cleaned_data['year']
        month = int(form.cleaned_data['month'])
        run, created = generate_run(year, month)
        if created:
            count = run.payslips.count()
            messages.success(
                request, f'{run.period_label} payroll generated: {count} payslips.'
            )
        else:
            messages.error(request, f'{run.period_label} payroll already exists.')
        return redirect('payroll:run_detail', pk=run.pk)
    return _render_run_list(request, form=form, modal='new', status=200)


RUN_MODALS = ('finalize', 'regenerate', 'delete')


def _render_run_detail(request, run, *, formset=None, modal=None, status=200):
    slips = run.payslips.select_related('employee', 'employee__position')
    totals = slips.aggregate(
        gross=Sum('gross'),
        overtime=Sum('overtime'),
        bonus=Sum('bonus'),
        advances=Sum('advances'),
        nssf_employee=Sum('nssf_employee'),
        tax=Sum('salary_tax'),
        net=Sum('net'),
        nssf_employer=Sum('nssf_employer'),
    )
    if run.is_draft:
        formset = formset or ExtrasFormSet(queryset=slips)
        forms_by_pk = {f.instance.pk: f for f in formset.forms}
        rows = [(slip, forms_by_pk.get(slip.pk)) for slip in slips]
    else:
        rows = [(slip, None) for slip in slips]
    return render(
        request,
        'payroll/run_detail.html',
        {
            'run': run, 'slips': slips, 'rows': rows, 'totals': totals,
            'formset': formset, 'modal': modal,
        },
        status=status,
    )


@login_required
def run_detail(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk)
    modal = next((m for m in RUN_MODALS if request.GET.get(m)), None)
    if modal and not run.is_draft:
        modal = None
    return _render_run_detail(request, run, modal=modal)


@login_required
@require_POST
def run_extras_update(request, pk):
    """Save overtime/bonus/advances for every changed payslip in one POST."""
    run = get_object_or_404(PayrollRun, pk=pk)
    if not run.is_draft:
        messages.error(request, 'This run is finalized. Payslips are locked.')
        return redirect('payroll:run_detail', pk=run.pk)
    formset = ExtrasFormSet(request.POST, queryset=run.payslips.all())
    if not formset.is_valid():
        messages.error(request, 'Some values are invalid. Fix the highlighted cells.')
        return _render_run_detail(request, run, formset=formset, status=200)
    with transaction.atomic():
        changed = formset.save(commit=False)
        for slip in changed:
            apply_payslip_math(slip)
            slip.save()
    if changed:
        messages.success(
            request, f'{len(changed)} payslip(s) recalculated for {run.period_label}.'
        )
    else:
        messages.info(request, 'No values changed.')
    return redirect('payroll:run_detail', pk=run.pk)


@login_required
@require_POST
def run_regenerate(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk)
    if not run.is_draft:
        messages.error(request, f'{run.period_label} is finalized and cannot be regenerated.')
        return redirect('payroll:run_detail', pk=run.pk)
    result = regenerate_run(run)
    messages.success(
        request,
        f'{run.period_label} regenerated: {result["updated"]} updated, '
        f'{result["added"]} added, {result["removed"]} removed. '
        'Overtime, bonus and advances were kept.',
    )
    return redirect('payroll:run_detail', pk=run.pk)


@login_required
@require_POST
def run_delete(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk)
    if not run.is_draft:
        messages.error(request, f'{run.period_label} is finalized and cannot be deleted.')
        return redirect('payroll:run_detail', pk=run.pk)
    label = run.period_label
    run.delete()
    messages.success(request, f'{label} draft deleted.')
    return redirect('payroll:run_list')


@login_required
@require_POST
def payslip_update(request, payslip_pk):
    payslip = get_object_or_404(Payslip, pk=payslip_pk)
    if not payslip.run.is_draft:
        messages.error(request, 'This run is finalized. Payslips are locked.')
        return redirect('payroll:run_detail', pk=payslip.run_id)
    form = PayslipExtrasForm(request.POST, instance=payslip)
    if form.is_valid():
        slip = form.save(commit=False)
        apply_payslip_math(slip)
        slip.save()
        messages.success(request, f'Payslip for {slip.employee.emp_id} recalculated.')
    else:
        messages.error(request, 'Could not update payslip, check the values.')
    return redirect('payroll:run_detail', pk=payslip.run_id)


@login_required
@require_POST
def run_finalize(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk)
    if not run.is_draft:
        messages.error(request, f'{run.period_label} is already finalized.')
        return redirect('payroll:run_detail', pk=run.pk)
    run.status = PayrollRun.STATUS_FINALIZED
    run.finalized_at = timezone.now()
    run.save(update_fields=['status', 'finalized_at'])
    due = run.gdt_due_date.strftime('%d %b %Y')
    messages.success(
        request,
        f'{run.period_label} payroll finalized. Withheld salary tax must be '
        f'paid to GDT by {due}.',
    )
    return redirect('payroll:run_detail', pk=run.pk)


@login_required
def export_csv(request, pk):
    """Download the run as CSV (UTF-8 BOM so Excel opens it cleanly)."""
    run = get_object_or_404(PayrollRun, pk=pk)
    data = exports.run_csv(run).encode("utf-8-sig")
    response = HttpResponse(data, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="payroll_{run.year}-{run.month:02d}.csv"'
    )
    return response


@login_required
def export_xlsx(request, pk):
    """Download the run as a formatted Excel workbook."""
    run = get_object_or_404(PayrollRun, pk=pk)
    data = exports.run_xlsx(run)
    response = HttpResponse(
        data,
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = (
        f'attachment; filename="payroll_{run.year}-{run.month:02d}.xlsx"'
    )
    return response


@login_required
def payslip_view(request, payslip_pk):
    """Standalone printable payslip (no sidebar, clean A4 print).

    `?edit=1` opens the inline extras panel (draft runs only).
    """
    payslip = get_object_or_404(
        Payslip.objects.select_related('employee', 'run'), pk=payslip_pk
    )
    edit_form = None
    if request.GET.get('edit') and payslip.run.is_draft:
        edit_form = PayslipExtrasForm(instance=payslip)
    siblings = list(
        payslip.run.payslips.order_by('employee__emp_id')
        .values_list('pk', 'employee__emp_id')
    )
    index = next(i for i, (pk, _) in enumerate(siblings) if pk == payslip.pk)
    prev_slip = siblings[index - 1] if index > 0 else None
    next_slip = siblings[index + 1] if index + 1 < len(siblings) else None
    return render(
        request,
        'payroll/payslip.html',
        {
            'slip': payslip, 'edit_form': edit_form,
            'prev_slip': prev_slip, 'next_slip': next_slip,
            'position': index + 1, 'count': len(siblings),
        },
    )
