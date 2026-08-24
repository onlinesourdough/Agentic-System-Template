#!/usr/bin/env python3
"""Structural and stale-path checks for the standalone seed."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


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
    ".agents/skills/system-template/SKILL.md",
    "workspace/runs",
    "workspace/history/runs.jsonl",
    "workspace/learning",
    "workspace/engine/tracer.py",
    "workspace/engine/checks.py",
    "workspace/engine/tests/test_template.py",
    "docs/contract.md",
    "docs/validation.md",
)
STALE_ROOT_NAMES = {"engine", "scripts", "tests"}
CURATED_EXAMPLE_FIELDS = {"curated", "example", "source_run_id", "status"}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _public_text_files(root: Path) -> Iterable[Path]:
    roots = [root / "AGENTS.md", root / "README.md", root / ".agents", root / "docs", root / "examples"]
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
        "hand" + "off",
        "sche" + "ma",
        "runtime " + "dependency",
        "runtime" + "-dependency",
        "shared " + "package",
        "central " + "database",
        "raw " + "prompt",
    )
    lowered = text.lower()
    return [phrase for phrase in forbidden if phrase in lowered]


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

    for path in (root / "workspace", root / "examples", root / "docs"):
        if path.is_symlink():
            errors.append(f"functional root must be a directory, not a symlink: {path.name}/")

    history = root / "workspace" / "history" / "runs.jsonl"
    if history.exists() and not history.is_file():
        errors.append("workspace/history/runs.jsonl must be a file")

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
