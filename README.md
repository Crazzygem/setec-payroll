# Payroll KH

A Django web application for monthly payroll processing in Cambodia:
employee records, automatic salary calculation using Cambodian NSSF and
Tax-on-Salary rules, monthly payroll runs, and printable payslips.

Built as the final project for the Python course.

## Features

- **Employee management**: CRUD with search; click a table row to edit; salary,
  allowances, dependants, NSSF/residency flags, contract type (modal UI).
- **Organization**: departments and job titles managed in-app under the
  Organization sidebar group; the employee form picks from those dropdowns,
  and a list item still in use cannot be deleted.
- **Payroll engine**: pure `Decimal` calculations with unit tests:
  - Progressive monthly salary tax (0% / 5% / 10% / 15% / 20%, marginal)
  - NSSF: 2% employee (pension), 5.4% employer (occupational risk + health + pension)
  - Dependant allowance: KHR 150,000 per dependant per month
  - Non-residents: flat 20%
- **Monthly payroll runs**: one click generates a payslip per active employee;
  edit overtime / bonus / advances while the run is a draft; **finalize** locks it.
- **Printable payslips**: A4 layout, earnings/deductions breakdown, employer
  contributions, print-to-PDF via the browser.
- **Export**: download any run as CSV or formatted Excel (.xlsx) with a totals
  row; money cells are real numbers with `#,##0` formatting (pandas + openpyxl).
- **Dashboard**: headcount, latest run totals, GDT withholding-tax deadline,
  recent payroll runs.
- **Authentication**: login required for every page.
- **Responsive**: off-canvas navigation and 44px touch targets on small screens.

## Tech stack

Python 3.11 · Django 5.2 · SQLite · pandas + openpyxl (exports) · Bootstrap 5 (CDN) · IBM Plex Sans (Google Fonts)

Design direction lives in [DESIGN.md](DESIGN.md): emerald accent, IBM Plex Sans,
dials ENERGY 1 / RHYTHM 2 / MOTION 1.

## Quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo        # 8 employees + Aug/Sep 2026 payroll runs
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign in:

| Username | Password |
|----------|----------|
| `hr` | `payroll2026` |

*(Demo credentials for local coursework use only. Do not deploy publicly.)*

## Run the tests

```bash
python manage.py test
```

46 tests: payroll-engine band boundaries (hand-computed expectations),
payslip math, CRUD, run generation, finalize locking, payslip rendering.

## Calculation rules and sources

| Rule | Value | Source |
|------|-------|--------|
| Resident salary tax (monthly, marginal) | 0% ≤ 1,500,000 · 5% ≤ 2,000,000 · 10% ≤ 8,500,000 · 15% ≤ 12,500,000 · 20% above | [PwC: taxes on personal income](https://taxsummaries.pwc.com/cambodia/individual/taxes-on-personal-income) |
| Non-resident salary tax | 20% flat | same |
| Dependant allowance | KHR 150,000/month per dependant | [PwC: deductions](https://taxsummaries.pwc.com/cambodia/individual/deductions) |
| NSSF employee | 2% (old-age pension, first stage) | [PwC: other taxes](https://taxsummaries.pwc.com/cambodia/individual/other-taxes) |
| NSSF employer | 5.4% (0.8% occupational risk + 2.6% health + 2.0% pension) | same |
| Tax remittance deadline | 20th of the following month | [PwC: tax administration](https://taxsummaries.pwc.com/cambodia/individual/tax-administration) |

All rates live in **`payroll/rules.py`** with their sources documented.

### Worked example (also a unit test)

Employee: base 2,000,000 + allowance 200,000, 2 dependants, NSSF member.

```
Gross cash salary      = 2,200,000
NSSF employee (2%)     =    44,000
Dependant allowance    =   300,000   (2 × 150,000)
Taxable salary         = 1,856,000
Salary tax             =    17,800   (356,000 × 5%)
Net pay                = 2,138,200
Employer NSSF (5.4%)   =   118,800
```

## Known simplifications (academic scope)

- **Seniority accrual** is a simplified memo calculation (15 days of base wage
  per year of service, accrued monthly). It is labelled on the payslip and is
  *not* a legal determination. Verify against the applicable Prakas before any
  real-world use.
- No NSSF contributory-wage ceiling is applied (ceiling not verified for this
  project).
- Single user role (HR admin); no approvals workflow, attendance, or loans.
- Amounts in KHR only.

## Project structure

```
├── manage.py
├── DESIGN.md               # design direction (owner-authored)
├── AGENTS.md               # antislop pointer for AI coding agents
├── anti-slop/              # audit reports
├── payroll_project/        # settings, urls
├── core/                   # dashboard + seed_demo command
├── employees/              # Employee/Department/Position models, CRUD views, tests
├── payroll/
│   ├── rules.py            # all rates & assumptions (with sources)
│   ├── engine.py           # pure calculation functions
│   ├── services.py         # run generation, payslip recalculation
│   ├── models.py           # PayrollRun, Payslip
│   ├── views.py            # runs, extras editing, finalize, payslip print
│   └── tests/              # engine + view tests (46 total incl. employees + exports)
└── templates/              # base layout, login
```
