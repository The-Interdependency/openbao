#!/usr/bin/env python3
# ratios: loc_comments=148:11 imports_exports=8:12 calls_definitions=56:12
"""Record skill-lib exposure and derive evidence-qualified maturity.

Usage guidance:
    python tools/skill_usage.py record canon --outcome success
    python tools/skill_usage.py record canon --outcome failed --critical
    python tools/skill_usage.py resolve-critical canon
    python tools/skill_usage.py status

Installed plugins should pass ``--state "$PLUGIN_DATA/usage.json"``. Without
``--state``, data is stored in ``.skill-lib/usage.json`` under the current
working directory. Writes are atomic. The file contains no prompt content.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DESIGNATIONS = (
    ("experimental", 0),
    ("field-test", 10),
    ("operational", 25),
    ("reliable", 50),
    ("daily-use", 100),
)
OUTCOMES = ("success", "corrected", "failed", "abandoned", "hmmm")
ASSESSED_OUTCOMES = OUTCOMES[:-1]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def empty_state() -> dict[str, Any]:
    return {"schema_version": 1, "skills": {}}


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_state()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("skills"), dict):
        raise ValueError(f"{path}: unsupported usage-state schema")
    return data


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def new_record() -> dict[str, Any]:
    return {
        "use_count": 0,
        "outcomes": {outcome: 0 for outcome in OUTCOMES},
        "unresolved_critical_failures": 0,
        "last_used": None,
    }


def nominal_designation(use_count: int) -> str:
    result = DESIGNATIONS[0][0]
    for name, threshold in DESIGNATIONS:
        if use_count >= threshold:
            result = name
    return result


def effective_designation(record: dict[str, Any]) -> str:
    nominal = nominal_designation(int(record["use_count"]))
    nominal_rank = next(i for i, item in enumerate(DESIGNATIONS) if item[0] == nominal)
    outcomes = record["outcomes"]
    assessed = sum(int(outcomes[name]) for name in ASSESSED_OUTCOMES)
    success_rate = int(outcomes["success"]) / assessed if assessed else None

    cap_rank = len(DESIGNATIONS) - 1
    if assessed < 5 or (success_rate is not None and success_rate < 0.80):
        cap_rank = 1
    elif success_rate is not None and success_rate < 0.90:
        cap_rank = 2
    elif success_rate is not None and success_rate < 0.95:
        cap_rank = 3
    if int(record["unresolved_critical_failures"]) > 0:
        cap_rank = min(cap_rank, 1)
    return DESIGNATIONS[min(nominal_rank, cap_rank)][0]


def summarize(name: str, record: dict[str, Any]) -> dict[str, Any]:
    outcomes = record["outcomes"]
    assessed = sum(int(outcomes[item]) for item in ASSESSED_OUTCOMES)
    return {
        "skill": name,
        "use_count": int(record["use_count"]),
        "outcomes": outcomes,
        "assessed_success_rate": (
            round(int(outcomes["success"]) / assessed, 4) if assessed else None
        ),
        "nominal_designation": nominal_designation(int(record["use_count"])),
        "effective_designation": effective_designation(record),
        "unresolved_critical_failures": int(
            record["unresolved_critical_failures"]
        ),
        "last_used": record["last_used"],
    }


def record_use(
    state: dict[str, Any], name: str, outcome: str, critical: bool
) -> dict[str, Any]:
    record = state["skills"].setdefault(name, new_record())
    record["use_count"] += 1
    record["outcomes"][outcome] += 1
    record["last_used"] = now_utc()
    if critical:
        record["unresolved_critical_failures"] += 1
    return summarize(name, record)


def resolve_critical(state: dict[str, Any], name: str) -> dict[str, Any]:
    record = state["skills"].setdefault(name, new_record())
    if record["unresolved_critical_failures"] > 0:
        record["unresolved_critical_failures"] -= 1
    return summarize(name, record)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    state_options = {
        "type": Path,
        "help": "Writable usage-state path (default: .skill-lib/usage.json).",
    }
    result.add_argument(
        "--state", default=Path(".skill-lib/usage.json"), **state_options
    )
    commands = result.add_subparsers(dest="command", required=True)

    record = commands.add_parser("record", help="Record one material skill use.")
    record.add_argument("--state", default=argparse.SUPPRESS, **state_options)
    record.add_argument("skill")
    record.add_argument("--outcome", choices=OUTCOMES, default="hmmm")
    record.add_argument("--critical", action="store_true")

    resolve = commands.add_parser(
        "resolve-critical", help="Resolve one recorded critical failure."
    )
    resolve.add_argument("--state", default=argparse.SUPPRESS, **state_options)
    resolve.add_argument("skill")

    status = commands.add_parser("status", help="Report one or every skill.")
    status.add_argument("--state", default=argparse.SUPPRESS, **state_options)
    status.add_argument("skill", nargs="?")
    return result


def main() -> int:
    args = parser().parse_args()
    state = load_state(args.state)

    if args.command == "record":
        output: Any = record_use(state, args.skill, args.outcome, args.critical)
        atomic_write(args.state, state)
    elif args.command == "resolve-critical":
        output = resolve_critical(state, args.skill)
        atomic_write(args.state, state)
    elif args.skill:
        output = summarize(args.skill, state["skills"].get(args.skill, new_record()))
    else:
        output = [
            summarize(name, record)
            for name, record in sorted(state["skills"].items())
        ]

    print(json.dumps({"state": str(args.state), "result": output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# ratios: loc_comments=148:11 imports_exports=8:12 calls_definitions=56:12
