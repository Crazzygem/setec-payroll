from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from employees.models import Department, Employee
from payroll.models import PayrollRun


@login_required
def index(request):
    """Dashboard: latest run as the focal point, plus real aggregates."""
    last_run = PayrollRun.objects.first()  # ordered newest period first
    run_summary = None
    cost_split = None
    if last_run:
        totals = last_run.payslips.aggregate(
            gross=Sum('gross'),
            tax=Sum('salary_tax'),
            net=Sum('net'),
            nssf_employee=Sum('nssf_employee'),
            advances=Sum('advances'),
            employer=Sum('nssf_employer'),
        )
        run_summary = {
            'run': last_run,
            **totals,
            'employer_cost': (totals['gross'] or 0) + (totals['employer'] or 0),
        }
        # Month-over-month change against the run just before this one, so the
        # comparison period is real and can be named on the card.
        prev_run = (
            PayrollRun.objects.filter(year__lt=last_run.year)
            | PayrollRun.objects.filter(year=last_run.year, month__lt=last_run.month)
        ).first()
        if prev_run:
            prev_net = prev_run.payslips.aggregate(net=Sum('net'))['net'] or 0
            run_summary['prev_run'] = prev_run
            run_summary['net_change'] = (totals['net'] or 0) - prev_net
            run_summary['net_change_pct'] = (
                round(run_summary['net_change'] / prev_net * 100, 1) if prev_net else None
            )
        # Where each ring of gross goes: employee side only, so the slices sum
        # to gross. Employer cost is extra and reported separately.
        cost_split = {
            'labels': ['Net pay', 'NSSF (employee)', 'Salary tax', 'Advances'],
            'values': [
                int(totals['net'] or 0),
                int(totals['nssf_employee'] or 0),
                int(totals['tax'] or 0),
                int(totals['advances'] or 0),
            ],
        }

    by_department = list(
        Department.objects.annotate(n=Count('employees', distinct=True))
        .order_by('-n', 'name')
    )
    dept_chart = {
        'labels': [d.name for d in by_department],
        'values': [d.n for d in by_department],
    }

    draft_runs = list(
        PayrollRun.objects.filter(status=PayrollRun.STATUS_DRAFT)
        .annotate(headcount=Count('payslips'))
        .order_by('-year', '-month')
    )

    return render(
        request,
        'core/index.html',
        {
            'active_employees': Employee.objects.filter(is_active=True).count(),
            'employee_total': Employee.objects.count(),
            'run_summary': run_summary,
            'recent_runs': PayrollRun.objects.annotate(
                headcount=Count('payslips'), net_total=Sum('payslips__net')
            ).order_by('-year', '-month')[:5],
            'cost_split': cost_split,
            'dept_chart': dept_chart,
            'draft_runs': draft_runs,
            'today': timezone.localdate(),
        },
    )
