from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Department(models.Model):
    """A named department employees belong to; deletion blocked while in use."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Position(models.Model):
    """A job title employees hold; deletion blocked while in use."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Employee(models.Model):
    """An employee record with everything the payroll engine needs."""

    class ContractType(models.TextChoices):
        FIXED = 'FIXED', 'Fixed-duration'
        UNSPECIFIED = 'UNSPECIFIED', 'Unspecified-duration'

    emp_id = models.CharField('Employee ID', max_length=10, unique=True)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    position = models.ForeignKey(
        Position, on_delete=models.PROTECT, related_name='employees'
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='employees'
    )
    hire_date = models.DateField()
    contract_type = models.CharField(
        max_length=12,
        choices=ContractType.choices,
        default=ContractType.UNSPECIFIED,
    )
    base_salary = models.DecimalField(
        'Base salary (KHR/month)',
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(1)],
    )
    allowance_monthly = models.DecimalField(
        'Allowance (KHR/month)',
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)],
    )
    dependents = models.PositiveSmallIntegerField(
        'Dependants (spouse/children)',
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    is_resident = models.BooleanField('Cambodia tax resident', default=True)
    nssf_member = models.BooleanField('NSSF member', default=True)
    is_active = models.BooleanField('Active', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['emp_id']

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def __str__(self):
        return f'{self.emp_id} · {self.full_name}'
