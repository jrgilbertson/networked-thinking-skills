import json
import tempfile
import unittest
from pathlib import Path

from shared.scripts.audit_inventory import inventory_vault
from shared.scripts.collect_model_judgments import collect_model_judgments, RunnerInvocationError
from shared.scripts.apply_model_judgments import compose_inventory
from shared.scripts.schema_validation import ValidationError, validate_audit_run_pair


class SyntheticRunner:
    def __init__(self, *, broken=False, split=False):
        self.calls = 0
        self.broken = broken
        self.split = split

    def run(self, prompt, *, output_path, stdout_path, stderr_path):
        import re
        self.calls += 1
        if self.broken:
            raise RunnerInvocationError('synthetic runner unavailable')
        paths = re.findall(r'Use this exact `note_path`: `([^`]+)`', prompt)
        if self.split and len(paths) > 1:
            output_path.write_text('invalid JSON')
            return
        output_path.write_text('\n'.join(json.dumps(dict(schema_version='1.0.0', note_path=p, dimension_adjustments={}, findings=[], factual_risk=False, factual_risk_reason=None, fact_check_required=False, evidence=[])) for p in paths))


class ModelLedWorkflowTest(unittest.TestCase):
    def setup_run(self, d, count=3):
        root = Path(d) / 'vault'
        (root / 'Atomic Notes').mkdir(parents=True)
        for i in range(count):
            (root / 'Atomic Notes' / f'Note {i}.md').write_text(f'---\ntitle: Example {i}\n---\n# Example {i}\n\nSynthetic idea.')
        rows = inventory_vault(root, run_id='synthetic')
        inventory = Path(d) / 'inventory.jsonl'
        inventory.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        return root, rows, inventory, Path(d) / 'judgments.jsonl'

    def collect(self, root, inventory, output, runner, **kwargs):
        return collect_model_judgments(vault_root=root, inventory_jsonl=inventory, output_jsonl=output,
            raw_dir=output.parent / 'raw', max_notes=20, max_chars=50000, runner=runner, **kwargs)

    def test_partial_scope_stays_unscored_and_resume_is_bound(self):
        with tempfile.TemporaryDirectory() as d:
            root, inventory, path, output = self.setup_run(d)
            runner = SyntheticRunner()
            self.collect(root, path, output, runner, limit=1, model_identity='synthetic-model')
            judgments = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(judgments[0]['schema_version'], '3.0.0')
            rows, manifest = compose_inventory(inventory, judgments, vault_root=root)
            self.assertEqual(manifest['model_coverage']['reviewed'], 1)
            self.assertEqual(manifest['model_coverage']['pending'], 2)
            self.assertTrue(all(row['score'] is None and not row['clean'] for row in rows[1:]))
            self.collect(root, path, output, runner, model_identity='synthetic-model')
            self.assertEqual(runner.calls, 2)
            self.collect(root, path, output, runner, model_identity='synthetic-model')
            self.assertEqual(runner.calls, 2)

    def test_changed_source_is_stale_at_composition(self):
        with tempfile.TemporaryDirectory() as d:
            root, inventory, path, output = self.setup_run(d, 1)
            self.collect(root, path, output, SyntheticRunner(), model_identity='synthetic-model')
            (root / inventory[0]['note_path']).write_text('Changed content.')
            rows, manifest = compose_inventory(inventory, [json.loads(output.read_text())], vault_root=root)
            self.assertEqual(rows[0]['review_status'], 'stale')
            self.assertIsNone(rows[0]['score'])
            self.assertEqual(manifest['model_coverage']['stale'], 1)

    def test_unknown_identity_has_no_cross_run_cache_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            root, inventory, path, output = self.setup_run(d, 1)
            runner = SyntheticRunner()
            self.collect(root, path, output, runner)
            inventory[0]['run_id'] = 'new-synthetic-run'
            path.write_text(json.dumps(inventory[0]) + '\n')
            self.collect(root, path, output, runner)
            self.assertEqual(runner.calls, 2)

    def test_failed_invocation_does_not_split_and_is_visible(self):
        with tempfile.TemporaryDirectory() as d:
            root, inventory, path, output = self.setup_run(d)
            runner = SyntheticRunner(broken=True)
            with self.assertRaises(RunnerInvocationError):
                self.collect(root, path, output, runner)
            self.assertEqual(runner.calls, 1)
            status = json.loads(output.with_suffix('.status.json').read_text())
            rows, manifest = compose_inventory(inventory, [], vault_root=root, collection_status=status)
            self.assertEqual(manifest['model_coverage']['failed'], 3)
            self.assertTrue(all(row['score'] is None for row in rows))

    def test_invalid_batch_splits_and_persists_validated_results(self):
        with tempfile.TemporaryDirectory() as d:
            root, inventory, path, output = self.setup_run(d, 2)
            runner = SyntheticRunner(split=True)
            self.collect(root, path, output, runner)
            self.assertEqual(runner.calls, 3)
            rows, manifest = compose_inventory(inventory, [json.loads(line) for line in output.read_text().splitlines()], vault_root=root)
            validate_audit_run_pair(rows, manifest)
            self.assertEqual(manifest['model_coverage']['reviewed'], 2)

    def test_inventory_mode_rejects_scored_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            root, rows, path, output = self.setup_run(d, 1)
            path.write_text(json.dumps({'schema_version': '1.0.0', 'score': 100}) + '\n')
            with self.assertRaisesRegex(ValidationError, 'inventory'):
                self.collect(root, path, output, SyntheticRunner())

    def test_changed_model_invalidates_completed_stream(self):
        with tempfile.TemporaryDirectory() as d:
            root, inventory, path, output = self.setup_run(d, 1)
            runner = SyntheticRunner()
            self.collect(root, path, output, runner, model_identity='synthetic-model-a')
            self.collect(root, path, output, runner, model_identity='synthetic-model-b')
            self.assertEqual(runner.calls, 2)

    def test_quality_is_separate_from_exact_failures(self):
        with tempfile.TemporaryDirectory() as d:
            root, inventory, path, output = self.setup_run(d, 1)
            self.collect(root, path, output, SyntheticRunner())
            rows, manifest = compose_inventory(inventory, [json.loads(output.read_text())], vault_root=root)
            self.assertEqual(rows[0]['score'], 100)
            self.assertTrue(rows[0]['clean'])
            self.assertEqual(rows[0]['priority'], 'P2')  # Missing parent, independently checked.
            self.assertTrue(any(c['source'] == 'anki' and c['status'] == 'not_checked' for c in rows[0]['integrity_checks']))
            manifest['model_coverage']['pending'] += 1
            with self.assertRaises(ValidationError):
                validate_audit_run_pair(rows, manifest)
