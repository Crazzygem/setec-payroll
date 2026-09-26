import calendar

from django import forms
from django.forms import modelformset_factory

from .models import Payslip

MONTH_CHOICES = [(str(i), calendar.month_name[i]) for i in range(1, 13)]


class RunCreateForm(forms.Form):
    year = forms.IntegerField(
        min_value=2020, max_value=2100,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
    )
    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )


class PayslipExtrasForm(forms.ModelForm):
    """Edit the per-period variable inputs of a payslip (draft runs only)."""

    class Meta:
        model = Payslip
        fields = ('overtime', 'bonus', 'advances')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control form-control-sm')
            field.widget.attrs.setdefault('min', '0')
            field.widget.attrs.setdefault('step', '1')
            field.widget.attrs.setdefault('inputmode', 'numeric')


# Bulk editor on the run page: one row per payslip, only changed rows are saved.
# edit_only: a tampered TOTAL_FORMS cannot create payslips through this form.
ExtrasFormSet = modelformset_factory(
    Payslip, form=PayslipExtrasForm, extra=0, can_delete=False, edit_only=True
)
