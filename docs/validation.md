# Validation

The reference uses only Python 3.9+ standard-library features and POSIX shell
commands that are commonly available in a clean checkout.

From the repository root, run the checks and tests:

```sh
python3 workspace/engine/checks.py
python3 -m unittest discover -s workspace/engine/tests -p 'test_*.py'
```

The tracer proof can then be produced with:

```sh
python3 workspace/engine/tracer.py --promote-example
```

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
  python3 workspace/engine/tracer.py --promote-example
)
```

The tracer prints the inspected prior-run IDs, run directory, output and
proof references, ledger path, and curated example path. The first clean-clone
run is `run-0001` and uses the fixed demonstration timestamp, making the
chain easy to inspect and compare.
