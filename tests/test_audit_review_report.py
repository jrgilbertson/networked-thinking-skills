import unittest

from shared.scripts.audit_review_report import (
    ReviewError, add_item, parse_report, render_report, new_report, note_target,
)


REPORT = '''# Atomic note audit
<!-- atomic-note-audit:1.0.0 run=synthetic scope=selected%3Aone -->

Review the example. Learner context stays here.

| # | Priority | Note | Recommendation | Action taken |
|---|---|---|---|---|
| 7 <!-- item:original --> | P1 | [Example](<Atomic%20Notes/Example%7Cmath.md>) | <!-- action:example -->Fix $\\theta$ and `a\\|b`.<br><!-- action:rename -->Consider a new name. | <!-- outcome:pending-example action:example -->**Pending**<br><!-- outcome:decline-name action:rename -->**Declined — 2030-01-02T03:04:00+00:00** Learner prefers this name. |

My follow-up observation must survive.
'''


class ReviewReportTest(unittest.TestCase):
    def test_report_alone_recovers_mixed_actions_and_preserves_all_text(self):
        report = parse_report(REPORT, run_id='synthetic', scope='selected:one')
        item = report.items[0]
        self.assertEqual(item.number, 7)
        self.assertEqual(item.actions[0].text, r'Fix $\theta$ and `a\|b`.')
        self.assertEqual([o.action_id for o in item.outcomes], ['example', 'rename'])
        self.assertIn('Declined', item.outcomes[1].text)
        self.assertEqual(note_target(item.note), 'Atomic Notes/Example|math.md')
        self.assertEqual(render_report(report), REPORT)

    def test_reordered_items_and_new_items_keep_old_numbers_reserved(self):
        report = parse_report(REPORT)
        add_item(report, 'Atomic Notes/New.md', 'P0', [('repair', 'Repair it.')])
        self.assertEqual([i.number for i in report.items], [7, 8])
        report.items.reverse()
        recovered = parse_report(render_report(report))
        self.assertEqual([i.number for i in recovered.items], [8, 7])
        add_item(recovered, 'Atomic Notes/Third.md', 'P2', [('clarify', 'Clarify it.')])
        self.assertEqual(recovered.items[-1].number, 9)
        self.assertIn('decline-name', render_report(recovered))

    def test_rename_keeps_identity_and_old_history(self):
        report = parse_report(REPORT)
        report.items[0].note = '[Renamed](<Atomic%20Notes/Renamed.md>)'
        recovered = parse_report(render_report(report))
        self.assertEqual(recovered.items[0].number, 7)
        self.assertEqual(recovered.items[0].identity, 'original')
        self.assertIn('Learner prefers this name.', recovered.items[0].outcomes[1].text)

    def test_source_revision_adds_pending_action_without_closing_it_from_history(self):
        report = parse_report(REPORT)
        add_item(report, 'Atomic Notes/Example|math.md', 'P1', [('new-source', 'Verify the revised example.')])
        item = parse_report(render_report(report)).items[0]
        self.assertEqual(item.number, 7)
        self.assertEqual(len(item.actions), 3)
        self.assertEqual(item.outcomes[-1].action_id, 'new-source')
        self.assertEqual(item.outcomes[-1].text, '**Pending**')

    def test_bad_structure_never_recovers_a_partial_record(self):
        for broken in [
            REPORT.replace('<!-- action:rename -->', '<!-- action:example -->'),
            REPORT.replace('action:rename -->**Declined', 'action:missing -->**Declined'),
            REPORT.replace('<!-- action:rename -->', ''),
            REPORT.replace('P1 |', 'P9 |'),
            REPORT.replace('`a\\|b`', '`a|b`'),
            REPORT.replace('item:original', 'item:original extra=data'),
        ]:
            with self.subTest(broken=broken):
                with self.assertRaises(ReviewError):
                    parse_report(broken)

    def test_duplicate_item_or_event_and_wrong_run_or_scope_stop(self):
        row = next(line for line in REPORT.splitlines() if '<!-- item:' in line)
        with self.assertRaises(ReviewError):
            parse_report(REPORT.replace(row, row + '\n' + row))
        with self.assertRaises(ReviewError):
            parse_report(REPORT.replace('outcome:decline-name', 'outcome:pending-example'))
        for kwargs in [{'run_id': 'other'}, {'scope': 'selected:other'}]:
            with self.assertRaises(ReviewError):
                parse_report(REPORT, **kwargs)

    def test_empty_report_is_valid_and_hidden_data_is_identification_only(self):
        report = new_report('synthetic', 'selected:empty', '# Atomic note audit\n\nNo changes.\n')
        text = render_report(report)
        self.assertEqual(parse_report(text).items, [])
        self.assertNotIn('{', text)
        self.assertNotIn('recommendation=', text)

    def test_table_content_supports_unicode_entities_and_multiline_math(self):
        report = new_report('synthetic', 'selected:one', '# Atomic note audit\n')
        add_item(report, 'Atomic Notes/λ [example]|x.md', 'P2', [('math', 'Use $x|y$\nExplain λ & units.')])
        text = render_report(report)
        item = parse_report(text).items[0]
        self.assertEqual(note_target(item.note), 'Atomic Notes/λ [example]|x.md')
        self.assertIn(r'Use $x\|y$<br>Explain λ & units.', item.actions[0].text)

    def test_gfm_pipe_escaping_preserves_backslashes_inside_code_and_math(self):
        report = new_report('synthetic', 'selected:one', '# Atomic note audit\n')
        add_item(report, 'Atomic Notes/Example.md', 'P2', [('pipes', r'Use `x\|y` and $x|y$.')])
        text = render_report(report)
        self.assertIn(r'`x\\|y`', text)
        self.assertIn(r'$x\|y$', text)
        self.assertEqual(render_report(parse_report(text)), text)

    def test_old_or_incomplete_report_needs_reconciliation(self):
        with self.assertRaisesRegex(ReviewError, 'reconcil'):
            parse_report(REPORT.replace('<!-- atomic-note-audit:1.0.0 run=synthetic scope=selected%3Aone -->\n', ''))
