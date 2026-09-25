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
