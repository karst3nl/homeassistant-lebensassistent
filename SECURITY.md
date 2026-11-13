# Security and privacy

The repository is **public**. All tests and documentation must use fabricated data.

Never commit real finance exports, account balances, salary records, personal names, addresses, vehicle registration plates, bank transactions, production databases, HA access tokens, local URLs, passwords, secrets, or backups.

Git ignore patterns are only a safeguard; inspect the staged diff and run a secret scan before pushing. If sensitive material is identified, stop and clean the commit before publishing. Removal of a file alone does not erase it from Git history.

The application must use Home Assistant Ingress correctly, with no unprotected finance API port. Keep runtime data in persistent `/data`, limit container capabilities, avoid logging financial payloads, and test unauthorized access.

Do not post secret-bearing vulnerability reports publicly. Add a secure disclosure channel before accepting detailed external security reports.
