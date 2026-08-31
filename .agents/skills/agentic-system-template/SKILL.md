---
name: agentic-system-template
description: Establish or maintain a concrete persistent Agentic System when a capability must own several responsibilities, operational truth, evidence, evaluation, and failure/recovery across outcomes. Do not use for an ordinary one-off Project or an instruction-only Skill.
---

# Agentic System Template

Use this route only when the owner intends an independently operable System,
not merely a reusable method or one bounded Project.

## Method

1. Clarify the owner, purpose, operating boundary, and concrete responsibilities.
   Stop or route to a Skill or Project if independent persistent operation is
   not justified.
2. Inspect existing owner-local instructions, workspace truth, prior evidence,
   failures, and recovery state before changing the System.
3. Define only the workspace truth the capability needs to continue operating.
   Choose its files, directories, or other durable state from the domain; do
   not introduce a template-wide layout, ledger, schema, database, or runtime.
4. Define the actual repeatable operations, their inputs and outputs, tool and
   authority boundaries, stop conditions, and the proof needed for consequential
   actions.
5. Attach System-local evaluation only where an observable checkpoint needs it.
   Record the subject, criteria, evidence, outcome, and next action in the form
   the owning System can inspect and maintain.
6. Preserve material failures without rewriting them. When recovery is needed,
   retain the failed evidence and record the correction or replay relation needed
   to understand what changed.
7. Operate or validate the System through its real interfaces. Return the
   completed evidence, gaps, and remaining owner action without manufacturing
   generic demo state.

## Ownership boundary

The concrete System owns its domain criteria, skills, workspace truth, and
evolution. Adoption creates no dependency on this repository or an AIOS
runtime, and this template does not overwrite the adopted System later. Use
`audit-system` separately when accumulated-state inspection is requested.
