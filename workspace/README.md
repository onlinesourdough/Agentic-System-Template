# Workspace

`workspace/` is the persistent operational truth for this seed.

- `runs/` holds durable evidence for each route attempt.
- `history/runs.jsonl` keeps the append-only relation between runs.
- `learning/` holds durable notes intentionally retained for future work.
- `engine/` contains only the optional technical implementation of this
  filesystem reference.

Each traced run can include `output.json`, a separate `evaluation.json`, and
proof or failure/recovery evidence. The local evaluator belongs to this
System's route; it is not a general service or a requirement for other
Systems.

`workspace/` can also be read by the explicit `demo-route` audit scope. That
audit checks accumulated evidence without adding or changing operational truth.

This is a filesystem arrangement for the System Template, not an additional
AIOS concept or a service that another System must install.
