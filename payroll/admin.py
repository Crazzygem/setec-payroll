from django.contrib import admin

from .models import PayrollRun, Payslip


class PayslipInline(admin.TabularInline):
    model = Payslip
    extra = 0
    can_delete = False
    readonly_fields = ('gross', 'nssf_employee', 'salary_tax', 'net')


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'status', 'created_at', 'finalized_at')
    list_filter = ('status', 'year')
    inlines = [PayslipInline]


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('run', 'employee', 'gross', 'salary_tax', 'net')
    list_filter = ('run',)
    search_fields = ('employee__emp_id', 'employee__first_name')
