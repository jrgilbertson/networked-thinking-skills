import json
import io
import os
import shlex
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest

from shared.scripts.audit_engine import PROMPT_VERSION
from shared.scripts.collect_model_judgments import (
    CodexRunner,
    CommandRunner,
    RunnerInvocationError,
    _build_runner,
    _parse_args,
    collect_model_judgments,
    parse_model_output,
    render_batch_prompt,
)
from shared.scripts.schema_validation import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_VAULT = REPO_ROOT / "tests" / "fixtures" / "tiny-vault"
AUDIT_JSONL = REPO_ROOT / "tests" / "golden" / "fixture-audit.jsonl"


def load_fixture_rows() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in AUDIT_JSONL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def judgment_for(note_path: str, *, findings: list[dict[str, object]] | None = None) -> dict[str, object]:
    factual_risk = any(finding.get("code") == "factual_risk" for finding in findings or [])
    return {
        "schema_version": "1.0.0",
        "note_path": note_path,
        "dimension_adjustments": {},
        "findings": findings or [],
        "factual_risk": factual_risk,
        "factual_risk_reason": "Synthetic factual risk reason." if factual_risk else None,
        "fact_check_required": factual_risk,
        "evidence": [],
    }


def stored_judgment_for(
    note_path: str,
    *,
    prompt_version: str = "1.0.2",
) -> dict[str, object]:
    return {
        **judgment_for(note_path),
        "schema_version": "2.0.0",
        "prompt_version": prompt_version,
    }


def jsonl_for(judgments: list[dict[str, object]]) -> str:
    return "\n".join(json.dumps(judgment, sort_keys=True) for judgment in judgments) + "\n"


class FakeRunner:
    def __init__(self, outputs: list[str]):
        self.outputs = outputs
        self.prompts: list[str] = []

    def run(self, prompt: str, *, output_path: Path, stdout_path: Path, stderr_path: Path) -> None:
        if not self.outputs:
            raise AssertionError("fake runner has no output left")
        self.prompts.append(prompt)
        output_path.write_text(self.outputs.pop(0), encoding="utf-8")
        stdout_path.write_text("fake stdout", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")


class BrokenRunner:
    def __init__(self):
        self.prompts: list[str] = []

    def run(self, prompt: str, *, output_path: Path, stdout_path: Path, stderr_path: Path) -> None:
        self.prompts.append(prompt)
        raise AssertionError("programmer bug")


class OSErrorRunner:
    def __init__(self):
        self.prompts: list[str] = []

    def run(self, prompt: str, *, output_path: Path, stdout_path: Path, stderr_path: Path) -> None:
        self.prompts.append(prompt)
        raise OSError("filesystem unavailable")


class InvocationFailureRunner:
    def __init__(self):
        self.prompts: list[str] = []

    def run(self, prompt: str, *, output_path: Path, stdout_path: Path, stderr_path: Path) -> None:
        self.prompts.append(prompt)
        raise RunnerInvocationError("runner command unavailable")


class CollectModelJudgmentsTest(unittest.TestCase):
    def test_build_runner_selects_codex_and_legacy_compatibility(self):
        args = _parse_args(
            [
                "--runner",
                "codex",
                "--vault",
                str(FIXTURE_VAULT),
                "--audit-jsonl",
                str(AUDIT_JSONL),
                "--output-jsonl",
                "/tmp/model-judgments.jsonl",
                "--raw-dir",
                "/tmp/model-raw",
                "--codex-bin",
                "codex-test",
                "--model",
                "gpt-test",
                "--codex-sandbox",
                "read-only",
            ]
        )

        runner = _build_runner(args)

        self.assertIsInstance(runner, CodexRunner)
        self.assertEqual(runner.codex_bin, "codex-test")
        self.assertEqual(runner.model, "gpt-test")

        legacy_args = _parse_args(
            [
                "--vault",
                str(FIXTURE_VAULT),
                "--audit-jsonl",
                str(AUDIT_JSONL),
                "--output-jsonl",
                "/tmp/model-judgments.jsonl",
                "--raw-dir",
                "/tmp/model-raw",
            ]
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            legacy_runner = _build_runner(legacy_args)

        self.assertIsInstance(legacy_runner, CodexRunner)
        self.assertIn("compatibility path", stderr.getvalue())

    def test_build_runner_requires_command_template_for_command_runner(self):
        args = _parse_args(
            [
                "--runner",
                "command",
                "--vault",
                str(FIXTURE_VAULT),
                "--audit-jsonl",
                str(AUDIT_JSONL),
                "--output-jsonl",
                "/tmp/model-judgments.jsonl",
                "--raw-dir",
                "/tmp/model-raw",
            ]
        )

        with self.assertRaises(ValidationError):
            _build_runner(args)

    def test_build_runner_rejects_command_template_for_codex_runner(self):
        for runner_option in ([], ["--runner", "codex"]):
            with self.subTest(runner_option=runner_option):
                args = _parse_args(
                    [
                        *runner_option,
                        "--command",
                        "fake-agent",
                        "--vault",
                        str(FIXTURE_VAULT),
                        "--audit-jsonl",
                        str(AUDIT_JSONL),
                        "--output-jsonl",
                        "/tmp/model-judgments.jsonl",
                        "--raw-dir",
                        "/tmp/model-raw",
                    ]
                )

                with self.assertRaisesRegex(ValidationError, "--command requires --runner command"):
                    _build_runner(args)

    def test_build_runner_rejects_codex_options_for_command_runner(self):
        codex_only_options = [
            ("--codex-bin", "codex-test"),
            ("--model", "gpt-test"),
            ("--codex-sandbox", "read-only"),
            ("--load-user-config",),
        ]

        for option in codex_only_options:
            with self.subTest(option=option[0]):
                args = _parse_args(
                    [
                        "--runner",
                        "command",
                        "--command",
                        "fake-agent",
                        "--vault",
                        str(FIXTURE_VAULT),
                        "--audit-jsonl",
                        str(AUDIT_JSONL),
                        "--output-jsonl",
                        "/tmp/model-judgments.jsonl",
                        "--raw-dir",
                        "/tmp/model-raw",
                        *option,
                    ]
                )

                with self.assertRaisesRegex(ValidationError, option[0]):
                    _build_runner(args)

    def test_command_runner_can_write_final_response_to_output_path(self):
        rows = load_fixture_rows()[:1]
        judgments = [judgment_for(str(rows[0]["note_path"]))]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = tmp_path / "write_output.py"
            script.write_text(
                "import sys\n"
                "output = sys.argv[1]\n"
                "prompt = sys.stdin.read()\n"
                "open(output, 'w', encoding='utf-8').write(prompt)\n"
                "print('fake stdout log')\n",
                encoding="utf-8",
            )
            command = " ".join(
                shlex.quote(part)
                for part in [sys.executable, str(script), "{output_path}"]
            )
            runner = CommandRunner(
                vault_root=FIXTURE_VAULT,
                command_template=command,
                timeout_seconds=10,
            )
            output_path = tmp_path / "last-message.jsonl"
            stdout_path = tmp_path / "stdout.log"
            stderr_path = tmp_path / "stderr.log"

            runner.run(
                jsonl_for(judgments),
                output_path=output_path,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )

            self.assertEqual(parse_model_output(output_path.read_text(encoding="utf-8")), judgments)
            self.assertIn("fake stdout log", stdout_path.read_text(encoding="utf-8"))
            self.assertEqual(stderr_path.read_text(encoding="utf-8"), "")

    def test_command_runner_nonzero_exit_raises_invocation_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = tmp_path / "fail.py"
            script.write_text(
                "import sys\n"
                "sys.stderr.write('synthetic failure')\n"
                "raise SystemExit(3)\n",
                encoding="utf-8",
            )
            command = " ".join(shlex.quote(part) for part in [sys.executable, str(script)])
            runner = CommandRunner(
                vault_root=FIXTURE_VAULT,
                command_template=command,
                timeout_seconds=10,
            )
            output_path = tmp_path / "last-message.jsonl"
            stdout_path = tmp_path / "stdout.log"
            stderr_path = tmp_path / "stderr.log"

            with self.assertRaisesRegex(RunnerInvocationError, "exit 3"):
                runner.run(
                    "prompt",
                    output_path=output_path,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                )

            self.assertFalse(output_path.exists())
            self.assertIn("synthetic failure", stderr_path.read_text(encoding="utf-8"))

    def test_command_runner_format_errors_raise_invocation_error(self):
        invalid_templates = [
            "fake-agent {}",
            "fake-agent {output_path.name}",
        ]

        for command_template in invalid_templates:
            with self.subTest(command_template=command_template):
                runner = CommandRunner(
                    vault_root=FIXTURE_VAULT,
                    command_template=command_template,
                    timeout_seconds=10,
                )
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)

                    with self.assertRaisesRegex(RunnerInvocationError, "invalid command template"):
                        runner.run(
                            "prompt",
                            output_path=tmp_path / "last-message.jsonl",
                            stdout_path=tmp_path / "stdout.log",
                            stderr_path=tmp_path / "stderr.log",
                        )

    def test_collect_model_judgments_with_command_runner_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = tmp_path / "fake_agent.py"
            script.write_text(
                "import json\n"
                "import re\n"
                "import sys\n"
                "prompt = sys.stdin.read()\n"
                "for note_path in re.findall(r'Use this exact `note_path`: `([^`]+)`\\.', prompt):\n"
                "    print(json.dumps({\n"
                "        'schema_version': '1.0.0',\n"
                "        'note_path': note_path,\n"
                "        'dimension_adjustments': {},\n"
                "        'findings': [],\n"
                "        'factual_risk': False,\n"
                "        'factual_risk_reason': None,\n"
                "        'fact_check_required': False,\n"
                "        'evidence': [],\n"
                "    }, sort_keys=True))\n",
                encoding="utf-8",
            )
            command = " ".join(shlex.quote(part) for part in [sys.executable, str(script)])
            runner = CommandRunner(
                vault_root=FIXTURE_VAULT,
                command_template=command,
                timeout_seconds=10,
            )
            output = tmp_path / "model-judgments.jsonl"

            with redirect_stdout(io.StringIO()):
                count = collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=2,
                    max_chars=100_000,
                    limit=2,
                    runner=runner,
                )

            self.assertEqual(count, 2)
            self.assertEqual(len(output.read_text(encoding="utf-8").splitlines()), 2)
            self.assertTrue((tmp_path / "raw" / "batch-00001-stdout.log").exists())

    def test_command_runner_output_path_placeholder_survives_relative_raw_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = tmp_path / "write_output.py"
            script.write_text(
                "import json\n"
                "import re\n"
                "import sys\n"
                "output = sys.argv[1]\n"
                "prompt = sys.stdin.read()\n"
                "with open(output, 'w', encoding='utf-8') as handle:\n"
                "    for note_path in re.findall(r'Use this exact `note_path`: `([^`]+)`\\.', prompt):\n"
                "        print(json.dumps({\n"
                "            'schema_version': '1.0.0',\n"
                "            'note_path': note_path,\n"
                "            'dimension_adjustments': {},\n"
                "            'findings': [],\n"
                "            'factual_risk': False,\n"
                "            'factual_risk_reason': None,\n"
                "            'fact_check_required': False,\n"
                "            'evidence': [],\n"
                "        }, sort_keys=True), file=handle)\n",
                encoding="utf-8",
            )
            command = " ".join(
                shlex.quote(part)
                for part in [sys.executable, str(script), "{output_path}"]
            )
            runner = CommandRunner(
                vault_root=FIXTURE_VAULT,
                command_template=command,
                timeout_seconds=10,
            )
            output = tmp_path / "model-judgments.jsonl"
            original_cwd = Path.cwd()

            try:
                os.chdir(tmp_path)
                with redirect_stdout(io.StringIO()):
                    count = collect_model_judgments(
                        vault_root=FIXTURE_VAULT,
                        audit_jsonl=AUDIT_JSONL,
                        output_jsonl=output,
                        raw_dir=Path("relative-raw"),
                        max_notes=1,
                        max_chars=100_000,
                        limit=1,
                        runner=runner,
                    )
            finally:
                os.chdir(original_cwd)

            self.assertEqual(count, 1)
            self.assertTrue((tmp_path / "relative-raw" / "batch-00001-last-message.jsonl").exists())

    def test_parse_model_output_accepts_jsonl_json_array_and_fence(self):
        rows = load_fixture_rows()
        judgments = [judgment_for(str(row["note_path"])) for row in rows[:2]]

        self.assertEqual(parse_model_output(jsonl_for(judgments)), judgments)
        self.assertEqual(parse_model_output(json.dumps(judgments)), judgments)
        self.assertEqual(parse_model_output(f"```jsonl\n{jsonl_for(judgments)}```"), judgments)

    def test_parse_model_output_rejects_non_object_line(self):
        with self.assertRaises(ValidationError):
            parse_model_output("[1]\n")

    def test_render_batch_prompt_contains_exact_note_paths_and_jsonl_instruction(self):
        rows = load_fixture_rows()[:2]

        prompt = render_batch_prompt(FIXTURE_VAULT, rows)

        self.assertIn("Return strict JSONL only", prompt)
        self.assertIn(str(rows[0]["note_path"]), prompt)
        self.assertIn(str(rows[1]["content_hash"]), prompt)
        self.assertIn("NOTE_CONTENT_START", prompt)

    def test_collect_model_judgments_writes_valid_output(self):
        rows = load_fixture_rows()[:3]
        judgments = [judgment_for(str(row["note_path"])) for row in rows]
        runner = FakeRunner([jsonl_for(judgments)])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            with redirect_stdout(io.StringIO()):
                count = collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=3,
                    max_chars=100_000,
                    limit=3,
                    runner=runner,
                )

            self.assertEqual(count, 3)
            stored = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(stored), 3)
            self.assertEqual(
                [judgment["prompt_version"] for judgment in stored],
                [PROMPT_VERSION] * len(rows),
            )
            self.assertEqual(len(runner.prompts), 1)

    def test_collect_model_judgments_rejects_stale_audit_before_runner_invocation(self):
        row = load_fixture_rows()[0]
        row["prompt_version"] = "1.0.0"
        runner = FakeRunner([])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audit_jsonl = tmp_path / "stale-audit.jsonl"
            audit_jsonl.write_text(jsonl_for([row]), encoding="utf-8")

            with self.assertRaisesRegex(
                ValidationError,
                "rerun the deterministic audit before collecting model judgments",
            ):
                collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=audit_jsonl,
                    output_jsonl=tmp_path / "model-judgments.jsonl",
                    raw_dir=tmp_path / "raw",
                    max_notes=1,
                    max_chars=100_000,
                    runner=runner,
                )

            self.assertEqual(runner.prompts, [])

    def test_collect_model_judgments_resumes_existing_output(self):
        rows = load_fixture_rows()[:3]
        completed = stored_judgment_for(
            str(rows[0]["note_path"]),
            prompt_version=str(rows[0]["prompt_version"]),
        )
        remaining = [judgment_for(str(row["note_path"])) for row in rows[1:]]
        runner = FakeRunner([jsonl_for(remaining)])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            output.write_text(jsonl_for([completed]), encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                count = collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=3,
                    max_chars=100_000,
                    limit=3,
                    runner=runner,
                )

            self.assertEqual(count, 3)
            self.assertNotIn(str(rows[0]["note_path"]), runner.prompts[0])

    def test_collect_model_judgments_rejects_stale_resumed_prompt_version(self):
        row = load_fixture_rows()[0]
        runner = FakeRunner([])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            output.write_text(
                jsonl_for([stored_judgment_for(str(row["note_path"]), prompt_version="1.0.0")]),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValidationError, "prompt_version mismatch"):
                collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=1,
                    max_chars=100_000,
                    limit=1,
                    runner=runner,
                )

    def test_collect_model_judgments_rejects_resumed_judgment_without_prompt_version(self):
        row = load_fixture_rows()[0]
        runner = FakeRunner([])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            output.write_text(jsonl_for([judgment_for(str(row["note_path"]))]), encoding="utf-8")

            with self.assertRaisesRegex(ValidationError, "missing required keys: prompt_version"):
                collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=1,
                    max_chars=100_000,
                    limit=1,
                    runner=runner,
                )

    def test_collect_model_judgments_splits_and_retries_invalid_batch(self):
        rows = load_fixture_rows()[:2]
        bad_batch = jsonl_for(
            [
                judgment_for("Atomic Notes/Wrong.md"),
                judgment_for(str(rows[1]["note_path"])),
            ]
        )
        first = jsonl_for([judgment_for(str(rows[0]["note_path"]))])
        second = jsonl_for([judgment_for(str(rows[1]["note_path"]))])
        runner = FakeRunner([bad_batch, first, second])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            with redirect_stdout(io.StringIO()):
                count = collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=2,
                    max_chars=100_000,
                    limit=2,
                    runner=runner,
                )

            self.assertEqual(count, 2)
            self.assertEqual(len(runner.prompts), 3)

    def test_collect_model_judgments_does_not_split_programmer_errors(self):
        runner = BrokenRunner()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"

            with self.assertRaises(AssertionError):
                collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=2,
                    max_chars=100_000,
                    limit=2,
                    runner=runner,
                )

            self.assertEqual(len(runner.prompts), 1)

    def test_collect_model_judgments_does_not_split_os_errors(self):
        runner = OSErrorRunner()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"

            with self.assertRaises(OSError):
                collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=2,
                    max_chars=100_000,
                    limit=2,
                    runner=runner,
                )

            self.assertEqual(len(runner.prompts), 1)

    def test_collect_model_judgments_does_not_split_runner_invocation_errors(self):
        runner = InvocationFailureRunner()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"

            with self.assertRaises(RunnerInvocationError):
                collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=2,
                    max_chars=100_000,
                    limit=2,
                    runner=runner,
                )

            self.assertEqual(len(runner.prompts), 1)

    def test_duplicate_existing_judgment_fails(self):
        rows = load_fixture_rows()[:1]
        duplicate = stored_judgment_for(
            str(rows[0]["note_path"]),
            prompt_version=str(rows[0]["prompt_version"]),
        )
        runner = FakeRunner([])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            output.write_text(jsonl_for([duplicate, duplicate]), encoding="utf-8")

            with self.assertRaises(ValidationError):
                collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=1,
                    max_chars=100_000,
                    limit=1,
                    runner=runner,
                )

    def test_existing_judgment_outside_selected_rows_fails(self):
        rows = load_fixture_rows()[:2]
        outside_selected_rows = stored_judgment_for(
            str(rows[1]["note_path"]),
            prompt_version=str(rows[1]["prompt_version"]),
        )
        runner = FakeRunner([])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            output.write_text(jsonl_for([outside_selected_rows]), encoding="utf-8")

            with self.assertRaises(ValidationError):
                collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=1,
                    max_chars=100_000,
                    limit=1,
                    runner=runner,
                )


if __name__ == "__main__":
    unittest.main()
