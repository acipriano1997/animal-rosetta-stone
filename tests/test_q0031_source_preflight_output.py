"""Source-free regression for the Q0031 preflight's exclusive output behavior.

No empirical rows, source CSVs, author data or provider identities are used.
Run: python -m unittest discover -s tests -p 'test_q0031*.py' -v
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "q0031_source_preflight.py"
spec = importlib.util.spec_from_file_location("q0031_source_preflight", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ExclusiveOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ars-q0031-output-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "candidate.csv"
        self.source.write_bytes(b"private-source-sentinel-do-not-overwrite\n")
        self.expected = self.source.read_bytes()

    def run_report(self, report_path):
        # Stub empirical validators: ONLY output-path safety is under test.
        args = [str(SCRIPT), "--spider", str(self.source), "--spectra", str(self.source),
                "--playback", str(self.source), "--output", str(report_path)]
        with mock.patch.object(sys, "argv", args), \
                mock.patch.object(mod, "source_bytes", return_value=(b"", {"fingerprint_status": "SYNTHETIC"})), \
                mock.patch.object(mod, "spider", return_value={"synthetic": True}), \
                mock.patch.object(mod, "spectra", return_value={"synthetic": True}), \
                mock.patch.object(mod, "playback", return_value={"synthetic": True}), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            mod.main()
        self.assertEqual(self.source.read_bytes(), self.expected)
        return json.loads(stdout.getvalue())

    def test_new_output_created_without_source_data_or_gate_promotion(self):
        dst = self.root / "new-receipt.json"
        output = self.run_report(dst)
        self.assertEqual(json.loads(dst.read_text()), output)
        self.assertEqual(output["provider_file_digest_status"], "HELD_NOT_OBTAINED")
        self.assertEqual(output["q0031_cross_modal_generalization"], "NOT_MET")
        self.assertTrue(output["no_scientific_or_gdm_admission"])
        self.assertNotIn(self.expected.decode().strip(), dst.read_text())

    def test_existing_report_cannot_be_overwritten(self):
        dst = self.root / "existing-report.json"
        dst.write_bytes(b"PREEXISTING-REPORT")
        with self.assertRaisesRegex(mod.QAError, "refusing to overwrite"):
            self.run_report(dst)
        self.assertEqual(dst.read_bytes(), b"PREEXISTING-REPORT")

    def test_input_path_cannot_be_overwritten(self):
        with self.assertRaisesRegex(mod.QAError, "refusing to overwrite"):
            self.run_report(self.source)
        self.assertEqual(self.source.read_bytes(), self.expected)

    def test_symlink_to_input_cannot_be_overwritten(self):
        alias = self.root / "alias.json"
        alias.symlink_to(self.source)
        with self.assertRaisesRegex(mod.QAError, "refusing to overwrite"):
            self.run_report(alias)
        self.assertEqual(self.source.read_bytes(), self.expected)

    def test_hardlink_to_input_cannot_be_overwritten(self):
        alias = self.root / "hardlink.json"
        os.link(self.source, alias)
        with self.assertRaisesRegex(mod.QAError, "refusing to overwrite"):
            self.run_report(alias)
        self.assertEqual(self.source.read_bytes(), self.expected)

    def test_dangling_symlink_does_not_create_target(self):
        target = self.root / "absent.csv"
        alias = self.root / "dangling.json"
        alias.symlink_to(target)
        with self.assertRaisesRegex(mod.QAError, "refusing to overwrite"):
            self.run_report(alias)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
