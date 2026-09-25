"""Tests for the payroll engine, written FIRST (TDD), hand-computed expectations."""
from decimal import Decimal

from django.test import SimpleTestCase

from payroll.engine import calculate_payslip, salary_tax


class SalaryTaxBandTests(SimpleTestCase):
    """Monthly resident Tax-on-Salary bands (PwC Tax Summaries, Cambodia).
    Tax = marginal computation across bands, quantized to whole KHR."""

    def test_at_zero_bracket_ceiling_is_tax_free(self):
        self.assertEqual(salary_tax(Decimal('1500000')), Decimal('0'))

    def test_just_above_zero_bracket(self):
        # 200 KHR over the ceiling, taxed at 5% = 10 KHR
        self.assertEqual(salary_tax(Decimal('1500200')), Decimal('10'))

    def test_top_of_5_percent_bracket(self):
        # (2,000,000 - 1,500,000) * 5% = 25,000
        self.assertEqual(salary_tax(Decimal('2000000')), Decimal('25000'))

    def test_top_of_10_percent_bracket(self):
        # 25,000 + (8,500,000 - 2,000,000) * 10% = 675,000
        self.assertEqual(salary_tax(Decimal('8500000')), Decimal('675000'))

    def test_top_of_15_percent_bracket(self):
        # 675,000 + (12,500,000 - 8,500,000) * 15% = 1,275,000
        self.assertEqual(salary_tax(Decimal('12500000')), Decimal('1275000'))

    def test_top_bracket(self):
        # 1,275,000 + (20,000,000 - 12,500,000) * 20% = 2,775,000
        self.assertEqual(salary_tax(Decimal('20000000')), Decimal('2775000'))

    def test_zero_taxable(self):
        self.assertEqual(salary_tax(Decimal('0')), Decimal('0'))


class PayslipCalculationTests(SimpleTestCase):
    def test_worked_example_full_payslip(self):
        """README worked example: base 2,000,000 + 200,000 allowance,
        2 dependants, NSSF member."""
        result = calculate_payslip(
            base=Decimal('2000000'), allowance=Decimal('200000'),
            dependents=2, nssf_member=True, is_resident=True,
        )
        self.assertEqual(result['gross'], Decimal('2200000'))
        self.assertEqual(result['nssf_employee'], Decimal('44000'))       # 2%
        self.assertEqual(result['dependent_allowance'], Decimal('300000'))  # 2 × 150k
        self.assertEqual(result['taxable'], Decimal('1856000'))
        self.assertEqual(result['salary_tax'], Decimal('17800'))  # (1,856,000-1,500,000)×5%
        self.assertEqual(result['net'], Decimal('2138200'))
        self.assertEqual(result['nssf_employer'], Decimal('118800'))  # 5.4%

    def test_net_identity(self):
        result = calculate_payslip(
            base=Decimal('3000000'), allowance=Decimal('100000'),
            overtime=Decimal('150000'), bonus=Decimal('0'),
            advances=Decimal('200000'), dependents=1,
        )
        expected_net = (
            result['gross'] - result['nssf_employee']
            - result['salary_tax'] - Decimal('200000')
        )
        self.assertEqual(result['net'], expected_net)

    def test_overtime_and_bonus_are_taxable_cash(self):
        without = calculate_payslip(base=Decimal('2000000'))
        with_extra = calculate_payslip(
            base=Decimal('2000000'), overtime=Decimal('500000'),
            bonus=Decimal('300000'),
        )
        self.assertEqual(with_extra['gross'] - without['gross'], Decimal('800000'))
        self.assertGreater(with_extra['salary_tax'], without['salary_tax'])

    def test_non_member_pays_no_nssf(self):
        result = calculate_payslip(
            base=Decimal('2000000'), nssf_member=False, is_resident=True,
        )
        self.assertEqual(result['nssf_employee'], Decimal('0'))
        self.assertEqual(result['nssf_employer'], Decimal('0'))
        # No NSSF deduction → higher taxable salary than a member
        self.assertEqual(result['taxable'], Decimal('2000000'))

    def test_non_resident_flat_20_percent(self):
        result = calculate_payslip(
            base=Decimal('10000000'), is_resident=False, nssf_member=True,
        )
        self.assertEqual(result['salary_tax'], Decimal('2000000'))  # 20% flat
        self.assertEqual(result['taxable'], Decimal('10000000'))

    def test_dependants_reduce_tax(self):
        no_kids = calculate_payslip(base=Decimal('2000000'), dependents=0)
        three_kids = calculate_payslip(base=Decimal('2000000'), dependents=3)
        # 3 × 150,000 = 450,000 reduction in the 5% bracket → 22,500 less tax
        self.assertEqual(no_kids['salary_tax'] - three_kids['salary_tax'], Decimal('22500'))

    def test_tax_never_negative(self):
        result = calculate_payslip(base=Decimal('1000000'), dependents=5)
        self.assertGreaterEqual(result['salary_tax'], Decimal('0'))
        self.assertGreaterEqual(result['taxable'], Decimal('0'))

    def test_seniority_accrual(self):
        # 15 days/year → monthly = base/22 × 15/12; base 2,640,000 → 150,000
        result = calculate_payslip(base=Decimal('2640000'))
        self.assertEqual(result['seniority_accrual'], Decimal('150000'))

    def test_zero_inputs_do_not_crash(self):
        result = calculate_payslip(base=Decimal('0'))
        self.assertEqual(result['gross'], Decimal('0'))
        self.assertEqual(result['salary_tax'], Decimal('0'))
        self.assertEqual(result['net'], Decimal('0'))

    def test_rounding_is_whole_khr(self):
        result = calculate_payslip(base=Decimal('1500200'), dependents=0)
        for field in ('nssf_employee', 'salary_tax', 'net'):
            self.assertEqual(result[field] % 1, Decimal('0'), field)
