from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from employees.models import Employee
from payroll.models import PayrollRun


@login_required
def index(request):
    """Dashboard: headcount + latest payroll run summary."""
    last_run = PayrollRun.objects.first()  # ordered newest first
    run_summary = None
    if last_run:
        totals = last_run.payslips.aggregate(
            gross=Sum('gross'),
            tax=Sum('salary_tax'),
            net=Sum('net'),
            employer=Sum('nssf_employer'),
        )
        run_summary = {'run': last_run, **totals}

    return render(
        request,
        'core/index.html',
        {
            'active_employees': Employee.objects.filter(is_active=True).count(),
            'employee_total': Employee.objects.count(),
            'run_summary': run_summary,
            'run_count': PayrollRun.objects.count(),
        },
    )
