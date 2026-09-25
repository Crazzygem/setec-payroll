# DESIGN.md: Payroll KH

Design direction for this project. This file holds design fields (data to apply):
identity, palette, typography, mood, dials. It is authored by the product owner.

## Identity

Product: **Payroll KH**. A trustworthy Cambodian payroll system for small
organizations. Precise, local (KHR, NSSF, GDT), understated confidence.
Payroll accuracy comes before decoration.

## Personality / Mood

Precise, trustworthy, understated. A finance tool that feels accurate before it
feels flashy. Confidence without decoration. Calm density: money data is meant
to be scanned, verified, and printed.

## Palette

- Accent: **emerald green** (money / growth association)
  - accent: `#059669`
  - accent for white text (buttons, active nav): `#047857` (passes WCAG AA at 4.5:1)
  - accent soft background: `#ECFDF5`
- Neutrals (unchanged from build): background `#F8FAFC`, surface `#FFFFFF`,
  border `#E5E7EB`, text `#111827`, muted text `#6B7280`
- Sidebar: dark neutral `#111827`
- Cap: 2-3 core colors + 1 accent. Neutrals do not count toward the cap.

## Typography

**IBM Plex Sans** for headings and body (single family).

- Reason: engineered precision, built for data-dense interfaces, excellent
  tabular numerals for money columns.
- Tabular figures (`font-feature-settings: "tnum" 1`) in all tables and money
  fields so column digits align.
- Loaded from Google Fonts.

## Dials

`Dial: ENERGY 1 / RHYTHM 2 / MOTION 1`

- **ENERGY 1**: calm. The page says hello quietly. No hero gestures.
- **RHYTHM 2**: consistent layout with a few deliberate breaks (the printable
  payslip breaks from the app shell; dashboard stat row breaks from tables).
- **MOTION 1**: hover states and state transitions only. No scroll animation,
  no loops, no parallax.

## Content requirements

- Currency shown in KHR with thousands separators everywhere.
- Dense, scannable tables are the primary surface.
- The printable A4 payslip is a document layout of its own, not an app screen.

## Icons

Bootstrap Icons, chosen for content relevance (reason recorded per R-31):
bi-speedometer2 = Dashboard, bi-people = Employees, bi-cash-stack = Payroll
runs, bi-wallet2 = product brand (a payroll system holds money). No decorative
icons, no emoji.
