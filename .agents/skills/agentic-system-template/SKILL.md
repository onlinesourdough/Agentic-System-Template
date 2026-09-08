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
4. For a material business, product, architecture, or trust decision, inspect
   actual constraints and reasonable alternatives. Retain its context, rationale,
   consequences, and supersession history when it changes in the owner-chosen
   source of truth; ask only for genuinely missing authority or a decision.
   Execute an obvious authorized step.
5. Define the actual repeatable operations, their inputs and outputs, tool and
   authority boundaries, stop conditions, and the proof needed for consequential
   actions. Keep affected operational documentation current and make the
   responsible source of truth clear without prescribing an ADR or directory.
   Safe independent work may proceed in parallel; urgency does not skip evidence,
   review, data protection, or lifecycle cost.
6. For a defect, validate affected behavior at the nearest safe representative
   boundary before correction. If original behavior cannot be reproduced, report
   that as an evidence gap and use the closest safe evidence, then retain
   meaningful regression or domain proof. Do not weaken coverage merely to pass.
   Software Systems do not require browser E2E when another boundary is
   representative; content, design, and data Systems use relevant domain proof.
   A legitimate contract change retains explicit rationale and replacement
   coverage.
7. Protect secrets and private data in outputs, records, examples, and fixtures;
   use synthetic data and only required access. When the System actually owns
   software or data changes, favor existing maintainable patterns, clear
   responsibility, and comments only for non-obvious intent. For data, schema,
   RLS, permission, or refresh changes, name the exact target, scope, action
   authority, verification, and recovery or restore limitation. Use the owning
   stack's existing reviewable change mechanism, prefer read-only inspection,
   test only in an authorized isolated target, and do not infer production
   mutation authority from development authority.
8. Attach System-local evaluation only where an observable checkpoint needs it.
   Record the subject, criteria, evidence, outcome, and next action in the form
   the owning System can inspect and maintain.
9. Preserve material failures without rewriting them. When recovery is needed,
   retain the failed evidence and record the correction or replay relation needed
   to understand what changed.
10. Operate or validate the System through its real interfaces. Before handback,
    inspect final bytes and affected behavior or documentation; label inspection,
    execution, synthetic, and operational proof, along with gaps and remaining
    owner action, without manufacturing generic demo state. Return it clearly in
    the user's language and at the requested depth.

## Ownership boundary

The concrete System owns its domain criteria, skills, workspace truth, and
evolution. Adoption creates no dependency on this repository or an AIOS
runtime, and this template does not overwrite the adopted System later. Use
`audit-system` separately when accumulated-state inspection is requested.
