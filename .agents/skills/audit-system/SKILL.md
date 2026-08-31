---
name: audit-system
description: Perform a read-only, agent-led inspection of an explicit concrete System scope using ordinary file, Git, and runtime tools, returning PASS, FAIL, or BLOCKED with evidence and gaps.
---

# Audit System

Use this route to inspect accumulated System state after work has changed or
drift may have developed. It is separate from one-output evaluation and from
per-change Review.

## Method

1. Name one explicit scope and the owning System's applicable criteria. Include
   only the repository, workspace, operation, evidence family, runtime surface,
   or combination actually requested.
2. Identify the required evidence and stop conditions before inspection. Treat
   missing, ambiguous, inaccessible, or unprovable required evidence as a gap;
   never assume it passes.
3. Inspect owner instructions, workspace truth, outputs, evaluation evidence,
   failures, recoveries, and operating proof relevant to the scope with ordinary
   read-only file and runtime tools.
4. When repository currentness is in scope, attest the exact Git root,
   branch/upstream, credential-free remote identity, complete index/worktree
   state, exact local object, and a freshly read live upstream object. Cached
   tracking refs are not live proof. Use a temporary object store if ancestry
   must be established; do not fetch into the audited repository.
5. Compare the observed state with the owning System's documented criteria and
   prior evidence. Cite exact files, objects, commands, or runtime observations
   sufficient to replay the conclusion.
6. Return the scope, status, evidence, evidence gaps, and smallest next action.

## Status and stop behavior

- `PASS`: every required criterion is supported by current evidence.
- `FAIL`: available evidence proves drift, contradiction, or a failed criterion.
- `BLOCKED`: required evidence or safe read access is unavailable or ambiguous.

The audit starts and remains read-only. It performs no repair, run creation,
ledger or example write, issue action, commit, push, pull, fast-forward, stash,
rebase, merge, force operation, deployment, or settings change. Stop and route
findings to the owning lifecycle; the concrete System owns the criteria and any
later authorized repair.
