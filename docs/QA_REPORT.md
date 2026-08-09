# QA & User-Experience Report

Date: 2026-08-08 · Build: `main` (post-v0.1.0, includes proximity map + sensitivity)
Method: full manual click-through of every interactive control as an end user,
plus automated cross-engine and cross-viewport verification. All findings were
fixed in the same pass and re-verified.

## 1. Coverage matrix (what was actually tested — and what wasn't)

| Surface | How it was tested | Status |
|---|---|---|
| Chrome / Edge on Windows·Mac·Linux (Blink engine) | Full manual click-through in Chromium + 2 Playwright e2e journeys | ✅ Pass |
| Safari on Mac / iOS (WebKit engine) | Playwright **WebKit** project — both e2e journeys | ✅ Pass |
| Android phone view (touch, 375×812) | Chromium mobile emulation (Android UA, touch events); layout + interaction spot-checks on all key screens | ✅ Pass |
| Tablet (768×1024) | Viewport emulation, overflow checks | ✅ Pass |
| Desktop (766–1440px) | Primary manual pass | ✅ Pass |
| Firefox (Gecko) | Not tested | ⚠ Untested |
| Real iPhone / Android hardware, real Windows machine | **Not available in this environment** — engine/viewport emulation is a strong proxy but not a substitute for device testing (rendering quirks, soft-keyboard behavior, iOS Safari toolbar resizing) | ⚠ Untested |

Horizontal-overflow check (`document.body.scrollWidth > innerWidth`) was run on
mobile and tablet: **no body-level horizontal scrolling anywhere**; wide tables
scroll inside their own containers as designed.

## 2. What was exercised, control by control

**Dashboard** — create CMA · open existing · stat row · archived toggle · empty
state. **Subject** — empty-submit validation (error + `aria-invalid`), negative
sq ft rejection, full valid save, auto-titling ("CMA — {address}"), redirect to
comparables, prefill on revisit. **Comparables** — CSV template download link ·
CSV upload of the 20-row sample through the real file input (change-event
dispatch) · manual entry form (validation + successful add + form reset) ·
similarity recalculation · score → breakdown expansion · sort headers · text
filter · "included only" · include/exclude toggle · exclusion-reason entry ·
per-comp weight multiplier (verified persisted = 2.0) · two-step delete ·
weights editor. **Adjustments** — assumption edit → save (verified persisted) →
regenerate (82 rows, new $12,000/bedroom value used) · inline amount edit
(verified re-flagged `manual`, audit-logged) · manual add validation · delete.
**Valuation** — calculate · range-width k=1.5 (verified band = ±1.5σ) ·
warnings · chart · influence table · sensitivity panel. **Strategies** —
generate · price edit via blur (verified: price, `is_user_modified`, labels
flipped to Low/High at +6.8%) · price edit via Enter. **Report** — generate ·
open · content spot-check (range, disclaimer, methodology version). **Audit** —
full-trail readability · details expansion (before/after JSON). **Errors** —
nonexistent CMA id → clear error + retry; CSV with bad rows → row-level errors
while valid rows import.

## 3. Findings

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | Cosmetic | Comparables empty-state relied on CSS margin instead of a text space around the file path — fine visually, wrong for copy/paste and screen readers | **Fixed** (real space) |
| 2 | **Bug** | **Sale dates displayed one day early** (e.g. entered Jun 15 → shown "Jun 14"): `new Date("YYYY-MM-DD")` parses as UTC midnight, shifting back a day in timezones west of Greenwich | **Fixed** — date-only strings now parsed as local dates; regression unit tests added (`format.test.ts`) |
| 3 | Moderate | Comparable delete used native `window.confirm`, which some embedded webviews suppress entirely (confirmed in testing: the dialog never appeared, delete silently did nothing) and which cannot be styled or reliably automated | **Fixed** — inline two-step Delete → Confirm/Cancel control; 2 new component tests |
| 4 | Moderate | Pressing **Enter** in a strategy price field routed the commit through `blur()`, which failed to fire in the embedded-webview environment (change silently not saved; blur path worked) | **Fixed** — Enter now commits directly |
| 5 | Cosmetic | Report rendered "Parking — space(s)" when parking was not specified | **Fixed** — renders "—" |

## 4. Verified after fixes

- Backend: **87/87** pytest, ruff clean
- Frontend: **28/28** Vitest (3 new files/cases), ESLint + `tsc --noEmit` clean, production build green
- E2E: **4/4** — both journeys × {Chromium, WebKit}; CI now installs and runs both engines
- Manual re-check of the fixed flows in the browser

## 5. UX observations (deferred, non-blocking)

1. **Focus management on form errors** — failed submits show `role="alert"`
   messages but don't move focus to the first invalid field. Recommended for a
   dedicated a11y pass.
2. **Checkbox touch targets** are 16×16px (standard, but below the 44px ideal
   for touch). Padding-based hit-area enlargement recommended.
3. **Exclusion-reason input** is narrow inside the address cell on small
   screens; usable but cramped.
4. **Similarity breakdown on very narrow screens** requires horizontal
   scrolling of the inner table (by design, but a stacked mobile layout would
   read better).
5. **No dark mode** — the app is light-only by design for now; the report is
   deliberately pinned light.

## 6. User-experience verdict

The workflow holds together end to end for a first-time user: each step
explains itself, empty states say what to do next, warnings are in plain
English, and the audit trail reads like a story of the analysis. The new
[/guide](../frontend/src/app/guide/page.tsx) page closes the remaining gap
(orientation for someone who has never built a CMA). The honest rough edges are
listed above; none block the core workflow.
