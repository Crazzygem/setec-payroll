from django.contrib import admin

from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('emp_id', 'first_name', 'last_name', 'position',
                    'department', 'base_salary', 'is_active')
    list_filter = ('department', 'contract_type', 'is_active')
    search_fields = ('emp_id', 'first_name', 'last_name')
