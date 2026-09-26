import calendar

from django.core.validators import MinValueValidator
from django.db import models

from employees.models import Employee


class PayrollRun(models.Model):
    """One monthly payroll cycle (e.g. September 2026)."""

    STATUS_DRAFT = 'DRAFT'
    STATUS_FINALIZED = 'FINALIZED'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_FINALIZED, 'Finalized'),
    ]

    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()  # 1..12
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('year', 'month')
        ordering = ['-year', '-month']

    @property
    def period_label(self):
        return f'{calendar.month_name[self.month]} {self.year}'

    @property
    def is_draft(self):
        return self.status == self.STATUS_DRAFT

    @property
    def gdt_due_date(self):
        """Withheld salary tax must reach GDT by the 20th of the next month."""
        from datetime import date
        if self.month == 12:
            return date(self.year + 1, 1, 20)
        return date(self.year, self.month + 1, 20)

    @property
    def days_until_due(self):
        """Days from today to the GDT deadline; negative once it has passed."""
        from django.utils import timezone
        return (self.gdt_due_date - timezone.localdate()).days

    @property
    def days_overdue(self):
        return max(-self.days_until_due, 0)

    @property
    def deadline_state(self):
        """'overdue' only for a draft past the deadline: the app does not track
        whether tax was paid, so a finalized run is never flagged."""
        days = self.days_until_due
        if days < 0:
            return 'overdue' if self.is_draft else 'past'
        if days <= 5:
            return 'soon'
        return 'open'

    def __str__(self):
        return f'{self.period_label} ({self.get_status_display()})'


class Payslip(models.Model):
    """A computed payslip snapshot for one employee in one run.

    `base`, `allowance`, `dependents`, `nssf_member`, `is_resident` are copied
    from the employee at generation time; overtime/bonus/advances are editable
    while the run is DRAFT; everything else is derived by payroll.engine.
    """
    run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='payslips')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='payslips')

    # Inputs (editable while DRAFT)
    overtime = models.DecimalField(max_digits=12, decimal_places=0, default=0,
                                   validators=[MinValueValidator(0)])
    bonus = models.DecimalField(max_digits=12, decimal_places=0, default=0,
                                validators=[MinValueValidator(0)])
    advances = models.DecimalField(max_digits=12, decimal_places=0, default=0,
                                   validators=[MinValueValidator(0)])

    # Employment snapshot
    base = models.DecimalField(max_digits=12, decimal_places=0)
    allowance = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    dependents = models.PositiveSmallIntegerField(default=0)
    nssf_member = models.BooleanField(default=True)
    is_resident = models.BooleanField(default=True)

    # Computed results (whole KHR)
    gross = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    nssf_employee = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    dependent_allowance = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    taxable = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    salary_tax = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    net = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    nssf_employer = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    seniority_accrual = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('run', 'employee')
        ordering = ['employee__emp_id']

    @property
    def extras_total(self):
        return self.overtime + self.bonus

    @property
    def total_deductions(self):
        """Employee-side total withheld this period (shown on the payslip)."""
        return self.nssf_employee + self.salary_tax + self.advances

    def __str__(self):
        return f'{self.run.period_label} · {self.employee.emp_id}'
