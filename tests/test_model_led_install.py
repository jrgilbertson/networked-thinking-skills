import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ModelLedInstallTest(unittest.TestCase):
    def test_standalone_default_cli_pipeline_without_repository_imports(self):
        with tempfile.TemporaryDirectory() as d:
            temp = Path(d)
            skill = temp / 'standalone skill'
            shutil.copytree(ROOT / 'skills' / 'atomic-note-audit', skill, ignore=shutil.ignore_patterns('__pycache__'))
            vault = temp / 'synthetic vault'
            shutil.copytree(ROOT / 'tests' / 'fixtures' / 'tiny-vault', vault)
            evidence, raw = temp / 'evidence', temp / 'raw'
            fake = temp / 'synthetic_runner.py'
            fake.write_text('''import json,re,sys
prompt=sys.stdin.read()
for path in re.findall(r'Use this exact `note_path`: `([^`]+)`',prompt):
 print(json.dumps(dict(schema_version="1.0.0",note_path=path,dimension_adjustments={},findings=[],factual_risk=False,factual_risk_reason=None,fact_check_required=False,evidence=[])))
''')
            environment = dict(os.environ, PYTHONPATH='', PYTHONDONTWRITEBYTECODE='1')
            def run(script, *args):
                result = subprocess.run([sys.executable, str(skill / 'scripts' / script), *map(str, args)], cwd=temp,
                    env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result
            run('audit_inventory.py', '--vault', vault, '--run-id', 'synthetic-installed', '--evidence-dir', evidence)
            captured = [json.loads(line) for line in (evidence / 'inventory.jsonl').read_text().splitlines()]
            self.assertEqual(len(captured), 13)
            self.assertTrue(all('score' not in row for row in captured))
            run('collect_model_judgments.py', '--runner', 'command', '--command', shlex.join([sys.executable, str(fake)]),
                '--model-identity', 'synthetic-model', '--vault', vault, '--inventory-jsonl', evidence / 'inventory.jsonl',
                '--output-jsonl', evidence / 'judgments.jsonl', '--raw-dir', raw)
            run('apply_model_judgments.py', '--vault', vault, '--inventory-jsonl', evidence / 'inventory.jsonl',
                '--model-judgments', evidence / 'judgments.jsonl', '--output-jsonl', evidence / 'results.jsonl',
                '--output-manifest', evidence / 'manifest.json')
            run('validate_jsonl.py', evidence / 'results.jsonl')
            report = vault / 'Reviews' / 'Synthetic run' / 'Audit.md'
            run('generate_report.py', '--jsonl', evidence / 'results.jsonl', '--manifest', evidence / 'manifest.json', '--output', report)
            manifest = json.loads((evidence / 'manifest.json').read_text())
            self.assertEqual(manifest['model_coverage']['reviewed'], 13)
            self.assertEqual([p.name for p in report.parent.iterdir()], ['Audit.md'])
            self.assertLess(report.read_text().index('## Recommendation'), report.read_text().index('## Coverage'))
            self.assertFalse(evidence.resolve().is_relative_to(vault.resolve()))
