"""Cambodian payroll rules: ALL rates and assumptions live in this one file.

Sources (verified 2026-09-25 against PwC Tax Summaries, Cambodia):
  * Monthly salary tax bands, resident 0/5/10/15/20% (marginal)
  * Non-resident flat 20%; fringe benefits flat 20%
  * Dependant allowance: KHR 150,000 per month per dependant spouse/child
  * Withheld salary tax must reach GDT by the 20th of the following month
  * NSSF: occupational risk 0.8% (employer), healthcare 1.3% per share but
    100% employer-borne since 1 Jan 2018, old-age pension first stage 4%
    total = 2% employer + 2% employee

Simplifications for this academic project (flagged in README):
  * Seniority indemnity accrued as 15 days' base wage per completed year of
    service (monthly provision = base/22 x 15/12). VERIFY against Prakas
    127/17 before using in production.
  * No NSSF contributory-wage ceiling applied (ceiling not verified).
"""
from decimal import Decimal

# NSSF rates (share of monthly gross)
NSSF_EMPLOYEE_RATE = Decimal('0.02')    # pension, first stage
NSSF_EMPLOYER_RATE = Decimal('0.054')   # 0.008 ORC + 0.026 healthcare + 0.020 pension

# Tax parameters
DEPENDENT_ALLOWANCE = Decimal('150000')  # KHR per dependant per month
NON_RESIDENT_TAX_RATE = Decimal('0.20')  # flat

# (upper bound of band in KHR, rate); None upper bound = no ceiling
SALARY_TAX_BANDS = (
    (Decimal('1500000'), Decimal('0')),
    (Decimal('2000000'), Decimal('0.05')),
    (Decimal('8500000'), Decimal('0.10')),
    (Decimal('12500000'), Decimal('0.15')),
    (None, Decimal('0.20')),
)

# Seniority accrual (simplified)
DAILY_DIVISOR = Decimal('22')      # working days per month
SENIORITY_DAYS_PER_YEAR = Decimal('15')
