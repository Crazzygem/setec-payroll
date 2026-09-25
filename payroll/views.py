from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import PayslipExtrasForm, RunCreateForm
from .models import PayrollRun, Payslip
from .services import apply_payslip_math, generate_run


def _render_run_list(request, *, form=None, modal=None, status=200):
    runs = PayrollRun.objects.annotate(
        headcount=Count('payslips'),
        gross_total=Sum('payslips__gross'),
        tax_total=Sum('payslips__salary_tax'),
        net_total=Sum('payslips__net'),
    )
    return render(
        request,
        'payroll/run_list.html',
        {'runs': runs, 'form': form or RunCreateForm(), 'modal': modal},
        status=status,
    )


@login_required
def run_list(request):
    if request.GET.get('new'):
        return _render_run_list(request, modal='new')
    return _render_run_list(request)


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
                request, f'{run.period_label} payroll generated — {count} payslips.'
            )
        else:
            messages.error(request, f'{run.period_label} payroll already exists.')
        return redirect('payroll:run_detail', pk=run.pk)
    return _render_run_list(request, form=form, modal='new', status=200)


@login_required
def run_detail(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk)
    slips = run.payslips.select_related('employee')
    totals = slips.aggregate(
        gross=Sum('gross'),
        nssf_employee=Sum('nssf_employee'),
        tax=Sum('salary_tax'),
        net=Sum('net'),
        nssf_employer=Sum('nssf_employer'),
    )

    # Optional "edit extras" modal for one payslip (draft runs only)
    edit_form, target = None, None
    edit_pk = request.GET.get('edit')
    if edit_pk and run.is_draft:
        target = slips.filter(pk=edit_pk).first()
        if target:
            edit_form = PayslipExtrasForm(instance=target)

    return render(
        request,
        'payroll/run_detail.html',
        {
            'run': run,
            'slips': slips,
            'totals': totals,
            'edit_form': edit_form,
            'target': target,
        },
    )


@require_POST
def payslip_update(request, payslip_pk):
    payslip = get_object_or_404(Payslip, pk=payslip_pk)
    if not payslip.run.is_draft:
        messages.error(request, 'This run is finalized — payslips are locked.')
        return redirect('payroll:run_detail', pk=payslip.run_id)
    form = PayslipExtrasForm(request.POST, instance=payslip)
    if form.is_valid():
        slip = form.save(commit=False)
        apply_payslip_math(slip)
        slip.save()
        messages.success(request, f'Payslip for {slip.employee.emp_id} recalculated.')
    else:
        messages.error(request, 'Could not update payslip — check the values.')
    return redirect('payroll:run_detail', pk=payslip.run_id)


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
def payslip_view(request, payslip_pk):
    """Standalone printable payslip (no sidebar — clean A4 print)."""
    payslip = get_object_or_404(
        Payslip.objects.select_related('employee', 'run'), pk=payslip_pk
    )
    return render(request, 'payroll/payslip.html', {'slip': payslip})
