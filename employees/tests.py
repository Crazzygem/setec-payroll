from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Employee


def make_employee(**overrides):
    defaults = {
        'emp_id': 'EMP001',
        'first_name': 'Dara',
        'last_name': 'Sok',
        'position': 'Developer',
        'department': 'IT',
        'hire_date': '2025-01-15',
        'base_salary': 2000000,
    }
    defaults.update(overrides)
    return Employee.objects.create(**defaults)


class EmployeeCrudTests(TestCase):
    def setUp(self):
        User.objects.create_user('hr', password='hrpass123')

    def login(self):
        self.client.login(username='hr', password='hrpass123')

    def test_list_requires_login(self):
        response = self.client.get(reverse('employees:list'))
        self.assertEqual(response.status_code, 302)

    def test_list_renders_when_logged_in(self):
        self.login()
        response = self.client.get(reverse('employees:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Employee')

    def test_create_employee(self):
        self.login()
        response = self.client.post(
            reverse('employees:create'),
            {
                'emp_id': 'EMP100', 'first_name': 'Sophea', 'last_name': 'Chan',
                'position': 'Accountant', 'department': 'Finance',
                'hire_date': '2025-06-01', 'contract_type': 'UNSPECIFIED',
                'base_salary': 1800000, 'allowance_monthly': 100000,
                'dependents': 2, 'is_resident': True, 'nssf_member': True,
                'is_active': True,
            },
        )
        self.assertRedirects(response, reverse('employees:list'))
        self.assertTrue(Employee.objects.filter(emp_id='EMP100').exists())

    def test_create_invalid_reopens_modal_with_errors(self):
        self.login()
        response = self.client.post(reverse('employees:create'), {'emp_id': 'EMP001'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Employee.objects.count(), 0)
        self.assertTrue(response.context['form'].errors)

    def test_search_filters(self):
        self.login()
        make_employee()
        make_employee(emp_id='EMP002', first_name='Vandy', position='Designer')
        response = self.client.get(reverse('employees:list') + '?q=Designer')
        self.assertEqual(len(response.context['employees']), 1)
        self.assertEqual(response.context['employees'][0].emp_id, 'EMP002')

    def test_edit_updates_salary(self):
        self.login()
        employee = make_employee()
        response = self.client.post(
            reverse('employees:edit', args=[employee.pk]),
            {
                'emp_id': employee.emp_id, 'first_name': employee.first_name,
                'last_name': employee.last_name, 'position': employee.position,
                'department': employee.department, 'hire_date': employee.hire_date,
                'contract_type': employee.contract_type,
                'base_salary': 2500000, 'allowance_monthly': 0,
                'dependents': 0, 'is_resident': True, 'nssf_member': True,
                'is_active': True,
            },
        )
        self.assertRedirects(response, reverse('employees:list'))
        employee.refresh_from_db()
        self.assertEqual(int(employee.base_salary), 2500000)

    def test_delete_employee(self):
        self.login()
        employee = make_employee()
        response = self.client.post(reverse('employees:delete', args=[employee.pk]))
        self.assertRedirects(response, reverse('employees:list'))
        self.assertFalse(Employee.objects.filter(pk=employee.pk).exists())

    def test_delete_rejects_get(self):
        self.login()
        employee = make_employee()
        response = self.client.get(reverse('employees:delete', args=[employee.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Employee.objects.filter(pk=employee.pk).exists())

    def test_post_endpoints_require_login(self):
        employee = make_employee()
        self.client.logout()
        response = self.client.post(reverse('employees:create'), {'emp_id': 'EMP999'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Employee.objects.filter(emp_id='EMP999').exists())
        response = self.client.post(reverse('employees:delete', args=[employee.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Employee.objects.filter(pk=employee.pk).exists())
