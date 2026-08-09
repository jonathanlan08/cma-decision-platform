# Security & Data Handling

## Reporting a vulnerability

Open a GitHub issue titled "Security report" **without** exploit details and a
maintainer will follow up privately, or use GitHub's private vulnerability
reporting if enabled on the repository. Please do not publish exploits before a
fix lands.

## Threat model (current scope)

The MVP is a local, single-user demo application: no authentication, no
secrets, no third-party data services. The main risks are therefore *data
hygiene* risks:

| Risk | Mitigation |
|---|---|
| Real client data committed to the repo | Bundled data is synthetic by construction; CONTRIBUTING and the PR template forbid real records; `.gitignore` excludes local DB files and `.env` |
| Secrets in git | No secrets exist in the codebase; `.env.example` contains only non-secret defaults; the docker-compose password is a documented local-dev placeholder |
| CSV upload abuse | 2 MB / 500-row limits, strict UTF-8 decode, per-field validation, no formula evaluation (files are parsed with Python's `csv`, never executed or passed to a spreadsheet engine) |
| Injection | SQLAlchemy parameterized queries throughout; Jinja2 autoescape on for the report template; React escapes by default |
| CORS | Restricted to configured origins (`CORS_ORIGINS`) |

## Known gaps (deliberate, documented)

- **No authentication/authorization**: anyone who can reach the API can read
  and modify any analysis. Do not deploy this publicly as-is; auth is on the
  roadmap (v0.4) and the schema is ready for it.
- **No rate limiting**: same deployment caveat.
- SQLite is a local file; protect the host if analyses matter to you.

## Dependency hygiene

- Dependabot monthly grouped updates for pip, npm, and GitHub Actions.
- CI runs lint, type checks, and the full test suite on every PR.

## Data policy

Never commit: real sales/client records, private addresses connected to
clients, MLS credentials or exports, API keys, or brokerage-confidential
information. If any of these ever lands in git history, treat it as an
incident: rewrite history (`git filter-repo`), rotate any credentials, and note
the cleanup in the PR.
