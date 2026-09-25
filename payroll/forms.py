import calendar

from django import forms

from .models import Payslip

MONTH_CHOICES = [(str(i), calendar.month_name[i]) for i in range(1, 13)]


class RunCreateForm(forms.Form):
    year = forms.IntegerField(
        min_value=2020, max_value=2100, initial=2026,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
    )
    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
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
