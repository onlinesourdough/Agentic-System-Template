---
name: system-template
description: The primary System skill for routing a deterministic reference run and preserving its evidence.
---

# System Template primary System skill

This is the one primary System skill in the seed. It describes a small,
repeatable route that preserves operational truth in `workspace/` and moves a
proof into `examples/` only by deliberate choice.

## Route

1. Inspect relevant prior records in `workspace/history/runs.jsonl`. Use the
   route and input reference to identify the previous run; do not copy raw
   request text into a record.
2. Execute or route the work. The reference route is the deterministic `demo`
   handler in `workspace/engine/tracer.py`.
3. Create `workspace/runs/<run-id>/` and write structured input, output, and
   proof files. A failure writes failure evidence in that same run directory.
4. Append one JSON object to `workspace/history/runs.jsonl`. Each record keeps
   the run ID, timestamps, status, input/output/proof references, previous-run
   relation, and failure/recovery references.
5. If a recovery is needed, create a new run that points to the failed run and
   writes a recovery evidence file. Do not rewrite the failed record.
6. Promote an example only when the caller explicitly requests it. A promoted
   example must include its own `README.md` and `proof.json`, and must remain
   understandable without importing this repository.

## Reference command

From the repository root:

```sh
python3 workspace/engine/tracer.py --promote-example
```

Failure and recovery can be demonstrated with:

```sh
python3 workspace/engine/tracer.py --simulate-failure
python3 workspace/engine/tracer.py --recover --promote-example
```

The tracer is a reference implementation of this skill, not a service that
the seed must be installed into. Keep new System-specific behavior in the
System's own workspace and keep this public shell generic.
