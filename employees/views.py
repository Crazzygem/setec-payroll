from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import DepartmentForm, EmployeeForm, PositionForm
from payroll.models import PayrollRun

from .models import Department, Employee, Position


def _parse_pk(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _render_list(request, *, modal=None, form=None, target=None, status=200):
    """Render the employee list. `modal` decides which modal is open:
    'new' | 'edit' | 'delete' | None (server-driven, no JS state)."""
    q = request.GET.get('q', '').strip()
    employees = Employee.objects.all()
    if q:
        employees = employees.filter(
            Q(emp_id__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(position__name__icontains=q)
            | Q(department__name__icontains=q)
        )
    return render(
        request,
        'employees/list.html',
        {
            'employees': employees,
            'q': q,
            'modal': modal,
            'form': form or EmployeeForm(),
            'target': target,
        },
        status=status,
    )


@login_required
def employee_list(request):
    new = request.GET.get('new')
    edit = request.GET.get('edit')
    delete = request.GET.get('delete')

    if new:
        return _render_list(request, modal='new')
    if edit:
        pk = _parse_pk(edit)
        target = get_object_or_404(Employee, pk=pk) if pk else None
        if target:
            return _render_list(
                request, modal='edit', form=EmployeeForm(instance=target), target=target
            )
    if delete:
        pk = _parse_pk(delete)
        target = get_object_or_404(Employee, pk=pk) if pk else None
        if target:
            return _render_list(request, modal='delete', target=target)
    return _render_list(request)


@login_required
@require_POST
def employee_create(request):
    form = EmployeeForm(request.POST)
    if form.is_valid():
        employee = form.save()
        messages.success(request, f'Employee {employee.emp_id} added.')
        return redirect('employees:list')
    return _render_list(request, modal='new', form=form, status=200)


@login_required
def employee_edit(request, pk):
    target = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=target)
        if form.is_valid():
            employee = form.save()
            messages.success(request, f'Employee {employee.emp_id} updated.')
            return redirect('employees:list')
        return _render_list(request, modal='edit', form=form, target=target, status=200)
    return redirect('employees:list')


@login_required
@require_POST
def employee_delete(request, pk):
    target = get_object_or_404(Employee, pk=pk)
    emp_id = target.emp_id
    target.delete()
    messages.success(request, f'Employee {emp_id} deleted.')
    return redirect('employees:list')


SORTS = {
    'name': 'name',
    'members': '-count',
    'gross': '-gross_total',
    'net': '-net_total',
}


def _latest_run():
    return PayrollRun.objects.first()  # ordered newest period first


def _org_items(model, group_field, run, q='', sort='name'):
    """Departments/positions with member counts and the latest run's cost.

    `gross_total`/`net_total` come from one real run, so the template labels the
    period instead of implying all-time totals.
    """
    qs = model.objects.annotate(count=Count('employees', distinct=True))
    if q:
        qs = qs.filter(name__icontains=q)
    if run:
        qs = qs.annotate(
            gross_total=Sum(
                'employees__payslips__gross',
                filter=Q(employees__payslips__run=run),
            ),
            net_total=Sum(
                'employees__payslips__net',
                filter=Q(employees__payslips__run=run),
            ),
        ).order_by(SORTS.get(sort, 'name'), 'name')
    else:
        qs = qs.order_by(SORTS.get(sort, 'name'), 'name')
    return qs


def _org_render(request, template, model, form, group_field, modal=None, target=None,
                status=200, q='', sort='name'):
    run = _latest_run()
    items = _org_items(model, group_field, run, q, sort)
    members = []
    if target is not None and modal == 'edit':
        members = list(
            target.employees.select_related('position', 'department').order_by('emp_id')
        )
    return render(
        request,
        template,
        {
            'items': items,
            'form': form,
            'modal': modal,
            'target': target,
            'run': run,
            'q': q,
            'sort': sort,
            'members': members,
            'group_field': group_field,
        },
        status=status,
    )


def _org_list_view(request, model, form, template, group_field):
    modal = target = None
    if request.GET.get('new'):
        modal = 'new'
    edit_pk = _parse_pk(request.GET.get('edit'))
    delete_pk = _parse_pk(request.GET.get('delete'))
    if edit_pk:
        target = get_object_or_404(model, pk=edit_pk)
        modal = 'edit'
        form = form.__class__(instance=target)
    elif delete_pk:
        target = get_object_or_404(model, pk=delete_pk)
        modal = 'delete'
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'name')
    return _org_render(request, template, model, form, group_field,
                       modal, target, q=q, sort=sort)


def _org_create(request, form_cls, template, redirect_name, label, group_field):
    form = form_cls(request.POST)
    if form.is_valid():
        item = form.save()
        messages.success(request, f'{label} {item.name} added.')
        return redirect(redirect_name)
    return _org_render(request, template, form_cls._meta.model, form, group_field,
                       modal='new', status=200)


def _org_update(request, pk, form_cls, template, redirect_name, label, group_field):
    target = get_object_or_404(form_cls._meta.model, pk=pk)
    form = form_cls(request.POST, instance=target)
    if form.is_valid():
        item = form.save()
        messages.success(request, f'{label} {item.name} updated.')
        return redirect(redirect_name)
    return _org_render(request, template, form_cls._meta.model, form, group_field,
                       modal='edit', target=target, status=200)


def _org_delete(request, pk, model, redirect_name, label):
    target = get_object_or_404(model, pk=pk)
    try:
        target.delete()
    except ProtectedError:
        messages.error(
            request, f'Cannot delete {label} {target.name}: employees still use it.'
        )
        return redirect(redirect_name)
    messages.success(request, f'{label} {target.name} deleted.')
    return redirect(redirect_name)


@login_required
def department_list(request):
    return _org_list_view(request, Department, DepartmentForm(),
                          'employees/departments.html', 'department')


@login_required
@require_POST
def department_create(request):
    return _org_create(request, DepartmentForm, 'employees/departments.html',
                       'employees:department_list', 'Department', 'department')


@login_required
@require_POST
def department_update(request, pk):
    return _org_update(request, pk, DepartmentForm, 'employees/departments.html',
                       'employees:department_list', 'Department', 'department')


@login_required
@require_POST
def department_delete(request, pk):
    return _org_delete(
        request, pk, Department, 'employees:department_list', 'Department'
    )


@login_required
def position_list(request):
    return _org_list_view(request, Position, PositionForm(),
                          'employees/positions.html', 'position')


@login_required
@require_POST
def position_create(request):
    return _org_create(request, PositionForm, 'employees/positions.html',
                       'employees:position_list', 'Position', 'position')


@login_required
@require_POST
def position_update(request, pk):
    return _org_update(request, pk, PositionForm, 'employees/positions.html',
                       'employees:position_list', 'Position', 'position')


@login_required
@require_POST
def position_delete(request, pk):
    return _org_delete(
        request, pk, Position, 'employees:position_list', 'Position'
    )
