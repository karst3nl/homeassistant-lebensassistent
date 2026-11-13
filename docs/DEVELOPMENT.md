# Development policy

## Branches

- `alpha` is the **only active development branch** until the full v1.0 application is complete and tested.
- `main` remains a minimal stable placeholder and must not receive development commits.
- Changes, tests and application docs are committed to `alpha`.
- After the release acceptance checklist has passed, merge `alpha` into `main` through a reviewed pull request. Never auto-merge.

## Privacy

- Use synthetic data only in tests, screenshots and documentation.
- Never commit real account balances, salaries, bank records, names, vehicle registration plates, API credentials, actual Home Assistant configuration or application databases.
- Review staged changes before each push. `.gitignore` is not sufficient protection for already tracked files.
- Runtime data must be stored in Home Assistant persistent storage, not in the repository.

## Scope

The intended app covers accounts and transactions, recurring expenses, savings goals, vehicle expenses and refuelling, projects, timesheets, notifications, and a configurable dashboard.

The functional specification must be sanitized before publishing, including examples and metadata.
