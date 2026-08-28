# Contract

## Vocabulary

The first-class AIOS concepts are:

| Concept | Meaning |
| --- | --- |
| Space | Persistent business/domain context in which work is situated. |
| System | The persistent agentic capability that performs or routes work. |
| Project | A bounded, self-owning outcome created from owner intent. |

Template, resource, archive, and skill are supporting constructs. The
filesystem uses them without promoting them to new AIOS concepts.

## System and Skill boundary

A Skill is an instruction or method with clear inputs, steps, proof, and stop
conditions when it does not need independent persistent operation. Scripts or
references can support that method without making a System; neither a long
Skill nor supporting scripts alone creates one.

A System is justified when one reusable capability must operate independently
across multiple runs or outcomes and materially own several responsibilities
it needs as one cohesive operational responsibility. Evidence can include
tooling, workspace state, run relations, local validation, domain review,
evidence, and failure/replay handling. This is evidence, not an all-fields
checklist: each System owns the several concerns its independent operation
materially requires. The primary skill is its concise route, not a duplicate
of the engine, local contract, ledger, or technical docs.

## Operational truth

`workspace/` is the persistent operational surface:

| Path | Purpose |
| --- | --- |
| `workspace/runs/` | Durable evidence for each route attempt. |
| `workspace/history/runs.jsonl` | Append-only relation between runs. |
| `workspace/learning/` | Durable notes intentionally retained for future work. |
| `workspace/engine/` | Optional technical implementation of this reference. |

Each ledger object has these fields:

```text
run_id
started_at
finished_at
status
input_ref
output_ref
proof_ref
evaluation
previous_run_id
previous_run_relation
failure
recovery
```

The values are references and small structured facts. Input text is not
transcribed into the ledger. A failed attempt is retained; a later recovery is
a new append with a relation to that attempt and its own evidence file.
`previous_run_relation` is `null` for the first relevant run, `predecessor`
for an ordinary continuation, and `recovery` when the route explicitly
recovers an unresolved failed predecessor. Each failed run can be the target of
at most one recovery record.

`evaluation` is a small reference and outcome for the route's local semantic
eval. It is separate from deterministic output-shape validation. The demo eval
records its subject, exact checkpoint, observable checks, required evidence,
and failure action in `workspace/runs/<run-id>/evaluation.json`. It checks only
the demo route's required completion result; this seed does not claim a
universal semantic rubric. A failed eval leaves the structurally valid output
unchanged, records failure evidence, and is replayed only from a new recovery
run with a relation to the failed predecessor.

The eval reference must resolve to an existing JSON object inside its owning
run directory. Its outcome must agree with the ledger outcome and run status,
and its `output_ref` must agree with the ledger output reference. These local
integrity checks keep the eval chain inspectable without imposing a general
reference-validation framework.

## Read-only accumulated-state audit

`audit-system` is a separate route from per-run semantic eval and per-change
Review. A semantic eval judges one output at one checkpoint; Review assesses a
proposed change; the audit reads accumulated current System truth and proof for
drift. Its explicit scope is `repository`, named `demo-route`, or `both`; it
inspects only evidence relevant to that selected scope.

The reference returns exactly `PASS`, `FAIL`, or `BLOCKED` with scope, concise
evidence, evidence gaps, and the smallest next action. `BLOCKED` means required
scoped evidence is unavailable, never an assumed pass. The audit is read-only:
it creates no run, ledger record, example, repair, issue, or external action.
Failures route to the owning Build/Review lifecycle, or to AIOS improvement
triage when work originated there. It is a System Template-local reference,
not a universal audit contract for other Systems. Downstream adoption remains
an explicit decision for each owning System after this generic proof; this seed
creates no speculative downstream copy.

For `repository` and `both`, currentness evidence includes the exact Git
top-level, attached branch and its same-named upstream branch, one
credential-free fetch and push identity, and complete staged, unstaged, and
untracked status. The implementation reads the exact live upstream branch into
an ephemeral bare repository, reads the local branch into that same temporary
object graph, and reports exact local, cached-tracking, and fresh-live commit
IDs with one relation: `equal`, `behind`, `ahead`, or `diverged`. It never
fetches into or updates the audited repository. Therefore a clean worktree and
a cached tracking ref are not live proof. A dirty state or non-equal relation
is `FAIL`; missing or ambiguous access, detached or unexpected branch state,
missing upstream configuration, or an unprovable live object is `BLOCKED`.

This is a System Template-local reference pattern, not a cross-repository
dependency or parity obligation. A concrete System owns its domain criteria
and explicitly adopts any useful part of the pattern; the template does not
become its currentness owner. No global schema, central ledger, sync service,
or downstream repair path is introduced.

For `demo-route`, the audit treats failure and recovery as discoverable only
when their referenced JSON objects stay inside the owning run directory, exist,
and identify the failed run/eval failure or recovery run/failed predecessor
consistently. Missing required artifacts are `BLOCKED`; escaping, malformed, or
contradictory artifacts are `FAIL`.

## Promotion boundary

`examples/` is not a scratch directory. Every example is a deliberately
curated, standalone proof with a local `README.md` and `proof.json`. The
reference tracer writes one only after the `--promote-example` choice. A run
can be valid operational truth without being promoted. A failed eval cannot be
promoted as successful proof.

## Public shape

The only visible functional roots are `workspace/`, `examples/`, and `docs/`.
The root shell is `AGENTS.md`, `README.md`, and the hidden primary skill path
`.agents/skills/system-template/SKILL.md`. Technical implementation belongs
under `workspace/engine/`; this seed is copied or read as a reference and is
not imported by a running AIOS system.
