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
            vault = temp / 'note fixture'
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
            report = temp / 'draft.md'
            run('generate_report.py', '--jsonl', evidence / 'results.jsonl', '--manifest', evidence / 'manifest.json', '--output', report)
            manifest = json.loads((evidence / 'manifest.json').read_text())
            self.assertEqual(manifest['model_coverage']['reviewed'], 13)
            self.assertLess(report.read_text().index('## Recommendation'), report.read_text().index('## Coverage'))
            self.assertFalse(evidence.resolve().is_relative_to(vault.resolve()))
            self.assertTrue((skill/'references/audit-review-record.md').is_file())
            self.assertIn('| # | Priority | Note | Recommendation | Action taken |', report.read_text())
            before = {p.relative_to(vault).as_posix():p.read_text() for p in vault.rglob('*.md')}
            first = report.read_text()
            import re
            item_number = int(re.search(r'\| ([0-9]+) <!-- item:', first)[1])
            action_id = re.search(r'<!-- action:([^ ]+) -->', first)[1]
            event = temp/'event.json'
            event.write_text(json.dumps(dict(run_id='synthetic-installed', item=item_number, action_id=action_id,
                event_id='learner-decline', status='Declined', timestamp='2030-01-02T03:04:00+00:00',
                description='Learner chooses to retain this wording.', actor='Learner')))
            shutil.rmtree(evidence)
            shutil.rmtree(raw)
            snapshot = temp/'snapshot.md'
            snapshot.write_text(first)
            resumed = temp/'resumed.md'
            run('record_audit_outcome.py', '--report-snapshot', snapshot, '--event', event, '--draft', resumed)
            self.assertIn('Learner chooses to retain this wording.', resumed.read_text())
            self.assertEqual(resumed.read_text().count('outcome:learner-decline '), 1)
            if shutil.which('node'):
                from test_audit_report_publication import NODE_APP
                state = temp/'simulated-app.json'
                state.write_text(json.dumps(before))
                binary = temp/'simulated-obsidian'
                binary.write_text(f'''#!{sys.executable}
import json,subprocess,sys
from pathlib import Path
state=Path({str(state)!r})
code=next(arg[5:] for arg in sys.argv if arg.startswith('code='))
result=subprocess.run(['node','-e',{NODE_APP!r}],input=json.dumps(dict(code=code,files=json.loads(state.read_text()))),capture_output=True,text=True)
value=json.loads(result.stdout)
state.write_text(json.dumps(value['files']))
print(value.get('stdout',''))
print(value.get('stderr',''),file=sys.stderr)
sys.exit(0 if value['ok'] else 1)
''')
                binary.chmod(0o755)
                receipt = run('publish_audit_report.py', '--vault', 'Simulated app only', '--draft', report,
                    '--timestamp', '203001020304', '--obsidian-binary', binary)
                path = json.loads(receipt.stdout)['path']
                self.assertEqual(path, 'Reviews/Atomic Note Audits/203001020304 Atomic note audit.md')
                run('publish_audit_report.py', '--vault', 'Simulated app only', '--draft', resumed,
                    '--report-path', path, '--expected-snapshot', snapshot, '--obsidian-binary', binary)
                stored = json.loads(state.read_text())
                self.assertEqual(stored[path], resumed.read_text())
                self.assertEqual({p:v for p,v in stored.items() if p != path}, before)
                self.assertEqual(set(stored)-set(before), {path})
            self.assertEqual({p.relative_to(vault).as_posix():p.read_text() for p in vault.rglob('*.md')}, before)
