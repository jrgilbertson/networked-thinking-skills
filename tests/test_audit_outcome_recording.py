import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from shared.scripts.audit_review_report import ReviewError, parse_report
from shared.scripts.record_audit_outcome import prepare_outcome
from test_audit_review_report import REPORT


def event(**changes):
    value = dict(run_id='synthetic', item=7, action_id='example', event_id='repair-example',
                 status='Completed', timestamp='2030-01-02T03:04:00+00:00',
                 description='Corrected the example and checked its value.', actor='Learner-approved agent',
                 approval_ref='Learner approved the example repair.',
                 verification={
                     'source': {'status': 'passed', 'detail': 'Read back the corrected example; source hash verified.'},
                     'links': {'status': 'passed', 'detail': 'Parent and note targets resolve.'},
                     'anki': {'status': 'not_applicable', 'detail': 'This action changes no card or identifiers.'}})
    value.update(changes)
    return value


class OutcomeRecordingTest(unittest.TestCase):
    def test_completion_keeps_other_actions_and_history_visible_and_is_idempotent(self):
        revised = prepare_outcome(REPORT, event())
        self.assertIn('Corrected the example', revised)
        self.assertIn('source passed', revised)
        self.assertIn('anki not_applicable', revised)
        self.assertIn('Learner prefers this name.', revised)
        self.assertEqual(prepare_outcome(revised, event()), revised)
        item = parse_report(revised).items[0]
        self.assertEqual([o.action_id for o in item.outcomes], ['example', 'rename', 'example'])

    def test_approval_or_failed_checks_cannot_become_completion(self):
        cases = [dict(verification={}), dict(approval_ref=''),
                 dict(remaining_checks=['Verify the card after scan.']),
                 dict(timestamp='2030-01-02T03:04:00')]
        for name in ('source', 'links', 'anki'):
            for status in ('failed', 'not_checked'):
                verification = event()['verification']
                verification[name] = dict(status=status, detail='This check has not passed.')
                cases.append(dict(verification=verification))
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ReviewError):
                prepare_outcome(REPORT, event(**changes))

    def test_partial_work_requires_remaining_checks_and_keeps_them_visible(self):
        with self.assertRaises(ReviewError):
            prepare_outcome(REPORT, event(status='Partial'))
        result = prepare_outcome(REPORT, event(status='Partial', remaining_checks=['Verify the card after scan.']))
        self.assertIn('**Partial', result)
        self.assertIn('Remaining: Verify the card after scan.', result)

    def test_decline_needs_no_mutation_or_completion_evidence(self):
        result = prepare_outcome(REPORT, event(status='Declined', verification={}, approval_ref='',
                                               description='Learner prefers the current example.'))
        self.assertIn('**Declined — 2030', result)
        self.assertNotIn('**Completed', result)

    def test_bad_identity_or_event_reuse_preserves_input(self):
        for changes in [dict(run_id='other'), dict(item=99), dict(action_id='missing'), dict(event_id='bad -->')]:
            with self.subTest(changes=changes), self.assertRaises(ReviewError):
                prepare_outcome(REPORT, event(**changes))
        once = prepare_outcome(REPORT, event())
        with self.assertRaisesRegex(ReviewError, 'reused'):
            prepare_outcome(once, event(description='Different result.'))

    def test_approved_rename_updates_report_target_and_preserves_item_identity(self):
        renamed = event(rename_to='Atomic Notes/Renamed.md', previous_path='Atomic Notes/Example|math.md')
        result = prepare_outcome(REPORT, renamed)
        self.assertIn('Recorded rename:', result)
        self.assertIn('Atomic Notes/Renamed.md', result)
        self.assertEqual(parse_report(result).items[0].identity, 'original')
        self.assertEqual(prepare_outcome(result, renamed), result)
        with self.assertRaises(ReviewError):
            prepare_outcome(REPORT, event(rename_to='Atomic Notes/Renamed.md'))

    def test_snapshot_only_cli_needs_no_audit_artifacts_and_leaves_input_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source, data, draft = root/'report.md', root/'event.json', root/'draft.md'
            source.write_text(REPORT)
            data.write_text(json.dumps(event(status='Held', verification={}, description='Waiting for a learner decision.')))
            result = subprocess.run([sys.executable, '-m', 'shared.scripts.record_audit_outcome',
                '--report-snapshot', str(source), '--event', str(data), '--draft', str(draft)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(source.read_text(), REPORT)
            self.assertIn('Waiting for a learner decision.', draft.read_text())
            self.assertEqual(set(p.name for p in root.iterdir()), {'report.md', 'event.json', 'draft.md'})
