from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from shutil import copytree


ROOT = Path(__file__).resolve().parents[3]
ENGINE = ROOT / "workspace" / "engine"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


checks = _load_module("system_template_checks", ENGINE / "checks.py")
tracer = _load_module("system_template_tracer", ENGINE / "tracer.py")


class SystemTemplateTests(unittest.TestCase):
    def test_repository_shell_is_canonical(self) -> None:
        self.assertEqual(checks.check_structure(ROOT), [])
        self.assertTrue((ROOT / "workspace" / "history" / "runs.jsonl").is_file())

    def test_workspace_readme_is_required(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)
        (root / "workspace" / "README.md").unlink()

        errors = checks.check_structure(root)

        self.assertIn("required path is missing: workspace/README.md", errors)

    def _temporary_seed(self):
        temporary = tempfile.TemporaryDirectory()
        temp_root = Path(temporary.name) / "seed"
        copytree(ROOT, temp_root, ignore=lambda _path, names: {".git", "__pycache__"}.intersection(names))
        return temporary, temp_root

    def test_success_route_appends_then_promotes(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)

        result = tracer.trace_once(root, promote_example=True)

        self.assertEqual(result.run_id, "run-0001")
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.previous_run_id, None)
        self.assertEqual(result.previous_run_relation, None)
        self.assertTrue(result.output_path.is_file())
        self.assertTrue(result.proof_path.is_file())
        self.assertTrue(result.example_path is not None and result.example_path.is_dir())
        self.assertEqual(checks.check_structure(root), [])
        ledger_lines = (root / "workspace/history/runs.jsonl").read_text().splitlines()
        self.assertEqual(len([line for line in ledger_lines if line.strip()]), 1)
        record = json.loads(ledger_lines[-1])
        self.assertEqual(record["run_id"], "run-0001")
        self.assertEqual(record["input_ref"], tracer.INPUT_REF)
        self.assertEqual(record["status"], "succeeded")
        self.assertIsNone(record["failure"])
        self.assertIsNone(record["recovery"])
        proof = json.loads(result.proof_path.read_text())
        self.assertEqual(proof["curated_example_ref"], "examples/demo-route/run-0001/")
        example_proof = json.loads((result.example_path / "proof.json").read_text())
        self.assertTrue(example_proof["curated"])

    def test_second_run_inspects_predecessor_and_ledger_stays_append_only(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)

        first = tracer.trace_once(root)
        second = tracer.trace_once(root)

        self.assertEqual(first.run_id, "run-0001")
        self.assertEqual(second.run_id, "run-0002")
        self.assertEqual(second.previous_run_id, "run-0001")
        self.assertEqual(second.previous_run_relation, "predecessor")
        ledger_lines = [
            line
            for line in (root / "workspace/history/runs.jsonl").read_text().splitlines()
            if line.strip()
        ]
        self.assertEqual(len(ledger_lines), 2)
        self.assertEqual(json.loads(ledger_lines[1])["previous_run_id"], "run-0001")
        self.assertEqual(
            json.loads(ledger_lines[1])["previous_run_relation"], "predecessor"
        )

    def test_failure_and_recovery_evidence_are_linked(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)

        failed = tracer.trace_once(root, simulate_failure=True)
        continuation = tracer.trace_once(root)
        recovered = tracer.trace_once(root, recover=True, promote_example=True)

        self.assertEqual(failed.status, "failed")
        self.assertTrue(failed.failure_path is not None and failed.failure_path.is_file())
        self.assertEqual(continuation.run_id, "run-0002")
        self.assertEqual(continuation.previous_run_id, "run-0001")
        self.assertEqual(continuation.previous_run_relation, "predecessor")
        self.assertEqual(recovered.status, "succeeded")
        self.assertEqual(recovered.previous_run_id, "run-0001")
        self.assertEqual(recovered.previous_run_relation, "recovery")
        self.assertTrue(recovered.recovery_path is not None and recovered.recovery_path.is_file())
        with self.assertRaises(tracer.TraceError):
            tracer.trace_once(root, recover=True)
        records = [
            json.loads(line)
            for line in (root / "workspace/history/runs.jsonl").read_text().splitlines()
            if line.strip()
        ]
        self.assertEqual(records[0]["failure"]["ref"], "workspace/runs/run-0001/failure.json")
        self.assertIsNone(records[0]["recovery"])
        self.assertIsNone(records[1]["recovery"])
        self.assertEqual(records[2]["recovery"]["from_run_id"], "run-0001")
        self.assertEqual(records[2]["recovery"]["ref"], "workspace/runs/run-0003/recovery.json")
        self.assertEqual(records[0]["previous_run_relation"], None)
        self.assertEqual(records[1]["previous_run_relation"], "predecessor")
        self.assertEqual(records[2]["previous_run_relation"], "recovery")
        self.assertEqual(checks.check_structure(root), [])

    def test_recovery_is_single_use_per_failed_run(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)

        failed = tracer.trace_once(root, simulate_failure=True)
        recovered = tracer.trace_once(root, recover=True)

        self.assertEqual(failed.run_id, "run-0001")
        self.assertEqual(recovered.run_id, "run-0002")
        self.assertEqual(recovered.previous_run_id, "run-0001")
        with self.assertRaisesRegex(
            tracer.TraceError, "previous unresolved failed demo run"
        ):
            tracer.trace_once(root, recover=True)
        self.assertFalse((root / "workspace/runs/run-0003").exists())

        second_failure = tracer.trace_once(root, simulate_failure=True)
        second_recovery = tracer.trace_once(root, recover=True)
        self.assertEqual(second_failure.run_id, "run-0003")
        self.assertEqual(second_recovery.run_id, "run-0004")
        self.assertEqual(second_recovery.previous_run_id, "run-0003")
        self.assertEqual(second_recovery.previous_run_relation, "recovery")

    def test_stale_public_wording_is_rejected(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)
        bad_wording = "This is a " + "hand" + "off " + "sche" + "ma.\n"
        (root / "docs" / "bad.md").write_text(bad_wording)

        errors = checks.check_structure(root)

        self.assertTrue(any("stale public wording" in error for error in errors))

    def test_local_schema_wording_is_allowed(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)
        local_schema = "This System owns a versioned JSON schema for its local contract.\n"
        (root / "docs" / "local.md").write_text(local_schema)

        self.assertEqual(checks._contains_stale_language(local_schema), [])
        self.assertEqual(checks.check_structure(root), [])

    def test_ledger_checker_rejects_repeated_recovery_reference(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)

        tracer.trace_once(root, simulate_failure=True)
        tracer.trace_once(root, recover=True)
        records = [
            json.loads(line)
            for line in (root / "workspace/history/runs.jsonl").read_text().splitlines()
            if line.strip()
        ]
        duplicate = dict(records[1])
        duplicate["run_id"] = "run-0003"
        duplicate["output_ref"] = "workspace/runs/run-0003/output.json"
        duplicate["proof_ref"] = "workspace/runs/run-0003/proof.json"
        history = root / "workspace/history/runs.jsonl"
        history.write_text(
            "\n".join(json.dumps(record, sort_keys=True) for record in records + [duplicate])
            + "\n"
        )

        errors = checks.check_structure(root)

        self.assertTrue(any("more than once" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
