# Payroll Management (Django) - Final Project Build Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Deliver a demo-ready Django web app for Cambodian payroll management - employee CRUD, a monthly payroll run with verified Cambodia NSSF + salary-tax calculations, printable payslips - built overnight for submission tomorrow (2026-09-26).

**Architecture:** Single Django project, three apps (`core`, `employees`, `payroll`). SQLite, Django auth (single HR-admin role), server-rendered templates + Bootstrap 5 CDN, modal CRUD. All payroll math lives in one pure module (`payroll/engine.py`) so it is unit-testable and is the academic centerpiece.

**Tech Stack:** Python 3.12+, Django 5.x, SQLite, Bootstrap 5 (CDN), Chart.js (CDN, dashboard only), Google Fonts (Sora + Jakarta), pytest optional (default: Django test runner).

---

## Context & assumptions

- Solo project, no formal brief → we define scope; grading will look for: working CRUD, real business logic (the tax engine), clean UI, demo-able flow.
- Deadline: tomorrow. Current time at planning: 2026-09-25 22:23. Overnight = core build; early morning = demo prep.
- Amounts in **KHR** (tax table is KHR-denominated; avoids an FX module - YAGNI).
- Cambodia-specific rules **verified via PwC Tax Summaries (2026-09-25 fetch)**:
  - Monthly salary tax, residents (marginal bands):

    | Monthly taxable salary (KHR) | Rate |
    | --- | --- |
    | 0 – 1,500,000 | 0% |
    | 1,500,001 – 2,000,000 | 5% |
    | 2,000,001 – 8,500,000 | 10% |
    | 8,500,001 – 12,500,000 | 15% |
    | Over 12,500,000 | 20% |

  - Non-residents: flat 20% (stretch feature).
  - Fringe benefits: flat 20% (stretch feature).
  - Dependent deduction: **KHR 150,000/month** per dependent spouse/child.
  - NSSF (first-stage pension, current): **employee 2%** (pension only - healthcare is 100% employer-borne since 2018, ORC is employer-only). **Employer 5.4%** = 0.8% occupational risk + 2.6% healthcare + 2.0% pension.
  - Tax withheld must be remitted to GDT **by the 20th of the following month** (monthly declaration).
  - Cash salary = remuneration + wages + bonuses + overtime.
- **NOT verified (flagged in UI/README as simplified academic model):** seniority indemnity. Modeled as accrual: 15 days' base wage per year of service → monthly provision = `base/22 × 15/12`. All rates in one editable file so the lecturer can see the assumptions.
- Dev-work note: per Seth's standing rule, repo dev work normally goes through OpenCode. This is a greenfield school folder (no git repo yet) - confirm build channel at approval.

## Scope tiers (the deadline contract)

- **CORE (must ship → demoable):** Phases 0–3 + seed data. Employees CRUD, payroll engine + tests, monthly run, printable payslip, login.
- **PLUS (if time):** Phase 4 dashboard + month summary report.
- **STRETCH (only if everything else is green):** non-resident 20%, fringe-benefit line, CSV export of the run, Chart.js department chart.
- **CUT (do not start):** attendance, loans/advances repayment schedules, multi-company, PDF libraries (weasyprint/wkhtmltopdf), roles/permissions, email, REST API, Docker.

---

## Data model (`employees/models.py`, `payroll/models.py`)

```
Employee:   emp_id (unique, e.g. EMP001), first_name, last_name, position,
            department, hire_date, contract_type (FIXED|UNSPECIFIED),
            base_salary (KHR, Decimal), allowance_monthly (KHR),
            dependents (int ≥0), is_resident (bool, default True),
            nssf_member (bool, default True), is_active (bool)
PayrollRun: year, month (unique_together), status (DRAFT|FINALIZED), created_at
Payslip:    run FK, employee FK (unique_together), base, allowance, overtime,
            bonus, gross, nssf_employee, dependent_allowance, taxable,
            salary_tax, advances, net, nssf_employer, seniority_accrual,
            computed_at   (all Decimal KHR; snapshot, never recomputed in place)
```

## Payroll engine (`payroll/engine.py`) - the graded centerpiece

Pure functions, `Decimal` only (never float - money):

```python
from decimal import Decimal

# Sources: PwC Tax Summaries Cambodia (fetched 2026-09-25). Editable assumptions.
NSSF_EMPLOYEE_RATE  = Decimal("0.02")   # pension, first stage (2% employee)
NSSF_EMPLOYER_RATE  = Decimal("0.054")  # 0.8 ORC + 2.6 healthcare + 2.0 pension
DEPENDENT_ALLOWANCE = Decimal("150000") # KHR per dependent per month
DAILY_DIVISOR       = Decimal("22")     # working days for daily-rate math
SENIORITY_DAYS_PER_YEAR = Decimal("15") # simplified - verify Prakas 127/17

SALARY_TAX_BANDS = [  # (upper_bound KHR or None, rate) - marginal
    (Decimal("1500000"),  Decimal("0")),
    (Decimal("2000000"),  Decimal("0.05")),
    (Decimal("8500000"),  Decimal("0.10")),
    (Decimal("12500000"), Decimal("0.15")),
    (None,                Decimal("0.20")),
]

def salary_tax(taxable):
    tax, lower = Decimal("0"), Decimal("0")
    for upper, rate in SALARY_TAX_BANDS:
        if taxable <= lower:
            break
        slice_upper = taxable if upper is None else min(taxable, upper)
        tax += (slice_upper - lower) * rate
        lower = upper if upper is not None else taxable
    return tax

def calculate_payslip(*, base, allowance=Decimal("0"), overtime=Decimal("0"),
                      bonus=Decimal("0"), advances=Decimal("0"),
                      dependents=0, nssf_member=True, is_resident=True):
    gross = base + allowance + overtime + bonus
    nssf_employee = (gross * NSSF_EMPLOYEE_RATE) if nssf_member else Decimal("0")
    dependent_allowance = DEPENDENT_ALLOWANCE * dependents
    if is_resident:
        taxable = max(gross - nssf_employee - dependent_allowance, Decimal("0"))
        tax = salary_tax(taxable)
    else:
        taxable, tax = gross, gross * Decimal("0.20")   # stretch: flat non-resident
    net = gross - nssf_employee - tax - advances
    return { ...all fields..., "nssf_employer": gross * NSSF_EMPLOYER_RATE,
             "seniority_accrual": (base / DAILY_DIVISOR) * SENIORITY_DAYS_PER_YEAR / 12 }
```

**Worked example to sanity-check by hand (put in README + tests):**
Employee: base 2,000,000, allowance 200,000, dependents 2, nssf_member.
gross = 2,200,000 → nssf_employee = 44,000 → dependent_allowance = 300,000
taxable = 1,856,000 → tax = (1,856,000−1,500,000)×5% = 17,800
net = 2,200,000 − 44,000 − 17,800 = 2,138,200 (advances 0)
nssf_employer = 118,800 → total employer cost = 2,318,800.

---

## Phased build (each phase ends with a verification checkpoint)

### Phase 0 - Scaffold (30 min)
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install django && pip freeze > requirements.txt`
3. `django-admin startproject payroll_project .` then `python manage.py startapp core employees payroll`
4. `settings.py`: `INSTALLED_APPS += core, employees, payroll`; `LANGUAGE_CODE="en-us"`; `TIME_ZONE="Asia/Phnom_Penh"`; `LOGIN_URL="/accounts/login/"`; `LOGIN_REDIRECT_URL="/"`.
5. `templates/layouts/base.html`: Bootstrap 5 CDN, fonts Sora (headings) + Jakarta (body), sidebar nav (Dashboard / Employees / Payroll), `{% block content %}`. Compact density, KHR formatting via `django.contrib.humanize|intcomma`.
6. `git init && git add -A && git commit -m "chore: scaffold payroll project"` (commit after every phase).
**Verify:** `python manage.py runserver` → base page renders with sidebar.

### Phase 1 - Employees CRUD (1.5 h)
1. `Employee` model + migration (constraints: `base_salary > 0`, `dependents >= 0`).
2. `EmployeeForm` (ModelForm) + list view with search (`?q=` filters name/emp_id) + add/edit **Bootstrap modal**, delete with confirm modal. All views `@login_required`.
3. Django auth: `accounts/login.html` (Bootstrap card login), logout; create superuser + one demo HR user via seed (Phase 5).
**Verify:** create EMP001–EMP003 in UI; edit salary; delete one; search finds them; direct URL without login redirects to login.

### Phase 2 - Payroll engine + tests (2.5 h) - highest grading value, do not rush
1. `payroll/rules.py` (constants above) + `payroll/engine.py` (`salary_tax`, `calculate_payslip`).
2. `payroll/tests/test_engine.py` - write tests FIRST, watch them fail, then implement:
   - boundary 1,500,000 taxable → 0 tax; 1,500,001 → ~0.05 KHR-rounded
   - 2,000,000 → 25,000 | 8,500,000 → 675,000 | 12,500,000 → 1,275,000 (hand-computed)
   - above top band: 20,000,000 → 1,275,000 + 7,500,000×20% = 2,775,000
   - dependent allowance reduces tax; tax never negative
   - NSSF employee 2% / employer 5.4%; non-member pays 0
   - net identity: `net == gross - nssf_employee - tax - advances`
   - worked example above returns exactly the hand-computed numbers
   - zero-salary / all-zero inputs don't crash
3. Money rounding: quantize to whole KHR (`Decimal.quantize(1)`) at payslip-field level only.
**Verify:** `python manage.py test payroll -v 2` → all PASS.

### Phase 3 - Payroll run + payslips (2 h) - core end of demo
1. Models `PayrollRun`, `Payslip`; `generate_run(year, month)` service: one payslip per active employee, snapshot fields, idempotent (skip if exists), run stays DRAFT.
2. Views: runs list; create run (month picker, blocks duplicate month); run detail = table of employees with gross/tax/net + row action "View payslip"; per-payslip modal edit for overtime/bonus/advances **before finalize**; "Finalize" button (locks edits) with the "GDT payment due by the 20th" banner.
3. Payslip page: printable A4 HTML (`@media print`, "Print" button via `window.print()`), company header, full breakdown incl. NSSF both shares + seniority accrual memo + employer cost total.
**Verify:** generate 2026-09 run for seeded employees; open payslip; browser print preview looks like a payslip; finalize locks editing.

### Phase 4 - Dashboard + report (1.5 h) - PLUS tier
1. Dashboard cards: active employees, this-month gross payroll, total salary tax withheld (the GDT liability), employer NSSF cost; last run link.
2. Run detail totals footer (gross / total tax / total net / employer cost) - this doubles as the "report".
3. Optional: Chart.js bar (payroll by department).
**Verify:** totals on dashboard equal the sum of payslip rows (spot-check one month by hand).

### Phase 5 - Seed data + polish (1 h)
1. `core/management/commands/seed_demo.py`: 8 employees (mixed departments, salaries spanning all 5 tax bands, 0–3 dependents, 1 non-member), 1 DRAFT run (2026-09) + 1 FINALIZED run (2026-08). Demo user `hr / (created at runtime, printed, never committed)`.
2. Empty states, flash messages, consistent KHR formatting (`1,500,000 KHR`), README (setup, features, calculation rules + sources, screenshots, simplified-assumptions disclaimer).
**Verify:** `python manage.py flush && python manage.py seed_demo && python manage.py test` → clean demo + green tests.

### Phase 6 - Demo & submission (1 h, early morning)
1. Demo script (5 min): login → dashboard → add employee → generate Sep run → edit one OT → show payslip breakdown + hand-check math → finalize → show Aug finalized run.
2. 3–5 min screen recording; screenshots for README; zip source (exclude `.venv/`, `db.sqlite3` optional - seed script makes DB reproducible).

---

## Files likely to change

```
Final-Payroll_MGM/
├── manage.py, requirements.txt, README.md, .gitignore
├── payroll_project/settings.py, urls.py
├── core/                       # dashboard + seed_demo command
├── employees/                  # models.py, forms.py, views.py, urls.py, templates/employees/
├── payroll/
│   ├── rules.py                # ALL rates/assumptions + sources (single editable file)
│   ├── engine.py               # pure calculation functions
│   ├── services.py             # generate_run(), finalize_run()
│   ├── models.py, views.py, urls.py
│   ├── tests/test_engine.py
│   └── templates/payroll/      # run_list, run_detail, payslip.html (printable)
└── templates/layouts/base.html, templates/registration/login.html, static/
```

## Risks & open questions

- **Exact submission hour unknown** - scope tiers above are the contract; CORE is demo-able even if Phases 4–6 shrink.
- **Seniority indemnity** is an unverified simplification (Prakas 127/17 not reachable tonight) → visibly labeled "simplified academic model" in code, payslip, README. Do not present it as legal advice.
- **NSSF contributory wage ceiling** not verified → no cap applied; noted in `rules.py`.
- Rounding: whole-KHR quantize may drift ±1 KHR vs hand math on odd inputs - tests use clean numbers.
- Build channel: repo dev normally goes to OpenCode (standing rule). Options for tonight: (a) OpenCode drives the build from this plan, (b) Hermes scaffolds directly (greenfield school project, speed). Seth decides at approval.
