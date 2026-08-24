# Contract

## Vocabulary

The first-class AIOS concepts are:

| Concept | Meaning |
| --- | --- |
| Space | The boundary in which work is organized. |
| System | The persistent agentic capability that performs or routes work. |
| Project | The bounded outcome being advanced. |

Template, resource, archive, and skill are supporting constructs. The
filesystem uses them without promoting them to new AIOS concepts.

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
previous_run_id
previous_run_relation
failure
recovery
```

The values are references and small structured facts. Input text is not
transcribed into the ledger. A failed attempt is retained; a later recovery is
a new append with a relation to that attempt and its own evidence file.

## Promotion boundary

`examples/` is not a scratch directory. Every example is a deliberately
curated, standalone proof with a local `README.md` and `proof.json`. The
reference tracer writes one only after the `--promote-example` choice. A run
can be valid operational truth without being promoted.

## Public shape

The only visible functional roots are `workspace/`, `examples/`, and `docs/`.
The root shell is `AGENTS.md`, `README.md`, and the hidden primary skill path
`.agents/skills/system-template/SKILL.md`. Technical implementation belongs
under `workspace/engine/`; this seed is copied or read as a reference and is
not imported by a running AIOS system.
