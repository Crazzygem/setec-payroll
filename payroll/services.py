"""Payroll services: run generation and payslip recomputation."""
from decimal import Decimal

from django.db import transaction

from employees.models import Employee

from .engine import calculate_payslip
from .models import PayrollRun, Payslip

ZERO = Decimal('0')


def apply_payslip_math(payslip: Payslip) -> Payslip:
    """Recompute every derived field from the payslip's stored inputs."""
    result = calculate_payslip(
        base=payslip.base,
        allowance=payslip.allowance,
        overtime=payslip.overtime or ZERO,
        bonus=payslip.bonus or ZERO,
        advances=payslip.advances or ZERO,
        dependents=payslip.dependents,
        nssf_member=payslip.nssf_member,
        is_resident=payslip.is_resident,
    )
    for field, value in result.items():
        setattr(payslip, field, value)
    return payslip


@transaction.atomic
def generate_run(year: int, month: int):
    """Create a draft run with one payslip per active employee.

    Returns (run, created). If the period already exists, returns it untouched.
    """
    run, created = PayrollRun.objects.get_or_create(year=year, month=month)
    if created:
        slips = []
        for emp in Employee.objects.filter(is_active=True):
            slip = Payslip(
                run=run,
                employee=emp,
                base=emp.base_salary,
                allowance=emp.allowance_monthly,
                dependents=emp.dependents,
                nssf_member=emp.nssf_member,
                is_resident=emp.is_resident,
                # overtime/bonus/advances start at 0
            )
            apply_payslip_math(slip)
            slips.append(slip)
        Payslip.objects.bulk_create(slips)
    return run, created


def next_period(today=None):
    """(year, month) to offer for a new run: the month after the newest run,
    or the current month when no run exists yet."""
    latest = PayrollRun.objects.first()  # ordered newest period first
    if latest is None:
        from django.utils import timezone
        today = today or timezone.localdate()
        return today.year, today.month
    if latest.month == 12:
        return latest.year + 1, 1
    return latest.year, latest.month + 1


@transaction.atomic
def regenerate_run(run: PayrollRun) -> dict:
    """Bring a draft run in line with current employee records.

    Refreshes each payslip's salary snapshot, adds payslips for employees who
    became active, and removes payslips of employees who are no longer active.
    Overtime, bonus and advances already entered are kept.
    """
    if not run.is_draft:
        raise ValueError('Only draft runs can be regenerated.')
    active = {e.pk: e for e in Employee.objects.filter(is_active=True)}
    removed, _ = run.payslips.exclude(employee_id__in=list(active)).delete()
    updated = 0
    existing = set()
    for slip in run.payslips.select_related('employee'):
        emp = slip.employee
        existing.add(emp.pk)
        slip.base = emp.base_salary
        slip.allowance = emp.allowance_monthly
        slip.dependents = emp.dependents
        slip.nssf_member = emp.nssf_member
        slip.is_resident = emp.is_resident
        apply_payslip_math(slip)
        slip.save()
        updated += 1
    added = []
    for pk, emp in active.items():
        if pk in existing:
            continue
        slip = Payslip(
            run=run, employee=emp, base=emp.base_salary,
            allowance=emp.allowance_monthly, dependents=emp.dependents,
            nssf_member=emp.nssf_member, is_resident=emp.is_resident,
        )
        apply_payslip_math(slip)
        added.append(slip)
    Payslip.objects.bulk_create(added)
    return {'updated': updated, 'added': len(added), 'removed': removed}
