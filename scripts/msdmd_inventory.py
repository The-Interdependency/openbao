# ratios: loc_comments=103:34 imports_exports=10:5 calls_definitions=45:5
"""Rebuild the fork's source-linked inventory; see docs/MSDMD.md for usage.

GPT generated; context, prompt Erin Spencer. This collector never runs OpenBao.
The checked report retains all diagnostic and discovery records. Its digest
binds the full schema-2 collection, generated locally as openbao_msdmd.ts.
"""
# === MODULE_BUILD ===
# id: openbao_msdmd_inventory
#   module_name: msdmd_inventory
#   module_kind: instrument
#   summary: collect fork metadata using an exact canonical skill-lib pin
#   owner: The Interdependency
#   public_surface: --write, --check, --strict, --verify-pin
#   auth_boundary: none
#   storage_boundary: repository report and generated collection
#   network_boundary: none during collection
#   user_data_boundary: repository source only
#   admin_only: false
#   tests: scripts/tests/test_msdmd_inventory.py
#   rollout: opt-in metadata collection
#   rollback: revert fork adoption files
# === END MODULE_BUILD ===
# === CONTRACTS ===
# id: openbao_msdmd_pin_before_import
#   given: missing or changed vendored skill files
#   then: reject collection before importing the collector
# id: openbao_msdmd_unknowns_remain_visible
#   given: partial, unsupported or invalid source metadata
#   then: preserve diagnostics and discovery; never infer verified vault behavior
# id: openbao_msdmd_required_scope_fails_closed
#   given: unavailable readers or unresolved required metadata
#   then: do not replace the accepted report or generated collection
# === END CONTRACTS ===
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
POLICY = "metadata/msdmd-policy.json"
VENDOR = "metadata/msdmd-vendor.json"
REPORT = "metadata/msdmd-report.json"
OUTPUT = "openbao_msdmd.ts"


def digest(value: object) -> str:
    """Hash canonical JSON without allocating a second full encoded collection."""
    result = hashlib.sha256()
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    for chunk in encoder.iterencode(value):
        result.update(chunk.encode("utf-8"))
    return result.hexdigest()


def verify_vendor(root: Path, policy: dict) -> dict:
    manifest = json.loads((root / VENDOR).read_text())
    commit = manifest.get("source_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or commit != policy["skill_lib_commit"]:
        raise ValueError("canonical source pin is missing or inconsistent")
    if manifest.get("source_repository") != "The-Interdependency/skill-lib" or not manifest.get("files"):
        raise ValueError("canonical source inventory is missing")
    base = root / ".agents/skills"
    for name, expected in manifest["files"].items():
        relative = Path(name)
        path = base / relative
        if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.resolve().is_relative_to(base.resolve()):
            raise ValueError("invalid vendored source path")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"vendored file differs from recorded pin: {name}")
    extras = [path.relative_to(base).as_posix() for path in base.rglob("*.py")
              if "__pycache__" not in path.parts and "node_modules" not in path.parts
              and path.relative_to(base).as_posix() not in manifest["files"]]
    if extras:
        raise ValueError("unrecorded Python files under vendored skills")
    return manifest


def fatal_diagnostics(collection: dict) -> list[dict]:
    # Other parser diagnostics remain in the report and fail optional --strict.
    from msdmd.collect import runtime_unavailable, VISIBILITY_FAILURE_CODES
    required = [d for d in collection["diagnostics"] if d["code"] in {
        "required_source_not_supported", "required_fact_unresolved",
        "source_revision_mismatch", "duplicate_native_fact_address", "duplicate_block_id"} | VISIBILITY_FAILURE_CODES]
    return runtime_unavailable(collection) + required


def summarize(collection: dict, generator: dict, policy: dict, vendor: dict) -> dict:
    errors = [d for d in collection["diagnostics"] if d["severity"] == "error"]
    return {
        "schema": "openbao.msdmd-inventory-report", "version": 1,
        "source": collection["source"], "policy": policy,
        "canonical_source": {"repository": vendor["source_repository"], "commit": vendor["source_commit"],
                             "inventory_sha256": digest(vendor)},
        "generator": generator, "collection_sha256": digest(collection),
        "counts": {key: len(collection[key]) for key in ("facts", "declarations", "edges", "conflicts", "diagnostics")},
        "native_fact_kinds": dict(sorted(Counter(f["kind"] for f in collection["facts"]).items())),
        "strict_clean": not errors, "error_count": len(errors),
        "coverage": collection["coverage"], "reader_manifests": collection["reader_manifests"],
        "reader_runs": collection["reader_runs"], "requirements": collection["requirements"],
        "discovery": collection["discovery"], "diagnostics": collection["diagnostics"],
        "conflicts": collection["conflicts"],
        "hmmm": policy["hmmm"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true", help="generate full local inventory and checked report")
    action.add_argument("--check", action="store_true", help="recollect and compare the checked report without writing")
    action.add_argument("--verify-pin", action="store_true", help="verify vendored bytes without collecting")
    parser.add_argument("--strict", action="store_true", help="also fail on every parser/identity error")
    args = parser.parse_args(argv)
    try:
        policy = json.loads((ROOT / POLICY).read_text())
        vendor = verify_vendor(ROOT, policy)
    except (OSError, ValueError, KeyError) as exc:
        print(f"MSDMD pin rejected: {exc}", file=sys.stderr)
        return 3
    if args.verify_pin:
        print(f"MSDMD pin verified: {vendor['source_commit']} ({len(vendor['files'])} files)")
        return 0
    sys.path.insert(0, str(ROOT / ".agents/skills"))
    from msdmd.collect import collect, generator_identity_components, render_typescript
    collection = collect(ROOT, policy["repository"], snapshot_identity=True,
                         generated_outputs=[OUTPUT, REPORT], required_sources=policy["required_sources"],
                         required_facts=policy["required_facts"])
    fatal = fatal_diagnostics(collection)
    if fatal:
        print(json.dumps({"fatal_diagnostics": fatal}, indent=2), file=sys.stderr)
        return 3
    report = summarize(collection, generator_identity_components(), policy, vendor)
    rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    if args.check:
        if not (ROOT / REPORT).is_file() or (ROOT / REPORT).read_text() != rendered:
            print("MSDMD report drift: review source/runtime changes, then regenerate", file=sys.stderr)
            return 1
    else:
        (ROOT / OUTPUT).write_text(render_typescript(collection, import_path="./.agents/skills/msdmd/collection"))
        (ROOT / REPORT).write_text(rendered)
    print(f"MSDMD inventory {'replays' if args.check else 'written'}: {len(collection['facts'])} facts, "
          f"{report['error_count']} error diagnostics; strict_clean={report['strict_clean']}; behavior unverified")
    return 2 if args.strict and not report["strict_clean"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
# ratios: loc_comments=103:34 imports_exports=10:5 calls_definitions=45:5
