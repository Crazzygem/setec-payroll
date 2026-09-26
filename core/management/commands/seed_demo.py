"""Seed demo data: 8 employees spanning every tax band, two payroll runs, login.

Usage: python manage.py seed_demo
Idempotent-ish: clears existing employees/runs first so it can be re-run.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from employees.models import Department, Employee, Position
from payroll.models import PayrollRun
from payroll.services import apply_payslip_math, generate_run

DEMO_USERNAME = 'hr'
DEMO_PASSWORD = 'payroll2026'

# Base salaries chosen to land in every resident tax band (0 / 5 / 10 / 15 / 20%)
EMPLOYEES = [
    dict(emp_id='EMP001', first_name='Dara', last_name='Sok', position='Developer',
         department='IT', hire_date=date(2025, 1, 15), base_salary=2000000,
         allowance_monthly=200000, dependents=2),
    dict(emp_id='EMP002', first_name='Vandy', last_name='Chan', position='UI Designer',
         department='IT', hire_date=date(2024, 9, 1), base_salary=1650000,
         allowance_monthly=0, dependents=1),
    dict(emp_id='EMP003', first_name='Sophea', last_name='Lim', position='Accountant',
         department='Finance', hire_date=date(2024, 3, 11), base_salary=3200000,
         allowance_monthly=300000, dependents=3),
    dict(emp_id='EMP004', first_name='Rithy', last_name='Phan', position='Finance Manager',
         department='Finance', hire_date=date(2022, 7, 4), base_salary=9000000,
         allowance_monthly=500000, dependents=2),
    dict(emp_id='EMP005', first_name='Chanthou', last_name='Meas', position='Ops Supervisor',
         department='Operations', hire_date=date(2023, 2, 20), base_salary=5500000,
         allowance_monthly=400000, dependents=0),
    dict(emp_id='EMP006', first_name='Sokunthea', last_name='Nou', position='HR Officer',
         department='HR', hire_date=date(2025, 6, 2), base_salary=1800000,
         allowance_monthly=100000, dependents=1),
    dict(emp_id='EMP007', first_name='Piseth', last_name='Keo', position='Driver',
         department='Operations', hire_date=date(2026, 1, 5), base_salary=1200000,
         allowance_monthly=150000, dependents=0),
    dict(emp_id='EMP008', first_name='Chan', last_name='Vy', position='Sales Executive',
         department='Sales', hire_date=date(2023, 11, 13), base_salary=13500000,
         allowance_monthly=1000000, dependents=3),
]


class Command(BaseCommand):
    help = 'Seed demo data: 8 employees, Aug-2026 finalized run, Sep-2026 draft run.'

    def handle(self, *args, **options):
        # Clear (runs first: payslips PROTECT employees)
        deleted_runs = PayrollRun.objects.count()
        PayrollRun.objects.all().delete()
        deleted_emps = Employee.objects.count()
        Employee.objects.all().delete()

        for data in EMPLOYEES:
            data = dict(data)
            department, _ = Department.objects.get_or_create(
                name=data.pop('department')
            )
            position, _ = Position.objects.get_or_create(name=data.pop('position'))
            Employee.objects.create(department=department, position=position, **data)

        user, _ = User.objects.get_or_create(username=DEMO_USERNAME)
        user.set_password(DEMO_PASSWORD)
        user.save()

        aug, _ = generate_run(2026, 8)
        aug.status = PayrollRun.STATUS_FINALIZED
        aug.finalized_at = timezone.now()
        aug.save(update_fields=['status', 'finalized_at'])

        # September: draft run with one overtime entry to show recalculation
        sep, _ = generate_run(2026, 9)
        slip = sep.payslips.get(employee__emp_id='EMP001')
        slip.overtime = Decimal('150000')
        apply_payslip_math(slip)
        slip.save()

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(EMPLOYEES)} employees '
            f'(cleared: {deleted_emps} employees, {deleted_runs} runs), '
            f'2 payroll runs (Aug finalized, Sep draft).'
        ))
        self.stdout.write(self.style.WARNING(
            f'Demo login -> username: {DEMO_USERNAME}   password: {DEMO_PASSWORD}'
        ))
