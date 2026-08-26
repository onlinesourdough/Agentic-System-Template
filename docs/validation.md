# Validation

The reference uses only Python 3.9+ standard-library features and POSIX shell
commands that are commonly available in a clean checkout.

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

The audit tests create isolated fixtures for a healthy PASS, a stale documented
command FAIL, and missing workspace evidence BLOCKED. They snapshot the seed
before and after each audit to prove the audit has no mutation path; the live
audit command above does not append another run.
The same isolated tests cover missing, escaping, malformed, and contradictory
failure/recovery artifacts, so discoverability is not merely ledger-deep.

For an independent checkout, clone the committed repository into a new
temporary directory and repeat both validations plus the tracer. A local
clone is sufficient and does not contact the configured remote:

```sh
clone_parent="$(mktemp -d)"
git clone --no-local "$(pwd)" "$clone_parent/System-template"
(
  cd "$clone_parent/System-template" &&
  python3 workspace/engine/checks.py &&
  python3 -m unittest discover -s workspace/engine/tests -p 'test_*.py' &&
  python3 workspace/engine/tracer.py --promote-example &&
  python3 workspace/engine/tracer.py --simulate-failure &&
  python3 workspace/engine/tracer.py --recover --promote-example &&
  python3 workspace/engine/audit_system.py --scope both
)
```

The tracer prints the inspected prior-run IDs, run directory, output and
evaluation and proof references, ledger path, and curated example path. The
first clean-clone run is `run-0001` and uses the fixed demonstration timestamp,
making the baseline, retained failure, and recovery/replay chain easy to
inspect and compare.
