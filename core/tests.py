"""Dashboard tests: chart payloads must equal the database aggregates."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from employees.models import Department, Employee, Position
from payroll.models import PayrollRun
from payroll.services import generate_run

from employees.tests import make_employee


class DashboardTests(TestCase):
    def setUp(self):
        User.objects.create_user('hr', password='hrpass123')
        self.client.login(username='hr', password='hrpass123')

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('home')).status_code, 302)

    def test_dashboard_without_runs_shows_empty_state(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['cost_split'])
        self.assertContains(response, 'No payroll run yet')

    def test_cost_split_matches_run_totals(self):
        make_employee()
        run, _ = generate_run(2026, 9)
        response = self.client.get(reverse('home'))
        split = response.context['cost_split']
        slip = run.payslips.get()
        self.assertEqual(dict(zip(split['labels'], split['values'])), {
            'Net pay': int(slip.net),
            'NSSF (employee)': int(slip.nssf_employee),
            'Salary tax': int(slip.salary_tax),
            'Advances': int(slip.advances),
        })
        # The employee-side slices must reconstruct gross.
        self.assertEqual(sum(split['values']), int(slip.gross))
        self.assertEqual(response.context['run_summary']['employer'],
                         int(slip.nssf_employer))

    def test_dept_chart_counts_match_database(self):
        make_employee()
        make_employee(emp_id='EMP002', department='Finance')
        make_employee(emp_id='EMP003', department='Finance', is_active=False)
        response = self.client.get(reverse('home'))
        chart = response.context['dept_chart']
        counts = dict(zip(chart['labels'], chart['values']))
        self.assertEqual(counts['IT'], 1)
        self.assertEqual(counts['Finance'], 2)
        self.assertEqual(
            sorted(counts), sorted(Department.objects.values_list('name', flat=True)))

    def test_hero_and_stats_render_real_values(self):
        make_employee()
        run, _ = generate_run(2026, 9)
        response = self.client.get(reverse('home'))
        self.assertContains(response, run.period_label)
        self.assertContains(response, 'is due to GDT by')
        self.assertContains(response, run.gdt_due_date.strftime('%d %b %Y'))
        self.assertEqual(response.context['department_total'],
                         Department.objects.count())
        self.assertEqual(response.context['position_total'],
                         Position.objects.count())
        self.assertEqual(len(response.context['draft_runs']), 1)
        self.assertContains(response, 'still a draft')

    def test_canvases_carry_data_attributes(self):
        make_employee()
        generate_run(2026, 9)
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'id="costChart"')
        self.assertContains(response, 'id="deptChart"')
        self.assertContains(response, 'chart.js@4.4.7')
        self.assertContains(response, 'integrity="sha384-')
