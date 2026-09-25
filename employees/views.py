from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import EmployeeForm
from .models import Employee


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
            | Q(position__icontains=q)
            | Q(department__icontains=q)
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


@require_POST
def employee_delete(request, pk):
    target = get_object_or_404(Employee, pk=pk)
    emp_id = target.emp_id
    target.delete()
    messages.success(request, f'Employee {emp_id} deleted.')
    return redirect('employees:list')
