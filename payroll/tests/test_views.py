"""Tests for run views: generation, totals, extras editing, finalize lock."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from employees.models import Employee

from ..models import PayrollRun, Payslip


def make_employee(**overrides):
    defaults = {
        'emp_id': 'EMP001', 'first_name': 'Dara', 'last_name': 'Sok',
        'position': 'Developer', 'department': 'IT', 'hire_date': '2025-01-15',
        'base_salary': 2000000,
    }
    defaults.update(overrides)
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
