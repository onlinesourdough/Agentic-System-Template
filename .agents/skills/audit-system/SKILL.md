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
2. For `repository` or `both`, require the exact Git top-level, an attached
   branch tracking its same-named upstream branch, one credential-free fetch
   and push identity, and the complete staged, unstaged, and untracked state.
   Read the exact upstream branch freshly into an ephemeral bare repository;
   do not update the audited repository's objects, refs, index, or worktree.
3. Compare the exact local and fresh-live commit IDs and report exactly
   `equal`, `behind`, `ahead`, or `diverged`. A cached tracking ref and a clean
   status are evidence, but are never substitutes for the fresh live read.
4. Run `python3 workspace/engine/audit_system.py --scope <scope>`.
5. Return the reported `PASS`, `FAIL`, or `BLOCKED` with its evidence, gaps,
   and next action. Missing or ambiguous access, a detached or unexpected
   branch, a missing upstream, or an unprovable live object cannot PASS.
6. Route a finding to the owning Build/Review lifecycle, or to AIOS
   improvement triage when that is where the work originated.

The audit starts and remains read-only. It performs no fast-forward, pull,
commit, push, stash, rebase, merge, force operation, issue action, run, ledger
line, example, repair, or other external action. Its local criteria and
fixtures belong to System Template. A concrete System owns its domain criteria
and explicitly decides whether to adopt this pattern.
