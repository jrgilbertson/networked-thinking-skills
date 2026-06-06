import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from shared.scripts.audit_engine import audit_vault
from shared.scripts.schema_validation import validate_audit_row


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_VAULT = REPO_ROOT / "tests" / "fixtures" / "tiny-vault"


def rows_by_stem(rows):
    return {Path(row["note_path"]).stem: row for row in rows}


class AuditEngineTest(unittest.TestCase):
    def test_audit_vault_scores_every_atomic_note(self):
        rows, manifest = audit_vault(FIXTURE_VAULT, run_id="test-run")

        self.assertEqual(len(rows), 9)
        self.assertEqual(manifest["total_notes"], 9)
        for row in rows:
            validate_audit_row(row, default_scan=True)
            self.assertEqual(row["row_status"], "complete")
            self.assertFalse(row["pending_model"])

    def test_multi_note_bundle_is_p0_and_capped(self):
        rows, _ = audit_vault(FIXTURE_VAULT, run_id="test-run")
        row = rows_by_stem(rows)["202601010103 Multi note bundle"]

        self.assertEqual(row["priority"], "P0")
        self.assertLessEqual(row["score"], 49)
        self.assertIn("multi_note_file", {finding["code"] for finding in row["findings"]})

    def test_clean_dae_note_is_clean(self):
        rows, _ = audit_vault(FIXTURE_VAULT, run_id="test-run")
        row = rows_by_stem(rows)["202601010101 Clean DAE note"]

        self.assertTrue(row["clean"])
        self.assertGreaterEqual(row["score"], 90)

    def test_factual_risk_note_requires_fact_check(self):
        rows, _ = audit_vault(FIXTURE_VAULT, run_id="test-run")
        row = rows_by_stem(rows)["202601010106 Factual risk note"]

        self.assertTrue(row["factual_risk"])
        self.assertTrue(row["fact_check_required"])
        self.assertIn("factual_risk", {finding["code"] for finding in row["findings"]})

    def test_cli_jsonl_validates_and_prints_valid_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            jsonl_path = Path(tmp) / "audit.jsonl"
            manifest_path = Path(tmp) / "manifest.json"

            audit_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.audit_notes",
                    "--vault",
                    str(FIXTURE_VAULT),
                    "--run-id",
                    "test-run",
                    "--jsonl",
                    str(jsonl_path),
                    "--manifest",
                    str(manifest_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(audit_result.returncode, 0, audit_result.stderr)
            self.assertEqual(audit_result.stdout.strip(), "rows=9")

            validation_result = subprocess.run(
                [sys.executable, "-m", "shared.scripts.validate_jsonl", str(jsonl_path)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(validation_result.returncode, 0, validation_result.stderr)
            self.assertEqual(validation_result.stdout.strip(), "valid_rows=9")

    def test_manifest_includes_all_count_keys(self):
        _, manifest = audit_vault(FIXTURE_VAULT, run_id="test-run")

        self.assertEqual(
            set(manifest["row_status_counts"]),
            {"complete", "reused_cache", "error", "skipped"},
        )
        self.assertEqual(set(manifest["priority_counts"]), {"P0", "P1", "P2", "P3"})
        self.assertEqual(manifest["validation_status"], "not_run")

    def test_recommendations_are_objects(self):
        rows, _ = audit_vault(FIXTURE_VAULT, run_id="test-run")

        for row in rows:
            for recommendation in row["recommendations"]:
                self.assertIsInstance(recommendation, dict)
                self.assertEqual(set(recommendation), {"mode", "message"})

    def test_cli_writes_manifest_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            jsonl_path = Path(tmp) / "audit.jsonl"
            manifest_path = Path(tmp) / "manifest.json"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.audit_notes",
                    "--vault",
                    str(FIXTURE_VAULT),
                    "--run-id",
                    "test-run",
                    "--jsonl",
                    str(jsonl_path),
                    "--manifest",
                    str(manifest_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_id"], "test-run")
            self.assertEqual(manifest["outputs"]["audit_rows"], str(jsonl_path))
            self.assertEqual(manifest["outputs"]["manifest"], str(manifest_path))


if __name__ == "__main__":
    unittest.main()
