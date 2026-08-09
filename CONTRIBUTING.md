# Contributing

Thanks for your interest! This project is a transparent CMA engine, and the
contribution rules exist to protect that transparency.

## Ground rules

1. **No black boxes.** Every number a user sees must be explainable: a
   component breakdown, visible unit math, or an audit event. Features that
   produce unexplained values (including ML-derived estimates without
   attribution) are out of scope for this codebase.
2. **Calculation changes are versioned.** If you change any behavior in
   `backend/app/services/`, bump `CALC_VERSION` in `backend/app/constants.py`
   and update `docs/METHODOLOGY.md` in the same PR. Tests enforce the documented
   behavior; change both together.
3. **No real data.** Sample/fixture data must be clearly synthetic. Never commit
   real sales records, client addresses, MLS exports, credentials, or API keys.
4. **No ToS violations.** Scrapers or integrations that bypass authentication,
   bot protection, paywalls, or rate limits will not be merged.

## Development setup

See the README's *Local setup*. Quick loop:

```bash
# backend
cd backend && source .venv/bin/activate
pytest && ruff check app tests

# frontend
cd frontend
npm test && npm run lint && npm run typecheck
```

## Pull requests

- Branch from `main`; keep PRs focused.
- Fill in the PR template checklist (tests, lint, methodology sync, no secrets).
- Add tests for new behavior, calculation edge cases especially (missing data,
  zero/invalid inputs, single-item collections, extreme values).
- UI work: keep the accessibility bar (labeled controls, visible focus,
  `role="alert"` for errors, table semantics, text alternatives for charts).

## Reporting bugs

Use the bug template. For calculation bugs, include the similarity breakdown /
adjustment grid / audit trail contents. That's what they're for.

## Code style

- Python: Ruff (config in `backend/pyproject.toml`), type hints required on
  public functions, calculation logic stays in `app/services/` (pure functions).
- TypeScript: ESLint + strict TS; presentational components take data via props
  so they stay testable without network mocks.
