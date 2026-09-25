"""Pure payroll calculation functions. No Django, no I/O, unit-tested directly.

All money is Decimal, quantized to whole KHR (ROUND_HALF_UP) at the payslip
field level. See payroll/rules.py for every rate and its source.
"""
from decimal import ROUND_HALF_UP, Decimal

from .rules import (
    DEPENDENT_ALLOWANCE,
    DAILY_DIVISOR,
    NON_RESIDENT_TAX_RATE,
    NSSF_EMPLOYER_RATE,
    NSSF_EMPLOYEE_RATE,
    SALARY_TAX_BANDS,
    SENIORITY_DAYS_PER_YEAR,
)

ZERO = Decimal('0')
WHOLE = Decimal('1')


def to_decimal(value) -> Decimal:
    """Accept int/str/float-free inputs and normalize to Decimal."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def whole_khr(value: Decimal) -> Decimal:
    """Quantize to whole KHR, rounding half up (Cambodian payslip convention)."""
    return value.quantize(WHOLE, rounding=ROUND_HALF_UP)


def salary_tax(taxable: Decimal) -> Decimal:
    """Marginal (progressive) monthly salary tax across the resident bands."""
    taxable = to_decimal(taxable)
    tax = ZERO
    lower = ZERO
    for upper, rate in SALARY_TAX_BANDS:
        if upper is None:  # top band: everything above the last ceiling
            tax += max(taxable - lower, ZERO) * rate
            break
        if taxable <= lower:
            break
        tax += (min(taxable, upper) - lower) * rate
        lower = upper
    return tax


def calculate_payslip(
    *,
    base,
    allowance=ZERO,
    overtime=ZERO,
    bonus=ZERO,
    advances=ZERO,
    dependents=0,
    nssf_member=True,
    is_resident=True,
) -> dict:
    """Compute one payslip. Every value returned is whole KHR (Decimal).

    Rules applied:
      gross      = base + allowance + overtime + bonus   (cash salary)
      nssf_emp   = 2% of gross if member, else 0
      taxable    = resident: gross - nssf_emp - (150,000 x dependants), floor 0
                   non-resident: gross (flat tax, no deductions)
      tax        = resident: marginal bands; non-resident: 20% flat
      net        = gross - nssf_emp - tax - advances
      nssf_er    = 5.4% of gross if member, else 0   (employer cost)
      seniority  = base / 22 x 15 / 12  (simplified monthly accrual)
    """
    base = to_decimal(base)
    allowance = to_decimal(allowance)
    overtime = to_decimal(overtime)
    bonus = to_decimal(bonus)
    advances = to_decimal(advances)

    gross = base + allowance + overtime + bonus

    nssf_employee = whole_khr(gross * NSSF_EMPLOYEE_RATE) if nssf_member else ZERO
    dependent_allowance = DEPENDENT_ALLOWANCE * int(dependents)

    if is_resident:
        taxable = max(gross - nssf_employee - dependent_allowance, ZERO)
        tax = whole_khr(salary_tax(taxable))
    else:
        taxable = gross
        tax = whole_khr(gross * NON_RESIDENT_TAX_RATE)

    net = gross - nssf_employee - tax - advances
    nssf_employer = whole_khr(gross * NSSF_EMPLOYER_RATE) if nssf_member else ZERO
    seniority_accrual = whole_khr(
        base / DAILY_DIVISOR * SENIORITY_DAYS_PER_YEAR / 12
    )

    return {
        'base': base,
        'allowance': allowance,
        'overtime': overtime,
        'bonus': bonus,
        'gross': whole_khr(gross),
        'nssf_employee': nssf_employee,
        'dependent_allowance': dependent_allowance,
        'taxable': whole_khr(taxable),
        'salary_tax': tax,
        'advances': advances,
        'net': whole_khr(net),
        'nssf_employer': nssf_employer,
        'seniority_accrual': seniority_accrual,
    }
