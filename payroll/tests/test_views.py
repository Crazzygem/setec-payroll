"""Tests for run views: generation, totals, extras editing, finalize lock."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from employees.models import Department, Employee, Position

from ..models import PayrollRun, Payslip


def make_employee(**overrides):
    defaults = {
        'emp_id': 'EMP001', 'first_name': 'Dara', 'last_name': 'Sok',
        'position': 'Developer', 'department': 'IT', 'hire_date': '2025-01-15',
        'base_salary': 2000000,
    }
    defaults.update(overrides)
    for field in ('position', 'department'):
        if isinstance(defaults[field], str):
            model = Position if field == 'position' else Department
            defaults[field], _ = model.objects.get_or_create(name=defaults[field])
    return Employee.objects.create(**defaults)


class PayrollRunTests(TestCase):
    def setUp(self):
        User.objects.create_user('hr', password='hrpass123')
        self.client.login(username='hr', password='hrpass123')

    def generate(self, year=2026, month=9):
        return self.client.post(
            reverse('payroll:run_create'), {'year': year, 'month': month}
        )

    def test_generate_creates_payslip_per_active_employee(self):
        make_employee()
        make_employee(emp_id='EMP002', first_name='Vandy')
        make_employee(emp_id='EMP003', first_name='Sokha', is_active=False)
        response = self.generate()
        run = PayrollRun.objects.get(year=2026, month=9)
        self.assertRedirects(response, reverse('payroll:run_detail', args=[run.pk]))
        self.assertEqual(run.payslips.count(), 2)
        self.assertFalse(run.payslips.filter(employee__emp_id='EMP003').exists())
        self.assertEqual(run.status, PayrollRun.STATUS_DRAFT)

    def test_duplicate_period_blocked(self):
        make_employee()
        self.generate()
        response = self.generate()
        self.assertEqual(PayrollRun.objects.count(), 1)
        # duplicate redirects to the existing run with an error message
        run = PayrollRun.objects.get()
        self.assertRedirects(response, reverse('payroll:run_detail', args=[run.pk]))

    def test_run_detail_totals_match_payslips(self):
        make_employee()
        make_employee(emp_id='EMP002', first_name='Vandy', base_salary=3000000)
        self.generate()
        response = self.client.get(
            reverse('payroll:run_detail', args=[PayrollRun.objects.get().pk])
        )
        slips = response.context['slips']
        self.assertEqual(len(slips), 2)
        totals = response.context['totals']
        self.assertEqual(
            totals['gross'], sum(s.gross for s in slips)
        )
        self.assertEqual(
            totals['tax'], sum(s.salary_tax for s in slips)
        )
        self.assertEqual(totals['net'], sum(s.net for s in slips))

    def test_extras_edit_recalculates_payslip(self):
        make_employee()
        self.generate()
        run = PayrollRun.objects.get()
        slip = run.payslips.get()
        response = self.client.post(
            reverse('payroll:payslip_update', args=[slip.pk]),
            {'overtime': 100000, 'bonus': 0, 'advances': 0},
        )
        self.assertRedirects(response, reverse('payroll:run_detail', args=[run.pk]))
        slip.refresh_from_db()
        # gross 2,100,000; NSSF 42,000; taxable 2,058,000; tax 30,800; net 2,027,200
        self.assertEqual(slip.gross, Decimal('2100000'))
        self.assertEqual(slip.nssf_employee, Decimal('42000'))
        self.assertEqual(slip.salary_tax, Decimal('30800'))
        self.assertEqual(slip.net, Decimal('2027200'))

    def test_finalize_locks_payslips(self):
        make_employee()
        self.generate()
        run = PayrollRun.objects.get()
        slip = run.payslips.get()
        self.client.post(reverse('payroll:run_finalize', args=[run.pk]))
        run.refresh_from_db()
        self.assertEqual(run.status, PayrollRun.STATUS_FINALIZED)
        self.assertIsNotNone(run.finalized_at)

        before = slip.net
        self.client.post(
            reverse('payroll:payslip_update', args=[slip.pk]),
            {'overtime': 500000, 'bonus': 0, 'advances': 0},
        )
        slip.refresh_from_db()
        self.assertEqual(slip.net, before)  # locked

    def test_finalize_sets_gdt_due_date(self):
        make_employee()
        self.generate(year=2026, month=9)
        run = PayrollRun.objects.get()
        self.assertEqual(run.gdt_due_date, date(2026, 10, 20))
        # December rolls into January of next year
        run2, _ = run.__class__.objects.get_or_create(year=2026, month=12)
        self.assertEqual(run2.gdt_due_date, date(2027, 1, 20))

    def test_payslip_page_renders(self):
        make_employee()
        self.generate()
        slip = Payslip.objects.get()
        response = self.client.get(reverse('payroll:payslip_view', args=[slip.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PAYSLIP')
        self.assertContains(response, 'Net pay')
        # net = 2,000,000 gross - 40,000 NSSF (2%) - 23,000 tax
        # taxable 1,960,000 → (1,960,000 - 1,500,000) x 5% = 23,000
        self.assertContains(response, '1,937,000')

    def test_requires_login(self):
        self.client.logout()
        for url_name in ('payroll:run_list',):
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 302)

    def test_post_endpoints_require_login(self):
        make_employee()
        self.generate()
        run = PayrollRun.objects.get()
        slip = run.payslips.get()
        self.client.logout()

        response = self.client.post(
            reverse('payroll:run_create'), {'year': 2026, 'month': 12}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(PayrollRun.objects.filter(year=2026, month=12).exists())

        response = self.client.post(reverse('payroll:run_finalize', args=[run.pk]))
        self.assertEqual(response.status_code, 302)
        run.refresh_from_db()
        self.assertEqual(run.status, PayrollRun.STATUS_DRAFT)

        response = self.client.post(
            reverse('payroll:payslip_update', args=[slip.pk]),
            {'overtime': 100000, 'bonus': 0, 'advances': 0},
        )
        self.assertEqual(response.status_code, 302)
        slip.refresh_from_db()
        self.assertEqual(slip.overtime, Decimal('0'))

    def test_run_list_rows_clickable_no_open_button(self):
        self.generate()
        response = self.client.get(reverse('payroll:run_list'))
        run = PayrollRun.objects.get()
        self.assertContains(
            response, f'data-href="{reverse("payroll:run_detail", args=[run.pk])}"'
        )
        self.assertNotContains(response, '>Open<')
        self.assertNotContains(response, '>Actions<')

    def test_run_detail_rows_open_payslips_without_action_buttons(self):
        make_employee()
        self.generate()
        run = PayrollRun.objects.get()
        slip = run.payslips.get()
        response = self.client.get(reverse('payroll:run_detail', args=[run.pk]))
        self.assertContains(
            response,
            f'data-href="{reverse("payroll:payslip_view", args=[slip.pk])}"',
        )
        self.assertNotContains(response, '>Extras<')
        self.assertNotContains(response, '>Payslip<')
        self.assertNotContains(response, '>Actions<')

    def test_dashboard_recent_runs_clickable(self):
        self.generate()
        response = self.client.get(reverse('home'))
        run = PayrollRun.objects.get()
        self.assertContains(
            response, f'data-href="{reverse("payroll:run_detail", args=[run.pk])}"'
        )
        self.assertNotContains(response, '>Open<')

    def test_payslip_extras_panel_draft_only(self):
        make_employee()
        self.generate()
        run = PayrollRun.objects.get()
        slip = run.payslips.get()
        url = reverse('payroll:payslip_view', args=[slip.pk])
        response = self.client.get(url)
        self.assertContains(response, 'Extras')
        self.assertNotContains(response, 'class="edit-panel"')
        response = self.client.get(url + '?edit=1')
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['edit_form'])
        self.assertContains(response, 'class="edit-panel"')
        run.status = PayrollRun.STATUS_FINALIZED
        run.save(update_fields=['status'])
        response = self.client.get(url + '?edit=1')
        self.assertIsNone(response.context['edit_form'])
        response = self.client.get(url)
        self.assertNotContains(response, 'Extras')


class RunWorkflowTests(TestCase):
    """Bulk extras editor, regenerate, delete draft, next period, prev/next."""

    def setUp(self):
        User.objects.create_user('hr', password='hrpass123')
        self.client.login(username='hr', password='hrpass123')
        self.e1 = make_employee()
        self.e2 = make_employee(emp_id='EMP002', first_name='Vandy')
        self.client.post(reverse('payroll:run_create'), {'year': 2026, 'month': 9})
        self.run = PayrollRun.objects.get()

    def formset_data(self, values):
        """values: {emp_id: (overtime, bonus, advances)}; others keep current."""
        slips = list(self.run.payslips.order_by('employee__emp_id'))
        data = {
            'form-TOTAL_FORMS': len(slips), 'form-INITIAL_FORMS': len(slips),
            'form-MIN_NUM_FORMS': 0, 'form-MAX_NUM_FORMS': 1000,
        }
        for i, slip in enumerate(slips):
            ot, bonus, adv = values.get(
                slip.employee.emp_id, (slip.overtime, slip.bonus, slip.advances))
            data.update({
                f'form-{i}-id': slip.pk, f'form-{i}-overtime': ot,
                f'form-{i}-bonus': bonus, f'form-{i}-advances': adv,
            })
        return data

    def test_bulk_extras_recalculates_changed_rows(self):
        url = reverse('payroll:run_extras_update', args=[self.run.pk])
        response = self.client.post(url, self.formset_data({'EMP001': (100000, 0, 0)}))
        self.assertRedirects(response, reverse('payroll:run_detail', args=[self.run.pk]))
        slip = self.run.payslips.get(employee=self.e1)
        # Same figures as test_extras_edit_recalculates_payslip.
        self.assertEqual(slip.gross, Decimal('2100000'))
        self.assertEqual(slip.net, Decimal('2027200'))
        other = self.run.payslips.get(employee=self.e2)
        self.assertEqual(other.net, Decimal('1937000'))

    def test_bulk_extras_rejects_negative_and_keeps_input(self):
        url = reverse('payroll:run_extras_update', args=[self.run.pk])
        response = self.client.post(url, self.formset_data({'EMP001': (-5, 0, 0)}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is-invalid')
        self.assertContains(response, 'value="-5"')
        self.assertEqual(self.run.payslips.get(employee=self.e1).overtime, 0)

    def test_bulk_extras_cannot_create_payslips(self):
        data = self.formset_data({})
        data['form-TOTAL_FORMS'] = 3
        data.update({'form-2-id': '', 'form-2-overtime': 5, 'form-2-bonus': 0,
                     'form-2-advances': 0})
        url = reverse('payroll:run_extras_update', args=[self.run.pk])
        response = self.client.post(url, data)
        self.assertIn(response.status_code, (200, 302))
        self.assertEqual(self.run.payslips.count(), 2)

    def test_bulk_extras_refused_on_finalized_run(self):
        self.client.post(reverse('payroll:run_finalize', args=[self.run.pk]))
        url = reverse('payroll:run_extras_update', args=[self.run.pk])
        self.client.post(url, self.formset_data({'EMP001': (100000, 0, 0)}))
        self.assertEqual(self.run.payslips.get(employee=self.e1).overtime, 0)

    def test_draft_detail_renders_inputs_and_totals_row(self):
        response = self.client.get(reverse('payroll:run_detail', args=[self.run.pk]))
        self.assertContains(response, 'name="form-0-overtime"')
        self.assertContains(response, '<tfoot')
        self.assertNotContains(response, 'onsubmit="return confirm')

    def test_regenerate_keeps_extras_and_syncs_employees(self):
        slip = self.run.payslips.get(employee=self.e1)
        slip.bonus = 50000
        slip.save()
        self.e1.base_salary = 2500000
        self.e1.save()
        self.e2.is_active = False
        self.e2.save()
        e3 = make_employee(emp_id='EMP003', first_name='Sokha')
        self.client.post(reverse('payroll:run_regenerate', args=[self.run.pk]))
        slip.refresh_from_db()
        self.assertEqual(slip.bonus, Decimal('50000'))
        self.assertEqual(slip.base, Decimal('2500000'))
        self.assertEqual(slip.gross, Decimal('2550000'))
        emp_ids = set(self.run.payslips.values_list('employee_id', flat=True))
        self.assertEqual(emp_ids, {self.e1.pk, e3.pk})

    def test_delete_draft_only(self):
        self.client.post(reverse('payroll:run_finalize', args=[self.run.pk]))
        self.client.post(reverse('payroll:run_delete', args=[self.run.pk]))
        self.assertTrue(PayrollRun.objects.filter(pk=self.run.pk).exists())
        self.run.status = PayrollRun.STATUS_DRAFT
        self.run.save()
        response = self.client.post(reverse('payroll:run_delete', args=[self.run.pk]))
        self.assertRedirects(response, reverse('payroll:run_list'))
        self.assertFalse(PayrollRun.objects.filter(pk=self.run.pk).exists())

    def test_new_run_form_defaults_to_month_after_latest(self):
        response = self.client.get(reverse('payroll:run_list') + '?new=1')
        form = response.context['form']
        self.assertEqual(form.initial, {'year': 2026, 'month': '10'})
        PayrollRun.objects.create(year=2026, month=12)
        response = self.client.get(reverse('payroll:run_list') + '?new=1')
        self.assertEqual(response.context['form'].initial, {'year': 2027, 'month': '1'})

    def test_payslip_prev_next_links(self):
        first, second = self.run.payslips.order_by('employee__emp_id')
        response = self.client.get(reverse('payroll:payslip_view', args=[first.pk]))
        self.assertIsNone(response.context['prev_slip'])
        self.assertEqual(response.context['next_slip'][0], second.pk)
        self.assertContains(response, reverse('payroll:run_detail', args=[self.run.pk]))
        self.assertNotContains(response, 'history.back')
        response = self.client.get(reverse('payroll:payslip_view', args=[second.pk]))
        self.assertEqual(response.context['prev_slip'][0], first.pk)
        self.assertIsNone(response.context['next_slip'])

    def test_deadline_states(self):
        from unittest import mock
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 10, 25)):
            self.assertEqual(self.run.deadline_state, 'overdue')
            self.assertEqual(self.run.days_overdue, 5)
            self.run.status = PayrollRun.STATUS_FINALIZED
            self.assertEqual(self.run.deadline_state, 'past')
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 10, 17)):
            self.assertEqual(self.run.deadline_state, 'soon')
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 10, 1)):
            self.assertEqual(self.run.deadline_state, 'open')

    def test_new_workflow_endpoints_require_login_and_post(self):
        for name in ('run_extras_update', 'run_regenerate', 'run_delete'):
            url = reverse(f'payroll:{name}', args=[self.run.pk])
            self.assertEqual(self.client.get(url).status_code, 405)
        self.client.logout()
        self.client.post(reverse('payroll:run_delete', args=[self.run.pk]))
        self.assertTrue(PayrollRun.objects.filter(pk=self.run.pk).exists())


class RunOrderingTests(TestCase):
    def test_run_lists_newest_period_first(self):
        User.objects.create_user('hr', password='hrpass123')
        self.client.login(username='hr', password='hrpass123')
        make_employee()
        for year, month in ((2026, 1), (2026, 9), (2025, 12), (2026, 8)):
            self.client.post(reverse('payroll:run_create'), {'year': year, 'month': month})
        expected = [(2026, 9), (2026, 8), (2026, 1), (2025, 12)]
        runs = self.client.get(reverse('payroll:run_list')).context['runs']
        self.assertEqual([(r.year, r.month) for r in runs], expected)
        recent = self.client.get(reverse('home')).context['recent_runs']
        self.assertEqual([(r.year, r.month) for r in recent], expected)
