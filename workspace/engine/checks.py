#!/usr/bin/env python3
"""Structural and stale-path checks for the standalone seed."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


VISIBLE_FUNCTIONAL_ROOTS = {"workspace", "examples", "docs"}
PUBLIC_ROOT_FILES = {"AGENTS.md", "README.md"}
TOOLCHAIN_ROOT_FILES = {
    "Cargo.lock",
    "Cargo.toml",
    "Gemfile",
    "GNUmakefile",
    "Makefile",
    "go.mod",
    "go.sum",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "pytest.ini",
    "setup.cfg",
    "tox.ini",
    "yarn.lock",
}
REQUIRED_PATHS = (
    "AGENTS.md",
    "README.md",
    ".agents/skills/README.md",
    ".agents/skills/system-template/SKILL.md",
    ".agents/skills/audit-system/SKILL.md",
    "workspace/README.md",
    "workspace/runs",
    "workspace/history/runs.jsonl",
    "workspace/learning",
    "workspace/engine/tracer.py",
    "workspace/engine/audit_system.py",
    "workspace/engine/fixtures/audit-system.json",
    "workspace/engine/fixtures/semantic-wrong-output.json",
    "workspace/engine/checks.py",
    "workspace/engine/tests/test_template.py",
    "docs/contract.md",
    "docs/validation.md",
)
STALE_ROOT_NAMES = {"engine", "scripts", "tests"}
FORBIDDEN_LOCAL_SKILL_PAYLOADS = {
    "global-skill",
    "global-skills",
    "manage-skills",
}
SKILL_NAVIGATION_MARKERS = (
    ".agents/skills/<name>/skill.md",
    "`system-template` is the primary system entrypoint",
    "`audit-system` is the separate, read-only accumulated-state audit",
    "system- or domain-specific repeatable method or eval",
    "cross-project and global skills remain harness- or plugin-installed outside this repository",
    "concrete system owns its local skills",
    "does not overwrite those skills later",
)
CURATED_EXAMPLE_FIELDS = {
    "curated",
    "evaluation_outcome",
    "example",
    "source_run_id",
    "status",
}
LEDGER_FIELDS = {
    "run_id",
    "started_at",
    "finished_at",
    "status",
    "input_ref",
    "output_ref",
    "proof_ref",
    "evaluation",
    "previous_run_id",
    "previous_run_relation",
    "failure",
    "recovery",
}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _public_text_files(root: Path) -> Iterable[Path]:
    roots = [
        root / "AGENTS.md",
        root / "README.md",
        root / ".agents",
        root / "docs",
        root / "examples",
        root / "workspace" / "README.md",
    ]
    for candidate in roots:
        if candidate.is_file():
            yield candidate
        elif candidate.is_dir():
            for path in sorted(candidate.rglob("*")):
                if path.is_file() and ".git" not in path.parts:
                    yield path


def _contains_stale_language(text: str) -> List[str]:
    # Keep these fragments assembled so the check itself does not become a
    # public artifact containing the stale wording it is designed to catch.
    forbidden = (
        "hand" + "off " + "sche" + "ma",
        "hand" + "off-" + "sche" + "ma",
        "hand" + " " + "off " + "sche" + "ma",
        "hand" + " " + "off-" + "sche" + "ma",
        "shared " + "sche" + "ma",
        "shared-" + "sche" + "ma",
        "cross-" + "system " + "sche" + "ma",
        "cross " + "system " + "sche" + "ma",
        "runtime " + "dependency",
        "runtime" + "-dependency",
        "shared " + "package",
        "central " + "database",
        "raw " + "prompt",
    )
    lowered = text.lower()
    return [phrase for phrase in forbidden if phrase in lowered]


def _check_skill_navigation(root: Path, errors: List[str]) -> None:
    """Keep repository-local skill discovery flat and owner-local."""

    skills_root = root / ".agents" / "skills"
    if not skills_root.is_dir():
        return

    for path in sorted(skills_root.rglob("*")):
        relative = path.relative_to(skills_root)
        parts = {part.lower().replace("_", "-") for part in relative.parts}
        if path.name == "SKILL.md" and len(relative.parts) != 2:
            errors.append(f"nested skill entrypoint is not allowed: {relative.as_posix()}")
        if parts.intersection(FORBIDDEN_LOCAL_SKILL_PAYLOADS):
            errors.append(
                f"Global/manage skill payload is not repository-local: {relative.as_posix()}"
            )

    navigation = skills_root / "README.md"
    if not navigation.is_file():
        return
    normalized_navigation = " ".join(
        navigation.read_text(encoding="utf-8").lower().split()
    )

    for marker in SKILL_NAVIGATION_MARKERS:
        if marker not in normalized_navigation:
            errors.append(f"skill navigation lacks required boundary: {marker}")

    for relative in ("AGENTS.md", "README.md"):
        path = root / relative
        if path.is_file() and ".agents/skills/README.md" not in path.read_text(
            encoding="utf-8"
        ):
            errors.append(f"public shell does not link skill navigation: {relative}")


def check_structure(root: Path) -> List[str]:
    """Return structural violations; an empty list means the shell is valid."""

    errors: List[str] = []
    if not root.is_dir():
        return [f"repository root is not a directory: {root}"]

    visible_entries = [entry for entry in root.iterdir() if not entry.name.startswith(".")]
    for entry in visible_entries:
        if entry.name in VISIBLE_FUNCTIONAL_ROOTS:
            continue
        if entry.name in PUBLIC_ROOT_FILES or entry.name in TOOLCHAIN_ROOT_FILES:
            continue
        if entry.name in STALE_ROOT_NAMES:
            errors.append(f"legacy root path is present: {entry.name}/")
        elif entry.is_dir() or entry.is_symlink():
            errors.append(f"visible functional root is not allowed: {entry.name}/")
        else:
            errors.append(f"visible root file is not part of the public shell: {entry.name}")

    for stale_name in sorted(STALE_ROOT_NAMES):
        if (root / stale_name).exists():
            errors.append(f"legacy root path is present: {stale_name}/")

    for relative in REQUIRED_PATHS:
        if not (root / relative).exists():
            errors.append(f"required path is missing: {relative}")

    _check_skill_navigation(root, errors)

    for path in (root / "workspace", root / "examples", root / "docs"):
        if path.is_symlink():
            errors.append(f"functional root must be a directory, not a symlink: {path.name}/")
        elif not path.is_dir():
            errors.append(f"functional root must be a directory: {path.name}/")

    history = root / "workspace" / "history" / "runs.jsonl"
    if history.exists() and not history.is_file():
        errors.append("workspace/history/runs.jsonl must be a file")
    if history.is_file():
        _check_ledger(history, root, errors)

    for path in _public_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for phrase in _contains_stale_language(text):
            errors.append(f"stale public wording {phrase!r} in {path.relative_to(root)}")

    examples_root = root / "examples"
    if examples_root.is_dir():
        _check_example_tree(examples_root, errors)

    return errors


def _check_example_tree(directory: Path, errors: List[str]) -> bool:
    """Validate curated leaves while allowing a readable run-name container."""

    visible = sorted(entry for entry in directory.iterdir() if not entry.name.startswith("."))
    if not visible:
        return True

    proof_path = directory / "proof.json"
    readme_path = directory / "README.md"
    if proof_path.exists() or readme_path.exists():
        label = directory.as_posix()
        if not proof_path.is_file() or not readme_path.is_file():
            errors.append(f"example is not a standalone proof: {label}/")
            return True
        allowed_files = {"README.md", "proof.json"}
        extra = [entry.name for entry in visible if not entry.is_dir() and entry.name not in allowed_files]
        if extra:
            errors.append(f"example contains uncurated files: {label}/ ({', '.join(extra)})")
        try:
            import json

            proof = json.loads(proof_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"example proof is not valid JSON: {label}/ ({exc})")
            return True
        if not isinstance(proof, dict) or not CURATED_EXAMPLE_FIELDS.issubset(proof):
            errors.append(f"example proof lacks curation fields: {label}/")
        elif proof.get("curated") is not True:
            errors.append(f"example is not explicitly curated: {label}/")
        return True

    found_leaf = False
    for entry in visible:
        if entry.is_dir():
            found_leaf = _check_example_tree(entry, errors) or found_leaf
        else:
            errors.append(f"example file is outside a curated proof: {entry.relative_to(directory.parent)}")
    if directory != directory.parents[0] and not found_leaf and visible:
        errors.append(f"example container has no curated proof: {directory.as_posix()}/")
    return found_leaf


def _check_evaluation_evidence(
    record: Dict[str, object],
    line_number: int,
    root: Path,
    run_id: str,
    evaluation: Dict[str, object],
    errors: List[str],
) -> None:
    """Validate the one local eval reference that makes a run inspectable."""

    outcome = evaluation.get("outcome")
    if outcome == "passed" and record.get("status") != "succeeded":
        errors.append(
            f"ledger line {line_number} has a passed evaluation for a non-succeeded run"
        )
    elif outcome == "failed" and record.get("status") != "failed":
        errors.append(
            f"ledger line {line_number} has a failed evaluation for a non-failed run"
        )

    reference = evaluation.get("ref")
    if not isinstance(reference, str) or not reference:
        return

    runs_root = (root / "workspace" / "runs").resolve()
    owning_run = (runs_root / run_id).resolve()
    try:
        owning_run.relative_to(runs_root)
    except ValueError:
        errors.append(f"ledger line {line_number} has an invalid owning run directory")
        return

    evidence_path = (root / reference).resolve()
    try:
        evidence_path.relative_to(owning_run)
    except ValueError:
        errors.append(
            f"ledger line {line_number} evaluation reference escapes its owning run"
        )
        return
    if not evidence_path.is_file():
        errors.append(
            f"ledger line {line_number} evaluation evidence is missing: {reference}"
        )
        return

    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(
            f"ledger line {line_number} evaluation evidence is not valid JSON: {exc}"
        )
        return
    if not isinstance(evidence, dict):
        errors.append(f"ledger line {line_number} evaluation evidence must be an object")
        return
    if evidence.get("outcome") != outcome:
        errors.append(
            f"ledger line {line_number} evaluation evidence outcome disagrees with the ledger"
        )
    evidence_outcome = evidence.get("outcome")
    if evidence_outcome == "passed" and record.get("status") != "succeeded":
        errors.append(
            f"ledger line {line_number} passed evaluation evidence targets a non-succeeded run"
        )
    elif evidence_outcome == "failed" and record.get("status") != "failed":
        errors.append(
            f"ledger line {line_number} failed evaluation evidence targets a non-failed run"
        )
    if evidence.get("output_ref") != record.get("output_ref"):
        errors.append(
            f"ledger line {line_number} evaluation output reference disagrees with the ledger"
        )


def _check_ledger(path: Path, root: Path, errors: List[str]) -> None:
    """Validate the small append-only ledger without imposing a framework."""

    parsed: List[Tuple[int, Dict[str, object]]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"ledger cannot be read: {path.relative_to(root)} ({exc})")
        return

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"ledger line {line_number} is not valid JSON: {exc.msg}")
            continue
        if not isinstance(record, dict):
            errors.append(f"ledger line {line_number} must be a JSON object")
            continue

        missing = sorted(LEDGER_FIELDS.difference(record))
        if missing:
            errors.append(
                f"ledger line {line_number} is missing fields: {', '.join(missing)}"
            )
        parsed.append((line_number, record))

    seen: Dict[str, Dict[str, object]] = {}
    recovered: Dict[str, int] = {}
    for line_number, record in parsed:
        run_id = record.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            errors.append(f"ledger line {line_number} must have a non-empty run_id")
            continue
        duplicate_run_id = run_id in seen
        if duplicate_run_id:
            errors.append(f"ledger line {line_number} repeats run_id {run_id!r}")

        previous_id = record.get("previous_run_id")
        relation = record.get("previous_run_relation")
        if previous_id is None and relation is not None:
            errors.append(
                f"ledger line {line_number} has a relation without a previous run"
            )
        if previous_id is not None and relation not in {"predecessor", "recovery"}:
            errors.append(
                f"ledger line {line_number} has an invalid previous-run relation"
            )
        if previous_id is not None and not isinstance(previous_id, str):
            errors.append(f"ledger line {line_number} has an invalid previous_run_id")
        if isinstance(previous_id, str) and (
            previous_id == run_id or previous_id not in seen
        ):
            errors.append(
                f"ledger line {line_number} points to a run that is not earlier in the ledger"
            )

        recovery = record.get("recovery")
        if relation == "recovery" and recovery is None:
            errors.append(f"ledger line {line_number} lacks recovery evidence")
        if recovery is not None:
            if not isinstance(recovery, dict):
                errors.append(f"ledger line {line_number} has invalid recovery evidence")
                continue
            from_id = recovery.get("from_run_id")
            if relation != "recovery":
                errors.append(
                    f"ledger line {line_number} has recovery evidence without a recovery relation"
                )
            if from_id != previous_id:
                errors.append(
                    f"ledger line {line_number} recovery target disagrees with previous_run_id"
                )
            if not isinstance(from_id, str) or seen.get(from_id, {}).get("status") != "failed":
                errors.append(
                    f"ledger line {line_number} recovery target is not a failed run"
                )
            elif from_id in recovered:
                errors.append(
                    f"ledger line {line_number} recovers failed run {from_id!r} more than once"
                )
            else:
                recovered[from_id] = line_number
            if not isinstance(recovery.get("ref"), str) or not recovery.get("ref"):
                errors.append(f"ledger line {line_number} lacks a recovery reference")

        evaluation = record.get("evaluation")
        if not isinstance(evaluation, dict):
            errors.append(f"ledger line {line_number} has invalid evaluation evidence")
        elif evaluation.get("outcome") not in {"passed", "failed"}:
            errors.append(f"ledger line {line_number} has an invalid evaluation outcome")
        elif not isinstance(evaluation.get("ref"), str) or not evaluation.get("ref"):
            errors.append(f"ledger line {line_number} lacks an evaluation reference")
        else:
            _check_evaluation_evidence(
                record, line_number, root, run_id, evaluation, errors
            )

        if record.get("status") == "failed" and record.get("failure") is None:
            errors.append(f"ledger line {line_number} failed without failure evidence")
        if not duplicate_run_id:
            seen[run_id] = record


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check the System Template shell.")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root to check (defaults to this checkout)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    root = (args.root or repository_root()).resolve()
    errors = check_structure(root)
    if errors:
        print("FAIL: System Template checks", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"PASS: structure {root}")
    print("PASS: visible roots workspace/ examples/ docs/")
    print("PASS: stale-path and public-wording scan")
    print("PASS: curated examples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
