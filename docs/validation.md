# Validation

The reference uses only Python 3.9+ standard-library features and POSIX shell
commands that are commonly available in a clean checkout. Repository audit
scopes additionally require Git and non-interactive access to their configured
upstream.

From the repository root, run the checks and tests:

```sh
python3 workspace/engine/checks.py
python3 -m unittest discover -s workspace/engine/tests -p 'test_*.py'
python3 workspace/engine/audit_system.py --scope both
```

The passing tracer proof can then be produced with:

```sh
python3 workspace/engine/tracer.py --promote-example
```

The expected semantic-failure and correction/replay proof is a separate,
inspectable sequence. The first command successfully records a failed eval; it
does not rewrite the structurally valid but irrelevant output.

```sh
python3 workspace/engine/tracer.py --simulate-failure
python3 workspace/engine/tracer.py --recover --promote-example
```

Inspect each run's `output.json`, `evaluation.json`, `failure.json` or
`recovery.json`, and `proof.json`, plus the corresponding JSON Lines record.
The evaluator is System-local and separate from deterministic output-shape
validation; no AIOS service, model, database, or external package is needed.
The structural checks also reject missing, malformed, escaping, or
ledger-contradictory eval evidence.

The audit tests create isolated local Git upstreams for live-equal PASS and
behind, ahead, diverged, and dirty FAIL results. They also prove unavailable,
ambiguous, or unprovable upstream evidence is BLOCKED and that an unchanged
cached tracking ref cannot stand in for a fresh live read. Each repository
audit snapshots the complete fixture, including `.git`, before and after the
audit. The live fetch
occurs only in a temporary bare repository, so the audited refs, object store,
index, worktree, run history, and examples remain unchanged. The live audit
command above requires non-interactive access to the configured upstream.
The same isolated tests cover missing, escaping, malformed, and contradictory
failure/recovery artifacts, so discoverability is not merely ledger-deep.

For an independent checkout, clone the committed repository into a new
temporary directory and repeat both validations plus the tracer. The local
source becomes that clone's configured upstream, so the currentness proof is
fresh and deterministic without network access:

```sh
clone_parent="$(mktemp -d)"
git clone --no-local "$(pwd)" "$clone_parent/System-template"
(
  cd "$clone_parent/System-template" &&
  python3 workspace/engine/checks.py &&
  python3 -m unittest discover -s workspace/engine/tests -p 'test_*.py' &&
  python3 workspace/engine/audit_system.py --scope both &&
  python3 workspace/engine/tracer.py --promote-example &&
  python3 workspace/engine/tracer.py --simulate-failure &&
  python3 workspace/engine/tracer.py --recover --promote-example
)
```

The clean-clone audit runs before the tracer because creating retained runs and
examples intentionally makes that checkout differ from its upstream.

The tracer prints the inspected prior-run IDs, run directory, output and
evaluation and proof references, ledger path, and curated example path. The
first clean-clone run is `run-0001` and uses the fixed demonstration timestamp,
making the baseline, retained failure, and recovery/replay chain easy to
inspect and compare.
