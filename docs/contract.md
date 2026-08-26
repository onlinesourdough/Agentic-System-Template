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
