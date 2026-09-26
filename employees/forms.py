from django import forms
from django.forms.widgets import CheckboxInput, Select

from .models import Department, Employee, Position


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'emp_id', 'first_name', 'last_name', 'position', 'department',
            'hire_date', 'contract_type', 'base_salary', 'allowance_monthly',
            'dependents', 'is_resident', 'nssf_member', 'is_active',
        ]
        widgets = {
            'hire_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }
        # Each text states what payroll/engine.py does with the field.
        help_texts = {
            'dependents': 'Each dependant lowers taxable salary by 150,000 KHR '
                          'a month (tax residents only).',
            'is_resident': 'Residents are taxed on the progressive bands after NSSF '
                           'and dependants. Non-residents pay a flat 20% of gross.',
            'nssf_member': 'Deducts 2% of gross from pay and adds a 5.4% employer '
                           'cost. Untick to leave NSSF out.',
            'is_active': 'Only active employees get a payslip in new payroll runs.',
        }

    # Field groups for the add/edit modal, in reading order.
    SECTIONS = (
        ('Identity', ('emp_id', 'first_name', 'last_name')),
        ('Job', ('position', 'department', 'hire_date', 'contract_type')),
        ('Pay', ('base_salary', 'allowance_monthly')),
        ('Tax and NSSF', ('dependents', 'is_resident', 'nssf_member', 'is_active')),
    )

    def sections(self):
        return [(title, [self[name] for name in names]) for title, names in self.SECTIONS]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, Select):
                widget.attrs.setdefault('class', 'form-select form-select-sm')
            else:
                widget.attrs.setdefault('class', 'form-control form-control-sm')
            if name == 'emp_id':
                widget.attrs.setdefault('placeholder', 'e.g. EMP001')
            elif name in ('base_salary', 'allowance_monthly'):
                widget.attrs.setdefault('placeholder', 'e.g. 2000000')
                widget.attrs.setdefault('inputmode', 'numeric')


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name']
        widgets = {
            'name': forms.TextInput(
                attrs={'class': 'form-control form-control-sm',
                       'placeholder': 'e.g. Accounting'}
            ),
        }


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['name']
        widgets = {
            'name': forms.TextInput(
                attrs={'class': 'form-control form-control-sm',
                       'placeholder': 'e.g. Accountant'}
            ),
        }
