# ratios: loc_comments=93:10 imports_exports=12:2 calls_definitions=57:9
"""Run with python -m unittest discover -s scripts/tests -p test_msdmd_inventory.py.

These fixtures verify inventory integrity and disclosure, not OpenBao behavior.
"""
# === CHECKS ===
# id: check_openbao_msdmd_inventory
#   proves: openbao_msdmd_pin_before_import, openbao_msdmd_unknowns_remain_visible, openbao_msdmd_required_scope_fails_closed
#   call: self::test_inventory_contract
#   mutates: filesystem
#   cleanup: tempdir_teardown
# === END CHECKS ===
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/skills"))
spec = importlib.util.spec_from_file_location("openbao_inventory", ROOT / "scripts/msdmd_inventory.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
from msdmd.collect import collect


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = {"skill_lib_commit": "a" * 40, "repository": "example/vault",
                       "required_sources": [], "required_facts": [], "hmmm": ["behavior unverified"]}
        (self.root / "metadata").mkdir()
        base = self.root / ".agents/skills/msdmd"
        base.mkdir(parents=True)
        (base / "reader.py").write_bytes(b"# inert fixture\n")
        self.vendor = {"source_repository": "The-Interdependency/skill-lib", "source_commit": "a" * 40,
                       "files": {"msdmd/reader.py": hashlib.sha256(b"# inert fixture\n").hexdigest()}}
        (self.root / inventory.VENDOR).write_text(json.dumps(self.vendor))
        (self.root / inventory.POLICY).write_text(json.dumps(self.policy))

    def test_pin_rejects_tampering_and_added_python(self):
        inventory.verify_vendor(self.root, self.policy)
        path = self.root / ".agents/skills/msdmd/reader.py"
        path.write_text("changed")
        with self.assertRaisesRegex(ValueError, "differs"):
            inventory.verify_vendor(self.root, self.policy)
        path.write_bytes(b"# inert fixture\n")
        (path.parent / "extra.py").write_text("# extra")
        with self.assertRaisesRegex(ValueError, "unrecorded"):
            inventory.verify_vendor(self.root, self.policy)

    def test_pin_rejects_path_escape_and_different_commit(self):
        with self.assertRaisesRegex(ValueError, "pin"):
            inventory.verify_vendor(self.root, dict(self.policy, skill_lib_commit="b" * 40))
        self.vendor["files"] = {"../../outside.py": "b" * 64}
        (self.root / inventory.VENDOR).write_text(json.dumps(self.vendor))
        with self.assertRaisesRegex(ValueError, "path"):
            inventory.verify_vendor(self.root, self.policy)

    def test_pin_failure_does_not_import_or_collect(self):
        (self.root / inventory.VENDOR).unlink()
        with patch.object(inventory, "ROOT", self.root), patch("msdmd.collect.collect") as collecting:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(3, inventory.main(["--write"]))
            collecting.assert_not_called()

    def test_report_preserves_gaps_and_binds_facts(self):
        (self.root / "a.go").write_text('package p\nvar V = new("value")\n')
        (self.root / "unknown.hcl").write_text('path "a" {}\n')
        result = collect(self.root, "example/vault", snapshot_identity=True)
        report = inventory.summarize(result, {"runtime": "fixture"}, self.policy, self.vendor)
        self.assertFalse(report["strict_clean"])
        self.assertEqual(result["diagnostics"], report["diagnostics"])
        self.assertEqual(result["discovery"], report["discovery"])
        self.assertGreater(report["coverage"]["unsupported_files"], 0)
        before = report["collection_sha256"]
        result["facts"][0]["native"]["value"] = "different source observation"
        self.assertNotEqual(before, inventory.digest(result))

    def test_required_or_runtime_failure_preserves_previous_outputs(self):
        report = self.root / inventory.REPORT
        output = self.root / inventory.OUTPUT
        for code in ("required_source_not_supported", "required_fact_unresolved", "reader_dependency_unavailable",
                     "root_git_ignored", "duplicate_native_fact_address", "duplicate_block_id"):
            report.write_text("previous report")
            output.write_text("previous collection")
            result = {"diagnostics": [{"code": code, "severity": "error", "reader_id": "fixture"}]}
            with patch.object(inventory, "ROOT", self.root), patch("msdmd.collect.collect", return_value=result):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(3, inventory.main(["--write"]))
            self.assertEqual("previous report", report.read_text())
            self.assertEqual("previous collection", output.read_text())

    def test_check_detects_report_drift_without_writing(self):
        result = collect(self.root, "example/vault", snapshot_identity=True)
        report = self.root / inventory.REPORT
        report.write_text("stale report")
        with patch.object(inventory, "ROOT", self.root), patch("msdmd.collect.collect", return_value=result):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(1, inventory.main(["--check"]))
        self.assertEqual("stale report", report.read_text())


def test_inventory_contract():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(InventoryTests)
    result = unittest.TestResult()
    suite.run(result)
    assert result.wasSuccessful(), (result.errors, result.failures)
# ratios: loc_comments=93:10 imports_exports=12:2 calls_definitions=57:9
