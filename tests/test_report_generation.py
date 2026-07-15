import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from shared.scripts.reporting import render_markdown_report


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_JSONL = REPO_ROOT / "tests" / "golden" / "fixture-audit.jsonl"
MANIFEST_JSON = REPO_ROOT / "tests" / "golden" / "fixture-manifest.json"
GOLDEN_REPORT = REPO_ROOT / "tests" / "golden" / "fixture-report.md"


def load_fixture_rows() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in AUDIT_JSONL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_fixture_manifest() -> dict[str, object]:
    return json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))


class ReportGenerationTest(unittest.TestCase):
    def test_render_markdown_report_contains_kpi_summary_and_priority_sections(self):
        report = render_markdown_report(load_fixture_rows(), load_fixture_manifest())

        self.assertIn("# Atomic Note Audit", report)
        self.assertIn("- Run ID: fixture-run", report)
        self.assertIn("- Total notes: 10", report)
        self.assertIn("- Average score: 73.3 / 100", report)
        self.assertIn("- No-change notes: 3 / 10 (30.0%)", report)
        self.assertIn("- Bucket counts: P0 2, P1 1, P2 2, P3 2, No changes 3", report)
        self.assertIn("- Model judgment: not run; deterministic audit complete", report)
        for heading in [
            "## P0 Critical Remediation",
            "## P1 High-Impact Remediation",
            "## P2 Meaningful Improvements",
            "## P3 Polish",
            "## No Changes",
            "## Factual-Risk Notes",
            "## Duplicate Or Overlap Candidates",
            "## Remediation Next Steps",
        ]:
            self.assertIn(heading, report)
        self.assertIn("| Note | Score | Clean | Findings | Recommendations |", report)
        self.assertIn("|---|---:|:---:|---|---|", report)

    def test_report_renders_recommendation_objects_without_dict_repr(self):
        report = render_markdown_report(load_fixture_rows(), load_fixture_manifest())

        self.assertIn("link-parent: Link this note from a structure note.", report)
        self.assertIn("split-multi-note: Split bundled ideas into separate atomic notes.", report)
        self.assertNotIn("{'mode'", report)
        self.assertNotIn('"mode":', report)

    def test_render_markdown_report_rejects_unknown_priority(self):
        rows = load_fixture_rows()
        rows[0]["priority"] = "P9"

        with self.assertRaisesRegex(ValueError, "Unexpected priority value: 'P9'"):
            render_markdown_report(rows, load_fixture_manifest())

    def test_report_lists_no_change_and_factual_risk_notes(self):
        report = render_markdown_report(load_fixture_rows(), load_fixture_manifest())

        self.assertIn("## No Changes\n\n| Note | Score | Clean | Findings | Recommendations |", report)
        self.assertIn(
            "| [[202601010101 A clean atomic note explains one durable idea in plain language "
            "and keeps the claim small enough to test against examples]] | 100 | yes | none | none |",
            report,
        )
        self.assertIn(
            "| [[202601010107 Optional Anki cards can reinforce an atomic note when the prompt "
            "tests the central claim instead of repeating the heading]] | 100 | yes | none | none |",
            report,
        )
        self.assertIn("| [[202601010106 Factual risk note]] | 84 | no |", report)
        self.assertIn("mark-factual-risk: Mark empirical, current, attributed, or sensitive-domain claims for fact checking.", report)

    def test_report_includes_duplicate_overlap_candidate(self):
        report = render_markdown_report(load_fixture_rows(), load_fixture_manifest())

        self.assertIn("## Duplicate Or Overlap Candidates\n\n| Note | Score | Clean | Findings | Recommendations |", report)
        self.assertIn("| [[202601010109 Duplicate candidate note]] | 92 | no |", report)
        self.assertIn("duplicate_overlap: Review this note against related notes for possible overlap.", report)
        self.assertIn("duplicate-overlap-review: Review this note against related notes for possible overlap.", report)

    def test_rendered_fixture_matches_golden_report(self):
        report = render_markdown_report(load_fixture_rows(), load_fixture_manifest())

        self.assertEqual(report, GOLDEN_REPORT.read_text(encoding="utf-8"))

    def test_generate_report_validates_jsonl_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "reports" / "audit.md"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.generate_report",
                    "--jsonl",
                    str(AUDIT_JSONL),
                    "--manifest",
                    str(MANIFEST_JSON),
                    "--output",
                    str(output),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(output))
            self.assertTrue(output.exists())
            self.assertIn("# Atomic Note Audit", output.read_text(encoding="utf-8"))

    def test_generate_report_rejects_invalid_jsonl_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            invalid_jsonl = Path(tmp) / "invalid.jsonl"
            invalid_jsonl.write_text("{not json}\n", encoding="utf-8")
            output = Path(tmp) / "report.md"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.generate_report",
                    "--jsonl",
                    str(invalid_jsonl),
                    "--manifest",
                    str(MANIFEST_JSON),
                    "--output",
                    str(output),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            self.assertIn(str(invalid_jsonl), result.stderr)

    def test_generate_report_rejects_invalid_manifest_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            invalid_manifest = Path(tmp) / "manifest.json"
            invalid_manifest.write_text(
                json.dumps({"run_id": "bad-manifest", "priority_counts": {}}),
                encoding="utf-8",
            )
            output = Path(tmp) / "report.md"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.generate_report",
                    "--jsonl",
                    str(AUDIT_JSONL),
                    "--manifest",
                    str(invalid_manifest),
                    "--output",
                    str(output),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            self.assertIn(str(invalid_manifest), result.stderr)
            self.assertIn("Missing required keys", result.stderr)

    def test_generate_report_rejects_mismatched_manifest_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            mismatched_manifest_data = load_fixture_manifest()
            mismatched_manifest_data["run_id"] = "other-run"
            mismatched_manifest_data["total_notes"] = 10
            mismatched_manifest_data["row_status_counts"] = {
                "complete": 10,
                "reused_cache": 0,
                "error": 0,
                "skipped": 0,
            }
            mismatched_manifest_data["priority_counts"] = {
                "P0": 0,
                "P1": 10,
                "P2": 0,
                "P3": 0,
                "no_change": 0,
            }
            mismatched_manifest = Path(tmp) / "manifest.json"
            mismatched_manifest.write_text(
                json.dumps(mismatched_manifest_data),
                encoding="utf-8",
            )
            output = Path(tmp) / "report.md"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.generate_report",
                    "--jsonl",
                    str(AUDIT_JSONL),
                    "--manifest",
                    str(mismatched_manifest),
                    "--output",
                    str(output),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            self.assertIn("manifest run_id does not match audit rows", result.stderr)

    def test_generate_report_supports_direct_script_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "direct-report.md"
            script = REPO_ROOT / "shared" / "scripts" / "generate_report.py"
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--jsonl",
                    str(AUDIT_JSONL),
                    "--manifest",
                    str(MANIFEST_JSON),
                    "--output",
                    str(output),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(output))
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
