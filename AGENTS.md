# Repository Working Instructions

- Before making changes in this repository, read `C:\Dev\Xantara-POS-project-knowledge.md` for shared Xantara POS product context, architectural constraints, and production-readiness assumptions.
- After every meaningful code, schema, configuration, API, security, architecture, or operational change, update that knowledge file in the same task. Keep entries factual and based on the current code and verification results.
- When the knowledge file conflicts with executable code or tests, treat the code and tests as authoritative and correct the knowledge file.
- Preserve the POS invariants in the shared knowledge file, especially invoice immutability, integer money, branch-scoped inventory, atomic business operations, explicit authorization, and safe handling of secrets.
