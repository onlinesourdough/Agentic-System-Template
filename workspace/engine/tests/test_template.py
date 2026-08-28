from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from shutil import copytree, rmtree
from typing import Optional


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
audit = _load_module("system_template_audit", ENGINE / "audit_system.py")


REPEATABILITY_CHILD = "SYSTEM_TEMPLATE_REPEATABILITY_CHILD"


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

    def test_public_boundary_requires_several_needed_responsibilities(self) -> None:
        for relative in ("README.md", "docs/contract.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            normalized = " ".join(text.split())
            self.assertIn("several responsibilities", normalized)
            self.assertIn("not an all-fields", normalized)
            self.assertIn("long Skill", normalized)

    def _temporary_seed(self, source_root: Path = ROOT):
        temporary = tempfile.TemporaryDirectory()
        temp_root = Path(temporary.name) / "seed"
        copytree(
            source_root,
            temp_root,
            ignore=lambda _path, names: {".git", "__pycache__"}.intersection(names),
        )
        self._reset_operational_state(temp_root)
        return temporary, temp_root

    def _auditable_seed(self):
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)
        tracer.trace_once(root, promote_example=True)
        tracer.trace_once(root, simulate_failure=True)
        tracer.trace_once(root, recover=True, promote_example=True)
        upstream = tempfile.TemporaryDirectory()
        self.addCleanup(upstream.cleanup)
        upstream_path = Path(upstream.name) / "upstream.git"
        self._run_git(None, "init", "--bare", "--initial-branch=main", str(upstream_path))
        self._run_git(root, "init", "--initial-branch=main")
        self._run_git(root, "config", "user.name", "System Template Tests")
        self._run_git(root, "config", "user.email", "system-template@example.invalid")
        self._run_git(root, "add", "--all")
        self._run_git(root, "commit", "-m", "fixture baseline")
        self._run_git(root, "remote", "add", "origin", upstream_path.as_uri())
        self._run_git(root, "push", "--set-upstream", "origin", "main")
        return root

    @staticmethod
    def _run_git(root: Optional[Path], *arguments: str) -> str:
        command = ["git"]
        if root is not None:
            command.extend(("-C", str(root)))
        command.extend(arguments)
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
                "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        result = subprocess.run(
            command,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        return result.stdout.strip()

    def _advance_upstream(self, root: Path) -> str:
        checkout = tempfile.TemporaryDirectory()
        self.addCleanup(checkout.cleanup)
        checkout_path = Path(checkout.name) / "upstream-work"
        remote_url = self._run_git(root, "remote", "get-url", "origin")
        self._run_git(None, "clone", "--quiet", remote_url, str(checkout_path))
        self._run_git(checkout_path, "config", "user.name", "System Template Tests")
        self._run_git(
            checkout_path,
            "config",
            "user.email",
            "system-template@example.invalid",
        )
        self._run_git(checkout_path, "commit", "--allow-empty", "-m", "upstream")
        self._run_git(checkout_path, "push", "origin", "main")
        return self._run_git(checkout_path, "rev-parse", "HEAD")

    def _commit_local(self, root: Path) -> str:
        self._run_git(root, "commit", "--allow-empty", "-m", "local")
        return self._run_git(root, "rev-parse", "HEAD")

    @staticmethod
    def _tree_hash(root: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(root.rglob("*")):
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _complete_tree_hash(root: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(root.rglob("*")):
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            if path.is_symlink():
                digest.update(b"link")
                digest.update(os.readlink(path).encode("utf-8"))
            elif path.is_dir():
                digest.update(b"directory")
            elif path.is_file():
                digest.update(b"file")
                digest.update(path.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _reset_operational_state(root: Path) -> None:
        """Reset only the copied seed's mutable operational artifacts."""

        history = root / "workspace" / "history" / "runs.jsonl"
        history.write_text("", encoding="utf-8")
        for relative in (
            "workspace/runs",
            "workspace/learning",
            "examples",
        ):
            directory = root / relative
            if not directory.is_dir():
                continue
            for child in directory.iterdir():
                if child.name == ".gitkeep":
                    continue
                if child.is_dir() and not child.is_symlink():
                    rmtree(child)
                else:
                    child.unlink()

    @staticmethod
    def _run_full_suite(root: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment[REPEATABILITY_CHILD] = "1"
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(root / "workspace" / "engine" / "tests"),
                "-p",
                "test_*.py",
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_repeatability_survives_active_tracer_state(self) -> None:
        if os.environ.get(REPEATABILITY_CHILD) == "1":
            self.skipTest("parent test owns the repeatability subprocess proof")

        temporary, active_root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)
        source_history = (ROOT / "workspace" / "history" / "runs.jsonl").read_text(
            encoding="utf-8"
        )

        pristine = self._run_full_suite(active_root)
        self.assertEqual(
            pristine.returncode,
            0,
            pristine.stdout + "\n" + pristine.stderr,
        )

        success = tracer.trace_once(active_root, promote_example=True)
        failure = tracer.trace_once(active_root, simulate_failure=True)
        recovery = tracer.trace_once(active_root, recover=True, promote_example=True)
        self.assertEqual(success.run_id, "run-0001")
        self.assertEqual(success.status, "succeeded")
        self.assertEqual(failure.run_id, "run-0002")
        self.assertEqual(failure.status, "failed")
        self.assertEqual(recovery.run_id, "run-0003")
        self.assertEqual(recovery.status, "succeeded")
        self.assertEqual(recovery.previous_run_id, "run-0002")
        with self.assertRaisesRegex(
            tracer.TraceError, "previous unresolved failed demo run"
        ):
            tracer.trace_once(active_root, recover=True)

        repeat = self._run_full_suite(active_root)
        self.assertEqual(repeat.returncode, 0, repeat.stdout + "\n" + repeat.stderr)
        self.assertEqual(
            (ROOT / "workspace" / "history" / "runs.jsonl").read_text(
                encoding="utf-8"
            ),
            source_history,
        )

    def test_temporary_seed_preserves_placeholders_without_active_state(self) -> None:
        active_temporary, active_root = self._temporary_seed()
        self.addCleanup(active_temporary.cleanup)
        tracer.trace_once(active_root, promote_example=True)
        tracer.trace_once(active_root, simulate_failure=True)
        tracer.trace_once(active_root, recover=True, promote_example=True)

        temporary, root = self._temporary_seed(source_root=active_root)
        self.addCleanup(temporary.cleanup)

        self.assertEqual(
            (root / "workspace" / "history" / "runs.jsonl").read_text(
                encoding="utf-8"
            ),
            "",
        )
        for relative in ("workspace/runs", "workspace/learning", "examples"):
            directory = root / relative
            self.assertTrue((directory / ".gitkeep").is_file())
            self.assertEqual(
                [child.name for child in directory.iterdir() if child.name != ".gitkeep"],
                [],
            )

    def test_success_route_appends_then_promotes(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)

        result = tracer.trace_once(root, promote_example=True)

        self.assertEqual(result.run_id, "run-0001")
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.previous_run_id, None)
        self.assertEqual(result.previous_run_relation, None)
        self.assertTrue(result.output_path.is_file())
        self.assertTrue(result.evaluation_path.is_file())
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
        self.assertEqual(record["evaluation"]["outcome"], "passed")
        proof = json.loads(result.proof_path.read_text())
        self.assertEqual(proof["curated_example_ref"], "examples/demo-route/run-0001/")
        self.assertEqual(proof["evaluation_outcome"], "passed")
        example_proof = json.loads((result.example_path / "proof.json").read_text())
        self.assertTrue(example_proof["curated"])

    def test_audit_passes_for_healthy_reference_without_mutation(self) -> None:
        root = self._auditable_seed()
        fixture = json.loads(
            (root / "workspace/engine/fixtures/audit-system.json").read_text(
                encoding="utf-8"
            )
        )
        before = self._complete_tree_hash(root)

        result = audit.audit_system(root, "both")

        self.assertEqual(self._complete_tree_hash(root), before)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.scope, "both")
        self.assertEqual(result.evidence_gaps, [])
        self.assertEqual(result.next_action, "No action; keep the audit read-only.")
        self.assertIn(
            {"name": "healthy-live-equal", "scope": "both", "expected_status": "PASS"},
            fixture["cases"],
        )
        self.assertTrue(any("failure and recovery" in item for item in result.evidence))

    def test_audit_fails_for_stale_command_without_mutation(self) -> None:
        root = self._auditable_seed()
        readme = root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8")
            + "\npython3 workspace/engine/missing_audit_command.py\n",
            encoding="utf-8",
        )
        before = self._complete_tree_hash(root)

        result = audit.audit_system(root, "repository")

        self.assertEqual(self._complete_tree_hash(root), before)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.evidence_gaps, [])
        self.assertEqual(
            result.next_action,
            "Route the finding to the owning Build/Review lifecycle.",
        )
        self.assertTrue(any("missing_audit_command.py" in item for item in result.evidence))

    def test_audit_fails_for_contradictory_curated_proof_without_mutation(self) -> None:
        root = self._auditable_seed()
        proof_path = root / "examples/demo-route/run-0001/proof.json"
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
        proof["source_run_id"] = "run-0002"
        proof_path.write_text(json.dumps(proof), encoding="utf-8")
        before = self._tree_hash(root)

        result = audit.audit_system(root, "demo-route")

        self.assertEqual(self._tree_hash(root), before)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.evidence_gaps, [])
        self.assertTrue(any("does not cite a passing run" in item for item in result.evidence))

    def test_audit_blocks_for_missing_workspace_evidence_without_mutation(self) -> None:
        root = self._auditable_seed()
        history = root / "workspace/history/runs.jsonl"
        history.unlink()
        before = self._tree_hash(root)

        result = audit.audit_system(root, "demo-route")

        self.assertEqual(self._tree_hash(root), before)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.evidence, [])
        self.assertEqual(
            result.next_action,
            "Restore or provide the listed scoped evidence before rerunning.",
        )
        self.assertTrue(any("runs.jsonl" in item for item in result.evidence_gaps))

    def test_repository_audit_does_not_read_workspace_scope(self) -> None:
        root = self._auditable_seed()
        (root / "workspace/history/runs.jsonl").unlink()
        self._run_git(root, "add", "--all")
        self._run_git(root, "commit", "-m", "remove run-family evidence")
        self._run_git(root, "push", "origin", "main")
        before = self._complete_tree_hash(root)

        result = audit.audit_system(root, "repository")

        self.assertEqual(self._complete_tree_hash(root), before)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.scope, "repository")

    def test_repository_audit_proves_equal_ahead_and_diverged(self) -> None:
        for expected_relation in ("equal", "ahead", "diverged"):
            with self.subTest(relation=expected_relation):
                root = self._auditable_seed()
                if expected_relation == "ahead":
                    self._commit_local(root)
                elif expected_relation == "diverged":
                    self._advance_upstream(root)
                    self._commit_local(root)
                before = self._complete_tree_hash(root)

                result = audit.audit_system(root, "repository")

                self.assertEqual(self._complete_tree_hash(root), before)
                self.assertEqual(
                    result.status,
                    "PASS" if expected_relation == "equal" else "FAIL",
                )
                self.assertEqual(result.evidence_gaps, [])
                self.assertTrue(
                    any(
                        f"relation={expected_relation}" in item
                        and "local=" in item
                        and "live=" in item
                        for item in result.evidence
                    ),
                    result.evidence,
                )

    def test_cached_tracking_ref_is_not_live_proof(self) -> None:
        root = self._auditable_seed()
        local_oid = self._run_git(root, "rev-parse", "HEAD")
        cached_oid = self._run_git(root, "rev-parse", "@{upstream}")
        live_oid = self._advance_upstream(root)
        self.assertEqual(cached_oid, local_oid)
        self.assertNotEqual(live_oid, cached_oid)
        before = self._complete_tree_hash(root)

        result = audit.audit_system(root, "repository")

        self.assertEqual(self._complete_tree_hash(root), before)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.evidence_gaps, [])
        self.assertTrue(
            any(
                f"local={local_oid}" in item
                and f"cached_tracking={cached_oid}" in item
                and f"live={live_oid}" in item
                and "relation=behind" in item
                for item in result.evidence
            ),
            result.evidence,
        )

    def test_repository_audit_fails_for_dirty_state_without_mutation(self) -> None:
        root = self._auditable_seed()
        readme = root / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nstaged\n")
        self._run_git(root, "add", "README.md")
        readme.write_text(readme.read_text(encoding="utf-8") + "unstaged\n")
        (root / "untracked.txt").write_text("untracked\n", encoding="utf-8")
        porcelain = self._run_git(
            root, "status", "--porcelain=v2", "--untracked-files=all"
        )
        self.assertIn("1 MM", porcelain)
        self.assertIn("? untracked.txt", porcelain)
        before = self._complete_tree_hash(root)

        result = audit.audit_system(root, "repository")

        self.assertEqual(self._complete_tree_hash(root), before)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(
            any("worktree/index is not clean" in item for item in result.evidence)
        )

    def test_repository_audit_blocks_for_unprovable_git_state(self) -> None:
        cases = (
            ("unavailable", "fresh live upstream object"),
            ("missing-live", "fresh live upstream object"),
            ("ambiguous", "remote identity is missing or ambiguous"),
            ("missing-upstream", "branch.main.remote"),
            ("detached", "current branch (detached or missing)"),
            ("unexpected", "current branch is unexpected"),
        )
        for problem, expected_gap in cases:
            with self.subTest(problem=problem):
                root = self._auditable_seed()
                if problem == "unavailable":
                    unavailable = tempfile.TemporaryDirectory()
                    self.addCleanup(unavailable.cleanup)
                    missing = Path(unavailable.name) / "missing.git"
                    self._run_git(root, "remote", "set-url", "origin", missing.as_uri())
                elif problem == "missing-live":
                    remote_url = self._run_git(root, "remote", "get-url", "origin")
                    remote_path = Path(remote_url.removeprefix("file://"))
                    self._run_git(
                        None,
                        "--git-dir",
                        str(remote_path),
                        "update-ref",
                        "-d",
                        "refs/heads/main",
                    )
                elif problem == "ambiguous":
                    self._run_git(
                        root,
                        "config",
                        "--add",
                        "remote.origin.url",
                        "file:///second-upstream.git",
                    )
                elif problem == "missing-upstream":
                    self._run_git(root, "branch", "--unset-upstream")
                elif problem == "detached":
                    self._run_git(root, "checkout", "--detach")
                else:
                    self._run_git(root, "branch", "-m", "unexpected")
                before = self._complete_tree_hash(root)

                result = audit.audit_system(root, "repository")

                self.assertEqual(self._complete_tree_hash(root), before)
                self.assertEqual(result.status, "BLOCKED")
                self.assertTrue(
                    any(expected_gap in gap for gap in result.evidence_gaps),
                    result.evidence_gaps,
                )

    def test_repository_audit_does_not_disclose_remote_credentials(self) -> None:
        root = self._auditable_seed()
        self._run_git(
            root,
            "remote",
            "set-url",
            "origin",
            "https://secret-token@example.invalid/System-template.git",
        )
        before = self._complete_tree_hash(root)

        result = audit.audit_system(root, "repository")

        self.assertEqual(self._complete_tree_hash(root), before)
        self.assertEqual(result.status, "BLOCKED")
        self.assertNotIn("secret-token", json.dumps(result.as_dict()))

    def test_audit_blocks_for_missing_failure_or_recovery_evidence(self) -> None:
        cases = (
            ("failure", "workspace/runs/run-0002/failure.json", "run-0002"),
            ("recovery", "workspace/runs/run-0003/recovery.json", "run-0003"),
        )
        for kind, relative, run_id in cases:
            with self.subTest(kind=kind):
                root = self._auditable_seed()
                (root / relative).unlink()
                before = self._tree_hash(root)

                result = audit.audit_system(root, "demo-route")

                self.assertEqual(self._tree_hash(root), before)
                self.assertEqual(result.status, "BLOCKED")
                self.assertEqual(result.evidence, [])
                self.assertEqual(
                    result.evidence_gaps,
                    [f"required {kind} evidence is unavailable for {run_id}"],
                )

    def test_audit_fails_for_invalid_failure_or_recovery_evidence(self) -> None:
        cases = (
            ("failure", "escaping", "run-0002 has an escaping or invalid failure reference"),
            ("failure", "malformed", "failure evidence for run-0002 is not readable JSON"),
            ("failure", "contradictory", "failure evidence for run-0002 does not identify the eval failure"),
            ("failure", "wrong-run", "failure evidence for run-0002 identifies a different run"),
            ("failure", "wrong-eval", "failure evidence for run-0002 contradicts its evaluation reference"),
            ("recovery", "escaping", "run-0003 has an escaping or invalid recovery reference"),
            ("recovery", "malformed", "recovery evidence for run-0003 is not readable JSON"),
            ("recovery", "contradictory", "recovery evidence for run-0003 contradicts its failed predecessor"),
            ("recovery", "wrong-run", "recovery evidence for run-0003 identifies a different run"),
            ("recovery", "wrong-status", "recovery evidence for run-0003 has an invalid status"),
        )
        for kind, problem, expected_error in cases:
            with self.subTest(kind=kind, problem=problem):
                root = self._auditable_seed()
                history = root / "workspace/history/runs.jsonl"
                records = [
                    json.loads(line)
                    for line in history.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                record = next(
                    item
                    for item in records
                    if item["run_id"] == ("run-0002" if kind == "failure" else "run-0003")
                )
                evidence_path = root / (
                    "workspace/runs/run-0002/failure.json"
                    if kind == "failure"
                    else "workspace/runs/run-0003/recovery.json"
                )

                if problem == "escaping":
                    record[kind]["ref"] = "workspace/history/runs.jsonl"
                    history.write_text(
                        "\n".join(json.dumps(item) for item in records) + "\n",
                        encoding="utf-8",
                    )
                elif problem == "malformed":
                    evidence_path.write_text("{", encoding="utf-8")
                else:
                    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                    if problem == "wrong-run":
                        evidence["run_id"] = "run-0001"
                    elif problem == "wrong-eval":
                        evidence["evaluation_ref"] = "workspace/runs/run-0002/other.json"
                    elif problem == "wrong-status":
                        evidence["status"] = "other"
                    elif kind == "failure":
                        evidence["code"] = "OTHER_FAILURE"
                    else:
                        evidence["from_run_id"] = "run-0001"
                    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
                before = self._tree_hash(root)

                result = audit.audit_system(root, "demo-route")

                self.assertEqual(self._tree_hash(root), before)
                self.assertEqual(result.status, "FAIL")
                self.assertEqual(result.evidence_gaps, [])
                self.assertTrue(any(expected_error in item for item in result.evidence))

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

    def test_semantic_failure_is_structurally_valid_retained_and_replayed(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)
        fixture_path = root / tracer.SEMANTIC_FAILURE_FIXTURE_REF
        fixture_before = fixture_path.read_text(encoding="utf-8")
        fixture = json.loads(fixture_before)

        self.assertEqual(tracer.validate_output_structure(fixture), [])
        failed = tracer.trace_once(root, simulate_failure=True)
        failed_output = json.loads(failed.output_path.read_text(encoding="utf-8"))
        failed_evaluation = json.loads(
            failed.evaluation_path.read_text(encoding="utf-8")
        )

        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed_output["status"], "succeeded")
        self.assertEqual(failed_evaluation["outcome"], "failed")
        self.assertTrue(failed_evaluation["observable_checks"][0]["passed"])
        self.assertFalse(failed_evaluation["observable_checks"][-1]["passed"])
        self.assertEqual(fixture_path.read_text(encoding="utf-8"), fixture_before)
        self.assertFalse((root / "examples" / "demo-route" / failed.run_id).exists())

        replay = tracer.trace_once(root, recover=True, promote_example=True)
        replay_evaluation = json.loads(
            replay.evaluation_path.read_text(encoding="utf-8")
        )
        recovery = json.loads(replay.recovery_path.read_text(encoding="utf-8"))
        records = [
            json.loads(line)
            for line in (root / "workspace/history/runs.jsonl").read_text().splitlines()
            if line.strip()
        ]

        self.assertEqual(replay.status, "succeeded")
        self.assertEqual(replay.previous_run_id, failed.run_id)
        self.assertEqual(replay.previous_run_relation, "recovery")
        self.assertEqual(replay_evaluation["outcome"], "passed")
        self.assertEqual(recovery["from_run_id"], failed.run_id)
        self.assertIn("corrected", recovery["action"])
        self.assertEqual(records[0]["evaluation"]["outcome"], "failed")
        self.assertEqual(records[1]["evaluation"]["outcome"], "passed")
        self.assertEqual(records[1]["recovery"]["from_run_id"], failed.run_id)
        self.assertEqual(checks.check_structure(root), [])

    def test_semantic_failure_cannot_be_promoted(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)

        with self.assertRaisesRegex(tracer.TraceError, "cannot be promoted"):
            tracer.trace_once(root, simulate_failure=True, promote_example=True)

        self.assertFalse((root / "workspace/runs/run-0001").exists())
        self.assertEqual(
            (root / "workspace/history/runs.jsonl").read_text(encoding="utf-8"),
            "",
        )

    def test_evaluation_evidence_must_be_present_local_and_consistent(self) -> None:
        cases = (
            ("missing", "evaluation evidence is missing"),
            ("malformed", "evaluation evidence is not valid JSON"),
            ("non_object", "evaluation evidence must be an object"),
            ("escaping", "evaluation reference escapes its owning run"),
            ("outcome", "evaluation evidence outcome disagrees"),
            ("output", "evaluation output reference disagrees"),
        )
        for case, expected_error in cases:
            with self.subTest(case=case):
                temporary, root = self._temporary_seed()
                self.addCleanup(temporary.cleanup)
                result = tracer.trace_once(root)
                history = root / "workspace/history/runs.jsonl"
                record = json.loads(history.read_text(encoding="utf-8"))

                if case == "missing":
                    result.evaluation_path.unlink()
                elif case == "malformed":
                    result.evaluation_path.write_text("{", encoding="utf-8")
                elif case == "non_object":
                    result.evaluation_path.write_text("[]", encoding="utf-8")
                elif case == "escaping":
                    record["evaluation"]["ref"] = "workspace/history/runs.jsonl"
                elif case == "outcome":
                    evaluation = json.loads(
                        result.evaluation_path.read_text(encoding="utf-8")
                    )
                    evaluation["outcome"] = "failed"
                    result.evaluation_path.write_text(
                        json.dumps(evaluation), encoding="utf-8"
                    )
                else:
                    evaluation = json.loads(
                        result.evaluation_path.read_text(encoding="utf-8")
                    )
                    evaluation["output_ref"] = "workspace/runs/run-0001/other.json"
                    result.evaluation_path.write_text(
                        json.dumps(evaluation), encoding="utf-8"
                    )

                history.write_text(json.dumps(record) + "\n", encoding="utf-8")
                errors = checks.check_structure(root)
                self.assertTrue(
                    any(expected_error in error for error in errors), errors
                )

    def test_evaluation_outcomes_must_match_run_status(self) -> None:
        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)
        tracer.trace_once(root)
        history = root / "workspace/history/runs.jsonl"
        record = json.loads(history.read_text(encoding="utf-8"))
        record["status"] = "failed"
        record["failure"] = {"code": "TEST", "ref": "test"}
        history.write_text(json.dumps(record) + "\n", encoding="utf-8")

        errors = checks.check_structure(root)

        self.assertTrue(
            any("passed evaluation for a non-succeeded run" in error for error in errors),
            errors,
        )

        temporary, root = self._temporary_seed()
        self.addCleanup(temporary.cleanup)
        tracer.trace_once(root, simulate_failure=True)
        history = root / "workspace/history/runs.jsonl"
        record = json.loads(history.read_text(encoding="utf-8"))
        record["status"] = "succeeded"
        record["failure"] = None
        history.write_text(json.dumps(record) + "\n", encoding="utf-8")

        errors = checks.check_structure(root)

        self.assertTrue(
            any("failed evaluation for a non-failed run" in error for error in errors),
            errors,
        )

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
