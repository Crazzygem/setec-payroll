# 5-Minute Demo Script

**Setup before the demo** (once):
```bash
source .venv/bin/activate
python manage.py seed_demo     # already run — safe to re-run any time
python manage.py runserver
```
Open http://127.0.0.1:8000/ → login `hr` / `payroll2026`.

---

## Walkthrough

1. **Dashboard (30 s)** — headcount 8, latest run September 2026,
   gross 40,650,000 KHR, tax withheld with the GDT due date (20 Oct 2026).

2. **Employees (60 s)** — search "manager", open **Add Employee** modal
   (show the form: salary, dependants, NSSF flags), edit EMP001's allowance,
   mention delete confirm modal. Point out KHR formatting.

3. **Payroll runs (90 s)** — Payroll Runs list shows Aug (finalized) and
   Sep (draft) with totals. Open **September**:
   - Totals cards: gross / NSSF / tax withheld / net / employer cost
   - Banner: *"salary tax must be paid to GDT by 20 Oct 2026"*

4. **The engine (90 s)** — in the Sep table, open **Extras** for EMP001,
   set Overtime `150000` → **Recalculate**. Net updates to 2,277,700.
   Then hand-verify on screen:
   ```
   gross 2,350,000 − NSSF 47,000 (2%) − tax 25,300 = net 2,277,700
   taxable 2,003,000 → 25,000 (5% band) + 3,000×10% = 25,300
   ```

5. **Payslip (60 s)** — open EMP001's payslip, show the breakdown
   (earnings, deductions, employer contributions, seniority memo),
   click **Print / Save PDF** to show the A4 layout.

6. **Finalize (30 s)** — back to September → **Finalize run** →
   status flips to green, edit buttons disappear (locked), success
   message shows the GDT deadline.

7. **If asked about tests** — `python manage.py test` → 33 tests,
   including hand-computed tax band boundaries.

---

## Talking points

- All tax/NSSF rates sourced from PwC Tax Summaries (Cambodia), 2026-09-25.
- Seniority accrual = simplified academic model, clearly labeled on payslip.
- Money is `Decimal` throughout — no floating point.
- Design: Sora/Jakarta typography, compact layout, modal CRUD.

## Submission checklist

- [ ] `python manage.py test` → 33 OK (run once right before submitting)
- [ ] `python manage.py seed_demo && python manage.py runserver` → demo works
- [ ] Screenshots added to README (dashboard, employees, run detail, payslip)
- [ ] Demo video recorded (5 min, follow this script)
- [ ] Zip source: exclude `.venv/` (`db.sqlite3` optional — seed recreates it)
- [ ] Git history: 6 clean commits, no secrets
