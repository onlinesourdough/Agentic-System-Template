#!/usr/bin/env python3
"""Deterministic, dependency-light proof tracer for System Template.

The tracer is deliberately a small filesystem workflow, not a framework. It
keeps operational evidence under workspace, appends one ledger line per run,
and promotes an example only when the caller asks for curation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_TIMESTAMP = "2026-01-01T00:00:00Z"
ROUTE = "demo"
INPUT_REF = "fixture://system-template/demo-route"
SEMANTIC_FAILURE_FIXTURE_REF = "workspace/engine/fixtures/semantic-wrong-output.json"
EXPECTED_RESULT = "The primary System demo route completed deterministically."
RUN_ID_PATTERN = re.compile(r"^run-(\d{4,})$")
OUTPUT_FIELDS = {
    "previous_run_id", "previous_run_relation", "recovered_from", "result",
    "route", "run_id", "status",
}


class TraceError(RuntimeError):
    """Raised when the minimal trace cannot preserve its evidence."""


@dataclass(frozen=True)
class TraceResult:
    run_id: str
    status: str
    output_path: Path
    evaluation_path: Path
    proof_path: Path
    ledger_path: Path
    example_path: Optional[Path]
    previous_run_id: Optional[str]
    previous_run_relation: Optional[str]
    inspected_prior_runs: int
    failure_path: Optional[Path]
    recovery_path: Optional[Path]


def repository_root() -> Path:
    """Return the repository root derived from this file, not the cwd."""

    return Path(__file__).resolve().parents[2]


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path, root: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TraceError(f"cannot read JSON fixture {_relative(path, root)}: {exc}") from exc
    if not isinstance(value, dict):
        raise TraceError(f"JSON fixture {_relative(path, root)} must be an object")
    return value


def _read_ledger(ledger_path: Path) -> List[Dict[str, Any]]:
    if not ledger_path.exists():
        return []
    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TraceError(f"ledger line {line_number} is not valid JSON: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise TraceError(f"ledger line {line_number} must be an object")
        records.append(record)
    return records


def _next_run_id(records: List[Dict[str, Any]]) -> str:
    numbers = []
    for record in records:
        match = RUN_ID_PATTERN.match(str(record.get("run_id", "")))
        if match:
            numbers.append(int(match.group(1)))
    return f"run-{(max(numbers, default=0) + 1):04d}"


def _append_ledger(ledger_path: Path, record: Dict[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")


def validate_output_structure(output: Dict[str, Any]) -> List[str]:
    """Validate the tracer's local output shape without judging relevance."""

    errors = []
    missing = sorted(OUTPUT_FIELDS.difference(output))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
    if output.get("route") != ROUTE:
        errors.append("route must be demo")
    if output.get("status") != "succeeded":
        errors.append("output status must be succeeded")
    if not isinstance(output.get("run_id"), str) or not output.get("run_id"):
        errors.append("run_id must be a non-empty string")
    if not isinstance(output.get("result"), str) or not output.get("result"):
        errors.append("result must be a non-empty string")
    if output.get("previous_run_relation") not in {None, "predecessor", "recovery"}:
        errors.append("previous_run_relation is invalid")
    if output.get("previous_run_id") is not None and not isinstance(output.get("previous_run_id"), str):
        errors.append("previous_run_id must be null or a string")
    if output.get("recovered_from") is not None and not isinstance(output.get("recovered_from"), str):
        errors.append("recovered_from must be null or a string")
    return errors


def evaluate_demo_output(output: Dict[str, Any], output_ref: str) -> Dict[str, Any]:
    """Perform one System-local semantic check without changing ``output``."""

    structure_errors = validate_output_structure(output)
    result_matches = output.get("result") == EXPECTED_RESULT
    semantic_passed = not structure_errors and result_matches
    return {
        "checkpoint": "the demo route reports its required completion result",
        "failure_action": (
            "retain this output unchanged, append the failed run, and replay it "
            "from a new recovery run with the corrected local result"
        ),
        "observable_checks": [
            {"name": "local output structure is valid", "passed": not structure_errors, "detail": structure_errors},
            {"name": "route is the demo route", "passed": output.get("route") == ROUTE},
            {"name": "result is the required demo completion claim", "passed": result_matches},
        ],
        "outcome": "passed" if semantic_passed else "failed",
        "output_ref": output_ref,
        "required_evidence": [output_ref],
        "subject": "System Template demo-route completion claim",
    }


def _completed_output(run_id: str, previous_run_id: Optional[str], previous_run_relation: Optional[str], recovered_from: Optional[str]) -> Dict[str, Any]:
    return {
        "previous_run_id": previous_run_id,
        "previous_run_relation": previous_run_relation,
        "recovered_from": recovered_from,
        "result": EXPECTED_RESULT,
        "route": ROUTE,
        "run_id": run_id,
        "status": "succeeded",
    }


def _semantic_failure_output(root: Path, run_id: str, previous_run_id: Optional[str], previous_run_relation: Optional[str]) -> Dict[str, Any]:
    fixture = _read_json(root / SEMANTIC_FAILURE_FIXTURE_REF, root)
    fixture.update({
        "previous_run_id": previous_run_id,
        "previous_run_relation": previous_run_relation,
        "recovered_from": None,
        "run_id": run_id,
    })
    return fixture


def _promote_example(root: Path, run_id: str, output: Dict[str, Any], proof: Dict[str, Any]) -> Path:
    """Write a self-contained proof only after explicit curation."""

    example_dir = root / "examples" / "demo-route" / run_id
    example_proof = {
        "assertions": proof["assertions"],
        "curated": True,
        "evaluation_outcome": proof["evaluation_outcome"],
        "example": "demo-route",
        "result": output["result"],
        "route": output["route"],
        "source_evaluation_ref": proof["evaluation_ref"],
        "source_proof_ref": proof["proof_ref"],
        "source_run_id": run_id,
        "status": output["status"],
    }
    _write_json(example_dir / "proof.json", example_proof)
    (example_dir / "README.md").write_text(
        "# Curated demo-route proof\n\n"
        "This directory is an intentionally curated, standalone proof of one deterministic System Template route.\n\n"
        f"- Run: `{run_id}`\n- Route: `{output['route']}`\n- Status: `{output['status']}`\n"
        f"- Result: {output['result']}\n- Local semantic eval: `{proof['evaluation_outcome']}`\n\n"
        "The complete assertions are in `proof.json`. This example is a readable proof artifact; it is not an executable dependency.\n",
        encoding="utf-8",
    )
    return example_dir


def trace_once(root: Path, *, promote_example: bool = False, simulate_failure: bool = False, recover: bool = False, timestamp: str = DEFAULT_TIMESTAMP) -> TraceResult:
    """Run one deterministic route and preserve its evidence.

    ``simulate_failure`` selects a structurally valid, semantically wrong
    fixture. ``recover`` consumes the latest unresolved failed run and replays
    it with the corrected local output.
    """

    root = root.resolve()
    if simulate_failure and recover:
        raise TraceError("choose either --simulate-failure or --recover")
    if simulate_failure and promote_example:
        raise TraceError("a semantic-eval failure cannot be promoted as proof")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp):
        raise TraceError("timestamp must use UTC form YYYY-MM-DDTHH:MM:SSZ")

    ledger_path = root / "workspace" / "history" / "runs.jsonl"
    records = _read_ledger(ledger_path)
    relevant = [record for record in records if record.get("input_ref") == INPUT_REF]
    recovered_failures = {
        recovery.get("from_run_id")
        for record in relevant
        if isinstance(recovery := record.get("recovery"), dict) and recovery.get("from_run_id")
    }
    failed_prior = next((record for record in reversed(relevant) if record.get("status") == "failed" and record.get("run_id") not in recovered_failures), None)
    if recover and failed_prior is None:
        raise TraceError("--recover requires a previous unresolved failed demo run")

    previous = failed_prior if recover else (relevant[-1] if relevant else None)
    previous_run_id = previous.get("run_id") if previous else None
    previous_run_relation = None if previous_run_id is None else ("recovery" if recover else "predecessor")
    run_id = _next_run_id(records)
    run_dir = root / "workspace" / "runs" / run_id
    if run_dir.exists():
        raise TraceError(f"run directory already exists: {_relative(run_dir, root)}")
    run_dir.mkdir(parents=True)

    output_path = run_dir / "output.json"
    evaluation_path = run_dir / "evaluation.json"
    proof_path = run_dir / "proof.json"
    failure_path: Optional[Path] = None
    recovery_path: Optional[Path] = None
    recovered_from = failed_prior.get("run_id") if recover and failed_prior else None
    input_record = {
        "input_ref": INPUT_REF,
        "request_kind": "semantic-eval-replay" if (simulate_failure or recover) else "deterministic-demo",
        "route": ROUTE,
    }
    if simulate_failure:
        input_record["fixture_ref"] = SEMANTIC_FAILURE_FIXTURE_REF
    _write_json(run_dir / "input.json", input_record)

    output = (_semantic_failure_output(root, run_id, previous_run_id, previous_run_relation) if simulate_failure else _completed_output(run_id, previous_run_id, previous_run_relation, recovered_from))
    _write_json(output_path, output)
    output_ref = _relative(output_path, root)
    evaluation = evaluate_demo_output(output, output_ref)
    _write_json(evaluation_path, evaluation)
    evaluation_ref = _relative(evaluation_path, root)
    status = "succeeded" if evaluation["outcome"] == "passed" else "failed"
    recovery: Optional[Dict[str, Any]] = None

    if status == "failed":
        failure_path = run_dir / "failure.json"
        _write_json(failure_path, {
            "code": "SEMANTIC_EVAL_FAILED",
            "evaluation_ref": evaluation_ref,
            "message": "The output is structurally valid but fails the local semantic checkpoint.",
            "recoverable": True,
            "run_id": run_id,
        })
        assertions = [
            "the output passed local structural validation",
            "the local semantic eval rejected the irrelevant completion claim without editing it",
            "the failed run remained available for a later recovery replay",
        ]
    elif recover:
        recovery_path = run_dir / "recovery.json"
        recovery = {
            "action": "replay the local semantic-eval case with the corrected demo output",
            "correction": "use the required demo completion result",
            "from_run_id": failed_prior.get("run_id"),
            "run_id": run_id,
            "status": "recovered",
        }
        _write_json(recovery_path, recovery)
        assertions = [
            "the primary skill inspected a prior semantic-eval failure",
            "the replay used the corrected local result and passed the local semantic eval",
            "recovery evidence points to the failed predecessor",
        ]
    else:
        assertions = [
            "the primary skill selected the demo route",
            "deterministic validation and the separate local semantic eval passed",
            "output and proof were written under workspace/runs and one ledger record was appended",
        ]

    proof = {
        "assertions": assertions,
        "curated_example_ref": f"examples/demo-route/{run_id}/" if promote_example else None,
        "evaluation_outcome": evaluation["outcome"],
        "evaluation_ref": evaluation_ref,
        "failure_ref": _relative(failure_path, root) if failure_path else None,
        "input_ref": INPUT_REF,
        "ledger_ref": f"workspace/history/runs.jsonl#{run_id}",
        "previous_run_id": previous_run_id,
        "previous_run_relation": previous_run_relation,
        "proof_ref": _relative(proof_path, root),
        "recovery_ref": _relative(recovery_path, root) if recovery_path else None,
        "run_id": run_id,
        "status": status,
    }
    _write_json(proof_path, proof)
    ledger_record = {
        "evaluation": {"outcome": evaluation["outcome"], "ref": evaluation_ref},
        "failure": {"code": "SEMANTIC_EVAL_FAILED", "ref": _relative(failure_path, root)} if failure_path else None,
        "finished_at": timestamp,
        "input_ref": INPUT_REF,
        "output_ref": output_ref,
        "previous_run_id": previous_run_id,
        "previous_run_relation": previous_run_relation,
        "proof_ref": _relative(proof_path, root),
        "recovery": {"from_run_id": failed_prior.get("run_id"), "ref": _relative(recovery_path, root)} if recovery_path and failed_prior else None,
        "run_id": run_id,
        "started_at": timestamp,
        "status": status,
    }
    _append_ledger(ledger_path, ledger_record)
    example_path = _promote_example(root, run_id, output, proof) if promote_example else None
    return TraceResult(run_id, status, output_path, evaluation_path, proof_path, ledger_path, example_path, previous_run_id, previous_run_relation, len(relevant), failure_path, recovery_path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic System Template filesystem proof.")
    parser.add_argument("--promote-example", action="store_true", help="intentionally curate this successful run into examples/")
    parser.add_argument("--simulate-failure", action="store_true", help="run the structurally valid but semantically wrong local fixture")
    parser.add_argument("--recover", action="store_true", help="replay the latest failed demo run with its corrected local output")
    parser.add_argument("--timestamp", default=DEFAULT_TIMESTAMP, help=f"UTC timestamp (default: {DEFAULT_TIMESTAMP})")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = trace_once(repository_root(), promote_example=args.promote_example, simulate_failure=args.simulate_failure, recover=args.recover, timestamp=args.timestamp)
    except TraceError as exc:
        print(f"trace failed: {exc}", file=sys.stderr)
        return 1
    root = repository_root()
    print(f"route: {ROUTE}")
    print(f"inspected_prior_runs: {result.inspected_prior_runs}")
    print(f"run: {result.run_id}")
    print(f"status: {result.status}")
    print(f"output: {_relative(result.output_path, root)}")
    print(f"evaluation: {_relative(result.evaluation_path, root)}")
    print(f"proof: {_relative(result.proof_path, root)}")
    print(f"ledger: {_relative(result.ledger_path, root)}")
    if result.failure_path:
        print(f"failure: {_relative(result.failure_path, root)}")
    if result.recovery_path:
        print(f"recovery: {_relative(result.recovery_path, root)}")
    print(f"curated_example: {_relative(result.example_path, root) + '/' if result.example_path else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
