import json
from copy import deepcopy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from shared.scripts.audit_inventory import inventory_vault
from shared.scripts.collect_model_judgments import collect_model_judgments
from shared.scripts.apply_model_judgments import compose_inventory
from shared.scripts.reporting import render_markdown_report
from shared.scripts.base_generation import render_base
from shared.scripts.audit_review_report import ReviewError, parse_report, note_target


class ReportRunner:
    def run(self, prompt, *, output_path, stdout_path, stderr_path):
        import re
        output = []
        for path in re.findall(r'Use this exact `note_path`: `([^`]+)`', prompt):
            number = int(Path(path).stem.split()[-1])
            code = 'multi_note' if number < 2 else ('not_atomic' if number < 4 else ('title_body_mismatch' if number == 4 else None))
            output.append(dict(schema_version='1.0.0', note_path=path, dimension_adjustments={},
                findings=[dict(code=code, message='This synthetic note needs a focused change.')] if code else [],
                factual_risk=False, factual_risk_reason=None, fact_check_required=False, evidence=[]))
        output_path.write_text('\n'.join(json.dumps(j) for j in output))


class ModelLedReportingTest(unittest.TestCase):
    def fixture(self, directory, *, limit=None, count=100):
        root = directory / 'vault'
        (root / 'Atomic Notes').mkdir(parents=True)
        for i in range(count):
            (root / 'Atomic Notes' / f'Note {i:03}.md').write_text(f'---\ntitle: Idea {i}\n---\n# Idea {i}\n\nSynthetic content.')
        inventory = inventory_vault(root, run_id='synthetic-report', parent_targets={f'Note {i:03}' for i in range(count)})
        if inventory:
            inventory[0]['integrity_checks'].append(dict(code='missing_anki_target', source='anki',
                status='failed', priority='P1', message='Repair the stale card link.'))
        evidence = directory / 'evidence'
        evidence.mkdir()
        source = evidence / 'inventory.jsonl'
        source.write_text(''.join(json.dumps(r) + '\n' for r in inventory))
        judgments = evidence / 'judgments.jsonl'
        collect_model_judgments(vault_root=root, inventory_jsonl=source, output_jsonl=judgments,
            raw_dir=evidence / 'raw', max_notes=100, max_chars=100000, runner=ReportRunner(), limit=limit)
        rows, manifest = compose_inventory(inventory, [json.loads(line) for line in judgments.read_text().splitlines()],
            vault_root=root, outputs={'evidence': str(evidence)})
        return root, rows, manifest, evidence

    def test_plain_markdown_recommends_first_and_lists_each_action_note_once(self):
        with tempfile.TemporaryDirectory() as d:
            root, rows, manifest, evidence = self.fixture(Path(d))
            report = render_markdown_report(rows, manifest)
            self.assertLess(report.index('## Recommendation'), report.index('## Coverage'))
            self.assertLess(report.index('## Coverage'), report.index('| # | Priority |'))
            recommendation = report.split('## Recommendation')[1].split('## Coverage')[0]
            self.assertIn('Repair the stale card link.', recommendation)
            self.assertIn('Split bundled ideas', recommendation)
            self.assertIn('100 / 100 model-reviewed', report)
            self.assertIn('5 need action', report)
            self.assertIn('95 need no changes', report)
            parsed = parse_report(report)
            self.assertEqual([i.priority for i in parsed.items], ['P1', 'P1', 'P2', 'P2', 'P3'])
            self.assertEqual([i.number for i in parsed.items], [1, 2, 3, 4, 5])
            self.assertEqual([note_target(i.note) for i in parsed.items].count('Atomic Notes/Note 000.md'), 1)
            self.assertIn('Repair the stale card link.', report)
            self.assertIn('Anki integrity', report)
            self.assertIn('Supporting evidence', report)
            self.assertNotIn('![', report)
            self.assertEqual(report.count('| # | Priority | Note | Recommendation | Action taken |'), 1)
            self.assertNotIn('## P1', report)
            self.assertNotIn('## No Changes', report)
            golden = Path(__file__).parent / 'golden' / 'fixture-model-led-report.md'
            self.assertEqual(report.replace(evidence.resolve().as_uri(), 'evidence/'), golden.read_text())

    def test_partial_coverage_and_pending_base_are_honest(self):
        with tempfile.TemporaryDirectory() as d:
            _, rows, manifest, evidence = self.fixture(Path(d), limit=24)
            report = render_markdown_report(rows, manifest)
            self.assertIn('24 / 100 model-reviewed', report)
            self.assertIn('76 pending', report)
            self.assertIn('19 need no changes', report)
            path = evidence / 'results.jsonl'
            path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            base = render_base(str(path))
            no_changes = base.split('name: "No Changes"')[1].split('  - type:')[0]
            self.assertNotIn('Note 099.md', no_changes)
            self.assertIn('name: "Unreviewed"', base)

    def test_regeneration_recovers_ids_and_keeps_source_revisions_pending(self):
        with tempfile.TemporaryDirectory() as d:
            _, rows, manifest, _ = self.fixture(Path(d), count=5)
            first = render_markdown_report(rows, manifest)
            mapping = {note_target(i.note): i.number for i in parse_report(first).items}
            rows.reverse()
            rows[0]['priority'] = 'P0'
            revised = render_markdown_report(rows, manifest, existing_report=first)
            self.assertEqual({note_target(i.note): i.number for i in parse_report(revised).items}, mapping)
            self.assertEqual(parse_report(revised).items[0].priority, 'P0')
            rows[0]['content_hash'] = 'revised-source'
            newer = parse_report(render_markdown_report(rows, manifest, existing_report=revised))
            self.assertEqual(len(newer.items[0].actions), 2)
            self.assertTrue(all(o.text == '**Pending**' for o in newer.items[0].outcomes))

    def test_regeneration_stops_before_discarding_edited_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            _, rows, manifest, _ = self.fixture(Path(d), count=2, limit=1)
            rows[0]['fact_check_required'] = True
            original = render_markdown_report(rows, manifest)
            for prefix in ('1 / 2 model-reviewed.', 'Unfinished:', 'Fact-checks pending:', 'Anki:'):
                line = next(line for line in original.splitlines() if line.startswith(prefix))
                edited = original.replace(line, line + ' Learner annotation: preserve this context.')
                with self.subTest(prefix=prefix), self.assertRaisesRegex(ReviewError, 'Coverage.*edited'):
                    render_markdown_report(rows, manifest, existing_report=edited)
            annotated = original.replace('## Coverage\n\n', '## Coverage\n\nA learner observation.\n')
            self.assertIn('A learner observation.', render_markdown_report(rows, manifest, existing_report=annotated))

    def test_special_character_paths_and_math_recommendations_keep_their_content(self):
        with tempfile.TemporaryDirectory() as d:
            _, rows, manifest, _ = self.fixture(Path(d), count=1)
            rows[0]['note_path'] = 'Atomic Notes/λ [example]|math.md'
            rows[0]['findings'][0]['message'] = r'Use $\theta$ with a|b and λ.'
            text = render_markdown_report(rows, manifest)
            item = parse_report(text).items[0]
            self.assertEqual(note_target(item.note), rows[0]['note_path'])
            self.assertIn(r'$\theta$', text)
            self.assertIn(r'a\|b', text)

    def test_large_report_and_zero_action_report_preserve_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            _, rows, manifest, _ = self.fixture(Path(d), count=1)
            large = []
            for n in range(2000):
                row = deepcopy(rows[0])
                row['note_path'] = f'Atomic Notes/Synthetic {n}.md'
                large.append(row)
            manifest['total_notes'] = manifest['model_coverage']['reviewed'] = 2000
            report = parse_report(render_markdown_report(large, manifest))
            self.assertEqual(len(report.items), 2000)
            self.assertEqual(len({i.number for i in report.items}), 2000)
            self.assertTrue(all(len(i.actions) == 2 for i in report.items))
            rows[0].update(priority=None, clean=True, findings=[], integrity_checks=[])
            manifest['total_notes'] = manifest['model_coverage']['reviewed'] = 1
            empty = render_markdown_report(rows, manifest)
            self.assertEqual(parse_report(empty).items, [])
            self.assertIn('1 need no changes', empty)

    def test_held_decision_stays_held_without_claiming_a_fix(self):
        with tempfile.TemporaryDirectory() as d:
            _, rows, manifest, _ = self.fixture(Path(d), count=1)
            manifest['decisions'] = [dict(note_path=rows[0]['note_path'], status='held', message='Learner will review the card later.')]
            report = render_markdown_report(rows, manifest)
            self.assertIn('Held', report)
            self.assertIn('Learner will review the card later.', report)
            self.assertNotIn('Completed:', report)

    def test_generate_cli_publishes_only_one_report_and_resolves_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root, rows, manifest, evidence = self.fixture(Path(d), count=5)
            row_path, manifest_path = evidence / 'results.jsonl', evidence / 'manifest.json'
            row_path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            manifest_path.write_text(json.dumps(manifest))
            output = root / 'Reviews' / 'Synthetic run' / 'Audit.md'
            result = subprocess.run([sys.executable, '-m', 'shared.scripts.generate_report', '--jsonl', str(row_path), '--manifest', str(manifest_path), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([p.name for p in output.parent.iterdir()], ['Audit.md'])
            self.assertIn(evidence.resolve().as_uri(), output.read_text())
