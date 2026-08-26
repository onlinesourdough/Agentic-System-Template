---
name: audit-system
description: Read-only route for checking accumulated System Template drift in an explicit scope.
---

# Audit System reference skill

This concise skill routes a periodic, accumulated-state audit. It is distinct
from a per-run semantic eval and from per-change Review: it reads whether the
current System truth, evidence, recovery relation, and documented local routes
still agree after change has accumulated.

1. Select exactly one scope: `repository`, named `demo-route`, or `both`.
2. Run `python3 workspace/engine/audit_system.py --scope <scope>`.
3. Return the reported `PASS`, `FAIL`, or `BLOCKED` with its evidence, gaps,
   and next action. Do not turn uncertainty into PASS.
4. Route a finding to the owning Build/Review lifecycle, or to AIOS
   improvement triage when that is where the work originated.

The audit starts and remains read-only. It creates no run, ledger line,
example, repair, issue, or external action. Its local criteria and fixtures
belong to System Template; concrete Systems own their own domain criteria.
