# System Template

System Template is the canonical standalone seed and filesystem reference for
persistent Agentic Systems. It is intentionally neutral: a clean clone shows
how operational truth can persist without becoming a runtime framework.

## The model

AIOS has three first-class concepts:

- **Space** — persistent business/domain context in which work is situated.
- **System** — the persistent agentic capability that routes and performs
  work.
- **Project** — a bounded, self-owning outcome created from owner intent.

Template, resource, archive, and skill support those concepts; they are not
additional AIOS types.

## Filesystem contract

Only three visible functional roots are present:

```text
workspace/                         persistent operational truth
├── runs/                           one directory per run
├── history/runs.jsonl              append-only run ledger
├── learning/                       durable learning notes
└── engine/                         optional reference implementation
examples/                           deliberately curated standalone proof
docs/                               public contract and validation notes
```

The root shell is `AGENTS.md`, this file, and the primary System skill at
`.agents/skills/system-template/SKILL.md`. Hidden tool configuration is kept
minimal. The repository is a reference that can be copied or studied; another
system does not need to install or import it to run.

The ledger records a run ID, timestamps, status, input/output/eval/proof
references, the relevant previous run, and failure or recovery evidence. It
does not store raw input text. A run directory is the durable evidence surface;
the ledger points to it rather than becoming a second data store.

## System and Skill boundary

Use a Skill when the reusable value is an instruction or method with clear
inputs, steps, proof, and stop conditions, but no independent operational
responsibility. A long Skill, supporting scripts, and references do not by
themselves make a System.

Use a System when one reusable capability must remain independently operable
across runs and outcomes and materially owns several responsibilities it needs
as one cohesive operational responsibility. Relevant evidence can include
executable tooling, workspace state, run relations, local contracts and
validation, domain-specific review, evidence, and failure/replay handling.
That list is not an all-fields checklist: a System owns the several concerns
its independent operation materially requires. The primary skill is the
concise agent-facing route into that capability; it does not copy the engine,
ledger, contracts, or technical documentation into its instructions.

## Deterministic tracer

The small standard-library tracer demonstrates the complete route:

```text
primary skill → workspace run → output and proof → append-only ledger → curated example
```

Run the demonstration from the repository root:

```sh
python3 workspace/engine/tracer.py --promote-example
```

It inspects prior records for the route, chooses the next deterministic run
ID, writes structured input/output/proof files under `workspace/runs/`,
appends exactly one JSON object to `workspace/history/runs.jsonl`, and then
creates `examples/demo-route/<run-id>/` as an explicit standalone proof.
The default demonstration timestamp is fixed; `--timestamp` can supply an
ISO-8601 UTC value for another deterministic fixture.

Each route first validates its small local output shape, then records a
separate System-local semantic eval in `evaluation.json`. That eval checks only
this demo route's required completion claim; it is neither a general judge nor
a portable rubric. Its evidence names the subject, checkpoint, observable
checks, required evidence, and failure action.
The structural checks resolve each eval reference inside its owning run and
verify its JSON outcome and output reference agree with that run's ledger
record, so the evidence chain cannot silently become dangling or contradictory.

The data model also has explicit recovery evidence. To exercise it:

```sh
python3 workspace/engine/tracer.py --simulate-failure
python3 workspace/engine/tracer.py --recover --promote-example
```

`--simulate-failure` selects a fixture that is structurally valid but carries
an irrelevant result. The evaluator records a failed outcome without editing
that output; the failed run is retained and never promoted. `--recover` adds a
new run that points back to the unresolved failed predecessor, records the
correction/replay, and passes the eval. A second recovery attempt fails until
another failure is recorded.

For real Systems, retain relevant failures as owner-local regression or eval
cases before changing an affected model, prompt, tool, contract, or harness.
This authoring procedure is intentionally only a local seed pattern today; it
is not promoted as a portable Global Skill.
No orchestration service, database, or external package is needed.

## Checks and prerequisites

Prerequisite: Python 3.9 or newer. No third-party package is required.

Run the structural and stale-path checks, then the dependency-light tests:

```sh
python3 workspace/engine/checks.py
python3 -m unittest discover -s workspace/engine/tests -p 'test_*.py'
```

The checks enforce the three visible roots, required shell and tracer paths,
the absence of legacy top-level technical directories, and clean public
language. They also verify that every generated example carries a curated
marker and standalone proof files.

For the public contract and a clean-clone validation recipe, see
[`docs/contract.md`](docs/contract.md) and
[`docs/validation.md`](docs/validation.md).
