from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Department, Employee, Position


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
    for field in ('position', 'department'):
        if isinstance(defaults[field], str):
            model = Position if field == 'position' else Department
            defaults[field], _ = model.objects.get_or_create(name=defaults[field])
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
        department = Department.objects.create(name='Finance')
        position = Position.objects.create(name='Accountant')
        response = self.client.post(
            reverse('employees:create'),
            {
                'emp_id': 'EMP100', 'first_name': 'Sophea', 'last_name': 'Chan',
                'position': position.pk, 'department': department.pk,
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
                'last_name': employee.last_name, 'position': employee.position.pk,
                'department': employee.department.pk, 'hire_date': employee.hire_date,
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

    def test_rows_clickable_and_edit_modal_holds_delete(self):
        self.login()
        employee = make_employee()
        response = self.client.get(reverse('employees:list'))
        self.assertContains(response, f'data-href="?edit={employee.pk}')
        self.assertContains(response, 'cursor: pointer')
        self.assertNotContains(response, 'Actions')
        response = self.client.get(reverse('employees:list') + f'?edit={employee.pk}')
        self.assertEqual(response.context['modal'], 'edit')
        self.assertContains(response, f'?delete={employee.pk}')


class OrganizationTests(TestCase):
    def setUp(self):
        User.objects.create_user('hr', password='hrpass123')
        self.client.login(username='hr', password='hrpass123')

    def test_org_pages_require_login(self):
        self.client.logout()
        for url_name in ('department_list', 'position_list'):
            response = self.client.get(reverse(f'employees:{url_name}'))
            self.assertEqual(response.status_code, 302)

    def test_department_list_shows_counts(self):
        make_employee()
        response = self.client.get(reverse('employees:department_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'IT')
        self.assertEqual(response.context['items'][0].count, 1)

    def test_create_department(self):
        response = self.client.post(
            reverse('employees:department_create'), {'name': 'Legal'}
        )
        self.assertRedirects(response, reverse('employees:department_list'))
        self.assertTrue(Department.objects.filter(name='Legal').exists())

    def test_duplicate_department_rejected(self):
        Department.objects.create(name='Legal')
        response = self.client.post(
            reverse('employees:department_create'), {'name': 'Legal'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Department.objects.count(), 1)
        self.assertTrue(response.context['form'].errors)

    def test_delete_unused_department(self):
        department = Department.objects.create(name='Legal')
        response = self.client.post(
            reverse('employees:department_delete', args=[department.pk])
        )
        self.assertRedirects(response, reverse('employees:department_list'))
        self.assertFalse(Department.objects.filter(pk=department.pk).exists())

    def test_delete_department_in_use_is_blocked(self):
        employee = make_employee()
        department = Department.objects.get(name='IT')
        response = self.client.post(
            reverse('employees:department_delete', args=[department.pk]), follow=True
        )
        self.assertTrue(Department.objects.filter(pk=department.pk).exists())
        self.assertContains(response, 'employees still use it')
        self.assertTrue(Employee.objects.filter(pk=employee.pk).exists())

    def test_position_lifecycle(self):
        make_employee()
        response = self.client.post(
            reverse('employees:position_create'), {'name': 'Analyst'}
        )
        self.assertRedirects(response, reverse('employees:position_list'))
        analyst = Position.objects.get(name='Analyst')
        self.client.post(reverse('employees:position_delete', args=[analyst.pk]))
        self.assertFalse(Position.objects.filter(pk=analyst.pk).exists())
        in_use = Position.objects.get(name='Developer')
        response = self.client.post(
            reverse('employees:position_delete', args=[in_use.pk]), follow=True
        )
        self.assertTrue(Position.objects.filter(pk=in_use.pk).exists())
        self.assertContains(response, 'employees still use it')
