from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import DepartmentForm, EmployeeForm, PositionForm
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


def _org_items(model):
    return model.objects.annotate(count=Count('employees')).order_by('name')


def _org_render(request, template, model, form, modal=None, target=None, status=200):
    return render(
        request,
        template,
        {'items': _org_items(model), 'form': form, 'modal': modal, 'target': target},
        status=status,
    )


def _org_list_view(request, model, form, template):
    modal = target = None
    if request.GET.get('new'):
        modal = 'new'
    pk = _parse_pk(request.GET.get('delete'))
    if pk:
        target = get_object_or_404(model, pk=pk)
        modal = 'delete'
    return _org_render(request, template, model, form, modal, target)


def _org_create(request, form_cls, template, redirect_name, label):
    form = form_cls(request.POST)
    if form.is_valid():
        item = form.save()
        messages.success(request, f'{label} {item.name} added.')
        return redirect(redirect_name)
    return _org_render(
        request, template, form_cls._meta.model, form, modal='new', status=200
    )


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
    return _org_list_view(
        request, Department, DepartmentForm(), 'employees/departments.html'
    )


@login_required
@require_POST
def department_create(request):
    return _org_create(
        request, DepartmentForm, 'employees/departments.html',
        'employees:department_list', 'Department',
    )


@login_required
@require_POST
def department_delete(request, pk):
    return _org_delete(
        request, pk, Department, 'employees:department_list', 'Department'
    )


@login_required
def position_list(request):
    return _org_list_view(
        request, Position, PositionForm(), 'employees/positions.html'
    )


@login_required
@require_POST
def position_create(request):
    return _org_create(
        request, PositionForm, 'employees/positions.html',
        'employees:position_list', 'Position',
    )


@login_required
@require_POST
def position_delete(request, pk):
    return _org_delete(
        request, pk, Position, 'employees:position_list', 'Position'
    )
