"""Seed demo data: 6 employees spanning every tax band, Jan-Sep 2026 payroll runs, login.

Usage: python manage.py seed_demo
Idempotent-ish: clears existing employees/runs first so it can be re-run.
"""
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from employees.models import Department, Employee, Position
from payroll.models import PayrollRun
from payroll.services import apply_payslip_math, generate_run

DEMO_USERNAME = 'hr'
DEMO_PASSWORD = 'payroll2026'
DEMO_YEAR = 2026
LAST_FINALIZED_MONTH = 8  # Jan-Aug finalized, September left as a draft

# Base salaries chosen to land in every resident tax band (0 / 5 / 10 / 15 / 20%).
# Hire dates are all before 2026 so every employee belongs in the January run.
EMPLOYEES = [
    dict(emp_id='EMP001', first_name='Kimhornn', last_name='Lyhor', position='Developer',
         department='IT', hire_date=date(2025, 1, 15), base_salary=2000000,
         allowance_monthly=200000, dependents=2),
    dict(emp_id='EMP002', first_name='Yuon', last_name='Kimsinh', position='HR Officer',
         department='HR', hire_date=date(2024, 9, 1), base_salary=1500000,
         allowance_monthly=100000, dependents=1),
    dict(emp_id='EMP003', first_name='Meak', last_name='Channab', position='Accountant',
         department='Finance', hire_date=date(2024, 3, 11), base_salary=3200000,
         allowance_monthly=300000, dependents=3),
    dict(emp_id='EMP004', first_name='Kong', last_name='Meng', position='Finance Manager',
         department='Finance', hire_date=date(2022, 7, 4), base_salary=9000000,
         allowance_monthly=500000, dependents=2),
    dict(emp_id='EMP005', first_name='Chhay', last_name='CheyPiseth',
         position='Ops Supervisor', department='Operations', hire_date=date(2023, 2, 20),
         base_salary=5500000, allowance_monthly=400000, dependents=0),
    dict(emp_id='EMP006', first_name='Ngov', last_name='Bunsinh', position='Sales Executive',
         department='Sales', hire_date=date(2023, 11, 13), base_salary=13500000,
         allowance_monthly=1000000, dependents=3),
]

# Salary changes applied before a month's run is generated: {month: {emp_id: new base}}
RAISES = {7: {'EMP003': 3500000}}

# Per-month variable inputs: {month: {emp_id: {field: amount}}}
EXTRAS = {
    3: {'EMP001': {'overtime': 100000}},
    4: {'EMP005': {'overtime': 200000}},
    5: {'EMP002': {'advances': 300000}},
    6: {'EMP001': {'overtime': 150000}, 'EMP006': {'bonus': 1000000}},
    8: {'EMP005': {'overtime': 250000}},
    9: {'EMP001': {'overtime': 150000}},
}


class Command(BaseCommand):
    help = 'Seed demo data: 6 employees, Jan-Aug 2026 finalized runs, Sep 2026 draft run.'

    def handle(self, *args, **options):
        # Clear (runs first: payslips PROTECT employees)
        deleted_runs = PayrollRun.objects.count()
        PayrollRun.objects.all().delete()
        deleted_emps = Employee.objects.count()
        Employee.objects.all().delete()
        # Departments/positions from older seeds that no employee uses any more
        Department.objects.filter(employees__isnull=True).delete()
        Position.objects.filter(employees__isnull=True).delete()

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

        for month in range(1, 10):
            for emp_id, base in RAISES.get(month, {}).items():
                Employee.objects.filter(emp_id=emp_id).update(base_salary=base)

            run, _ = generate_run(DEMO_YEAR, month)
            for emp_id, fields in EXTRAS.get(month, {}).items():
                slip = run.payslips.get(employee__emp_id=emp_id)
                for field, amount in fields.items():
                    setattr(slip, field, Decimal(amount))
                apply_payslip_math(slip)
                slip.save()

            if month <= LAST_FINALIZED_MONTH:
                run.status = PayrollRun.STATUS_FINALIZED
                run.finalized_at = timezone.make_aware(datetime(DEMO_YEAR, month, 28, 17, 0))
                run.save(update_fields=['status', 'finalized_at'])

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(EMPLOYEES)} employees '
            f'(cleared: {deleted_emps} employees, {deleted_runs} runs), '
            f'9 payroll runs (Jan-Aug {DEMO_YEAR} finalized, Sep draft).'
        ))
        self.stdout.write(self.style.WARNING(
            f'Demo login -> username: {DEMO_USERNAME}   password: {DEMO_PASSWORD}'
        ))
