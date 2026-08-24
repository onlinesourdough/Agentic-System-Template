# Workspace

`workspace/` is the persistent operational truth for this seed.

- `runs/` holds durable evidence for each route attempt.
- `history/runs.jsonl` keeps the append-only relation between runs.
- `learning/` holds durable notes intentionally retained for future work.
- `engine/` contains only the optional technical implementation of this
  filesystem reference.

This is a filesystem arrangement for the System Template, not an additional
AIOS concept or a service that another System must install.
