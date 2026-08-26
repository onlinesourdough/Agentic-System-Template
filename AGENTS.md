# System Template

This repository is the neutral, standalone seed for persistent Agentic Systems.
Keep it small enough to understand by reading this file, `README.md`, and the
primary skill at `.agents/skills/system-template/SKILL.md`.

## Canonical model

AIOS has three first-class concepts: Space, System, and Project. Template,
resource, archive, and skill are supporting constructs; do not turn them into
additional AIOS types.

`workspace/` is persistent operational truth. A System run belongs in
`workspace/runs/`, its append-only relation belongs in
`workspace/history/runs.jsonl`, and durable learning notes belong in
`workspace/learning/`. `workspace/engine/` is only the optional technical
implementation of this reference. It is not another System concept.

The only visible functional roots are `workspace/`, `examples/`, and `docs/`.
Keep the shell, adapters, scripts, and tests beneath `workspace/engine/`.
Examples are added only as deliberately curated, standalone proof.

## Primary skill behavior

The one primary System skill first inspects relevant prior runs, then executes
or routes the work. The route keeps deterministic validation separate from its
small System-local semantic eval. It records structured input/output/eval/proof
references and failure or recovery evidence. It appends one ledger record and
promotes an example only when that promotion is intentional and successful.

`audit-system` is a separate, read-only accumulated-state route. It selects an
explicit repository, named run-family, or combined scope; it never creates a
run, ledger entry, example, repair, or external action.

Inputs are references rather than prompt transcripts. The ledger is plain
JSON Lines and contains no credentials, database, cross-System log, shared
package, or dependency on an AIOS runtime. This repository is a seed and
filesystem reference, not an installed component of another system.

## Validation

From the repository root, run:

```sh
python3 workspace/engine/checks.py
python3 -m unittest discover -s workspace/engine/tests -p 'test_*.py'
python3 workspace/engine/tracer.py --promote-example
```

Use Python 3.9 or newer. The tracer uses only the Python standard library and
has a fixed demonstration clock, so a clean clone produces the same proof
chain. Do not push, create remote artifacts, or add private project context to
this public seed.
