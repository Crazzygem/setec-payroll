# 5-Minute Demo Script

**Setup before the demo** (once):
```bash
source .venv/bin/activate
python manage.py seed_demo     # already run; safe to re-run any time
python manage.py runserver
```
Open http://127.0.0.1:8000/ and sign in with `hr` / `payroll2026`.

---

## Walkthrough

1. **Dashboard (30 s)**: headcount 8, latest run September 2026,
   gross 40,650,000 KHR, tax withheld with the GDT due date (20 Oct 2026),
   recent-runs list.

2. **Employees (60 s)**: search "manager", click a row to open the edit
   modal (show the Department/Position dropdowns and Delete in the modal
   footer), open Add Employee, edit EMP001's allowance. Then Organization →
   Departments: add "Legal", show it in the employee dropdown, delete it
   again. Point out KHR formatting.

3. **Payroll runs (90 s)**: the Payroll Runs list shows Aug (finalized) and
   Sep (draft) with totals. Open **September**:
   - Totals cards: gross / NSSF / tax withheld / net / employer cost
   - Banner: "salary tax must be paid to GDT by 20 Oct 2026"

4. **The engine (90 s)**: in the Sep table, open **Extras** for EMP001,
   set Overtime to `150000` and **Recalculate**. Net updates to 2,277,700.
   Then hand-verify on screen:
   ```
   gross 2,350,000 - NSSF 47,000 (2%) - tax 25,300 = net 2,277,700
   taxable 2,003,000 -> 25,000 (5% band) + 3,000 x 10% = 25,300
   ```

5. **Payslip (60 s)**: open EMP001's payslip, show the breakdown
   (earnings, deductions, employer contributions, seniority memo),
   click **Print / Save PDF** to show the A4 layout.

6. **Finalize (30 s)**: back to September, **Finalize run**, status flips to
   green, edit buttons disappear (locked), success message shows the GDT
   deadline.

7. **If asked about tests**: `python manage.py test` shows 46 tests,
   including hand-computed tax band boundaries.

8. **If asked about design**: `DESIGN.md` holds the direction (emerald accent,
   IBM Plex Sans, ENERGY 1 / RHYTHM 2 / MOTION 1); `anti-slop/` holds the
   audit report from the antislop quality pass.

---

## Talking points

- All tax/NSSF rates sourced from PwC Tax Summaries (Cambodia), 2026-09-25.
- Seniority accrual is a simplified academic model, clearly labelled on the payslip.
- Money is `Decimal` throughout, no floating point.
- Responsive off-canvas navigation, Escape closes modals, AA contrast verified.

## Submission checklist

- [ ] `python manage.py test` shows 46 OK (run once right before submitting)
- [ ] `python manage.py seed_demo && python manage.py runserver` demo works
- [ ] Screenshots added to README (dashboard, employees, run detail, payslip)
- [ ] Demo video recorded (5 min, follow this script)
- [ ] Zip source: exclude `.venv/` (`db.sqlite3` optional, seed recreates it)
- [ ] Git history: clean commits, no secrets
