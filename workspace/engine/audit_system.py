#!/usr/bin/env python3
"""Read-only accumulated-state audit for the System Template reference."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


AUDIT_SCOPES = ("repository", "demo-route", "both")
DEMO_INPUT_REF = "fixture://system-template/demo-route"
COMMAND_PATH = re.compile(r"python3\s+(workspace/engine/[A-Za-z0-9_.-]+\.py)")
REPOSITORY_EVIDENCE = (
    "AGENTS.md",
    "README.md",
    ".agents/skills/system-template/SKILL.md",
    ".agents/skills/audit-system/SKILL.md",
    "docs/contract.md",
    "docs/validation.md",
    "workspace/engine/checks.py",
    "workspace/engine/audit_system.py",
)


@dataclass(frozen=True)
class AuditResult:
    """The complete, compact response produced by a read-only audit."""

    status: str
    scope: str
    evidence: List[str]
    evidence_gaps: List[str]
    next_action: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "evidence": self.evidence,
            "evidence_gaps": self.evidence_gaps,
            "next_action": self.next_action,
            "scope": self.scope,
            "status": self.status,
        }


def repository_root() -> Path:
    """Return the repository root derived from this file, not the cwd."""

    return Path(__file__).resolve().parents[2]


def _load_checks(root: Path):
    checks_path = root / "workspace" / "engine" / "checks.py"
    spec = importlib.util.spec_from_file_location("system_template_audit_checks", checks_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the System Template structural checks")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path, label: str, findings: List[str]) -> Optional[Dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        findings.append(f"{label} is not readable JSON: {exc}")
        return None
    if not isinstance(value, dict):
        findings.append(f"{label} must be a JSON object")
        return None
    return value


def _scoped_path(root: Path, reference: object) -> Optional[Path]:
    if not isinstance(reference, str) or not reference:
        return None
    candidate = (root / reference).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _owned_run_path(root: Path, run_id: object, reference: object) -> Optional[Path]:
    """Resolve one evidence reference only when it remains in its owning run."""

    if not isinstance(run_id, str) or not run_id:
        return None
    runs_root = (root / "workspace" / "runs").resolve()
    owning_run = (runs_root / run_id).resolve()
    try:
        owning_run.relative_to(runs_root)
    except ValueError:
        return None
    candidate = _scoped_path(root, reference)
    if candidate is None:
        return None
    try:
        candidate.relative_to(owning_run)
    except ValueError:
        return None
    return candidate


def _result(status: str, scope: str, evidence: Iterable[str], gaps: Iterable[str]) -> AuditResult:
    if status == "PASS":
        next_action = "No action; keep the audit read-only."
    elif status == "FAIL":
        next_action = "Route the finding to the owning Build/Review lifecycle."
    else:
        next_action = "Restore or provide the listed scoped evidence before rerunning."
    return AuditResult(status, scope, list(evidence), list(gaps), next_action)


def _repository_audit(root: Path, findings: List[str], gaps: List[str]) -> List[str]:
    evidence: List[str] = []
    for relative in REPOSITORY_EVIDENCE:
        if not (root / relative).is_file():
            gaps.append(f"required repository evidence is unavailable: {relative}")
    if gaps:
        return evidence

    for relative in ("README.md", "docs/validation.md", ".agents/skills/system-template/SKILL.md", ".agents/skills/audit-system/SKILL.md"):
        text = (root / relative).read_text(encoding="utf-8")
        for command in COMMAND_PATH.findall(text):
            if not (root / command).is_file():
                findings.append(f"documented command target is unavailable: {command}")
    evidence.append("repository shell and documented local command targets were read")
    return evidence


def _workspace_audit(root: Path, findings: List[str], gaps: List[str]) -> List[str]:
    evidence: List[str] = []
    history = root / "workspace" / "history" / "runs.jsonl"
    runs_root = root / "workspace" / "runs"
    if not history.is_file():
        gaps.append("required workspace evidence is unavailable: workspace/history/runs.jsonl")
        return evidence
    if not runs_root.is_dir():
        gaps.append("required workspace evidence is unavailable: workspace/runs/")
        return evidence

    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(history.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            findings.append(f"ledger line {line_number} is not valid JSON: {exc.msg}")
            continue
        if not isinstance(record, dict):
            findings.append(f"ledger line {line_number} is not an object")
            continue
        if record.get("input_ref") == DEMO_INPUT_REF:
            records.append(record)
    if not records:
        gaps.append("required demo-route run evidence is unavailable")
        return evidence

    by_run_id = {record.get("run_id"): record for record in records}
    for record in records:
        run_id = record.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            findings.append("demo-route ledger record lacks a run_id")
            continue
        for field in ("output_ref", "proof_ref"):
            reference = _scoped_path(root, record.get(field))
            if reference is None:
                findings.append(f"{run_id} has an escaping or invalid {field}")
            elif not reference.is_file():
                gaps.append(f"required {field} is unavailable for {run_id}")
        evaluation = record.get("evaluation")
        evaluation_ref = evaluation.get("ref") if isinstance(evaluation, dict) else None
        reference = _scoped_path(root, evaluation_ref)
        if reference is None:
            findings.append(f"{run_id} has an escaping or invalid evaluation reference")
        elif not reference.is_file():
            gaps.append(f"required evaluation evidence is unavailable for {run_id}")

    failed = [record for record in records if record.get("status") == "failed"]
    recovered = [record for record in records if isinstance(record.get("recovery"), dict)]
    if not failed:
        gaps.append("required retained failed demo-route evidence is unavailable")
    if not recovered:
        gaps.append("required recovery evidence is unavailable")
    for record in recovered:
        recovery = record["recovery"]
        failed_run = recovery.get("from_run_id")
        if failed_run not in by_run_id or by_run_id[failed_run].get("status") != "failed":
            findings.append(f"recovery {record.get('run_id')} does not target a retained failed run")

    for record in failed:
        run_id = record.get("run_id")
        failure = record.get("failure")
        failure_ref = failure.get("ref") if isinstance(failure, dict) else None
        failure_path = _owned_run_path(root, run_id, failure_ref)
        if failure_path is None:
            findings.append(f"{run_id} has an escaping or invalid failure reference")
            continue
        if not failure_path.is_file():
            gaps.append(f"required failure evidence is unavailable for {run_id}")
            continue
        failure_evidence = _read_json(
            failure_path, f"failure evidence for {run_id}", findings
        )
        if failure_evidence is None:
            continue
        if failure_evidence.get("run_id") != run_id:
            findings.append(f"failure evidence for {run_id} identifies a different run")
        if failure_evidence.get("code") != "SEMANTIC_EVAL_FAILED":
            findings.append(f"failure evidence for {run_id} does not identify the eval failure")
        evaluation = record.get("evaluation")
        evaluation_ref = evaluation.get("ref") if isinstance(evaluation, dict) else None
        if failure_evidence.get("evaluation_ref") != evaluation_ref:
            findings.append(f"failure evidence for {run_id} contradicts its evaluation reference")

    for record in recovered:
        run_id = record.get("run_id")
        recovery = record["recovery"]
        recovery_path = _owned_run_path(root, run_id, recovery.get("ref"))
        if recovery_path is None:
            findings.append(f"{run_id} has an escaping or invalid recovery reference")
            continue
        if not recovery_path.is_file():
            gaps.append(f"required recovery evidence is unavailable for {run_id}")
            continue
        recovery_evidence = _read_json(
            recovery_path, f"recovery evidence for {run_id}", findings
        )
        if recovery_evidence is None:
            continue
        if recovery_evidence.get("run_id") != run_id:
            findings.append(f"recovery evidence for {run_id} identifies a different run")
        if recovery_evidence.get("from_run_id") != recovery.get("from_run_id"):
            findings.append(f"recovery evidence for {run_id} contradicts its failed predecessor")
        if recovery_evidence.get("status") != "recovered":
            findings.append(f"recovery evidence for {run_id} has an invalid status")

    examples_root = root / "examples" / "demo-route"
    proof_paths = sorted(examples_root.rglob("proof.json")) if examples_root.is_dir() else []
    if not proof_paths:
        gaps.append("required curated demo-route proof is unavailable")
    for proof_path in proof_paths:
        proof = _read_json(proof_path, str(proof_path.relative_to(root)), findings)
        if proof is None:
            continue
        source_run = proof.get("source_run_id")
        source = by_run_id.get(source_run)
        if source is None:
            findings.append(f"curated proof {proof_path.relative_to(root)} has no owned source run")
            continue
        if source.get("status") != "succeeded" or source.get("evaluation", {}).get("outcome") != "passed":
            findings.append(f"curated proof {proof_path.relative_to(root)} does not cite a passing run")
        if proof.get("source_evaluation_ref") != source.get("evaluation", {}).get("ref"):
            findings.append(f"curated proof {proof_path.relative_to(root)} contradicts its source evaluation")

    if not findings and not gaps:
        evidence.append(f"demo-route ledger has {len(records)} retained run records")
        evidence.append(
            f"retained failure and recovery artifacts are discoverable "
            f"({len(failed)} failed, {len(recovered)} recovery)"
        )
    return evidence


def audit_system(root: Path, scope: str) -> AuditResult:
    """Inspect the selected System surface without creating or changing it."""

    if scope not in AUDIT_SCOPES:
        raise ValueError(f"scope must be one of: {', '.join(AUDIT_SCOPES)}")
    root = root.resolve()
    findings: List[str] = []
    gaps: List[str] = []
    evidence: List[str] = []
    if scope in {"repository", "both"}:
        evidence.extend(_repository_audit(root, findings, gaps))
    if scope in {"demo-route", "both"}:
        evidence.extend(_workspace_audit(root, findings, gaps))
    if gaps:
        return _result("BLOCKED", scope, evidence, gaps)

    checks = _load_checks(root)
    if scope in {"repository", "both"}:
        for path in checks._public_text_files(root):
            for phrase in checks._contains_stale_language(
                path.read_text(encoding="utf-8")
            ):
                findings.append(
                    f"stale public wording {phrase!r} in {path.relative_to(root)}"
                )
    if scope in {"demo-route", "both"}:
        checks._check_ledger(
            root / "workspace" / "history" / "runs.jsonl", root, findings
        )
        checks._check_example_tree(root / "examples", findings)
    if findings:
        return _result("FAIL", scope, findings, [])
    return _result("PASS", scope, evidence, [])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only System Template audit.")
    parser.add_argument("--scope", choices=AUDIT_SCOPES, required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    result = audit_system(repository_root(), args.scope)
    print(json.dumps(result.as_dict(), sort_keys=True))
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[result.status]


if __name__ == "__main__":
    raise SystemExit(main())
