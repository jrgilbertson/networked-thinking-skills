import tempfile
import unittest
from pathlib import Path

from shared.scripts.audit_inventory import inventory_vault, evidence_directory
from shared.scripts.schema_validation import ValidationError, validate_inventory_row


class FakeAnki:
    def __init__(self, disconnected=False):
        self.actions = []
        self.disconnected = disconnected

    def invoke(self, action, params):
        self.actions.append(action)
        if self.disconnected:
            raise RuntimeError('unavailable')
        return []


class AuditInventoryTest(unittest.TestCase):
    def make_note(self, root, name, content):
        p = root / 'Atomic Notes' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def test_inventory_is_unscored_and_exact_checks_resolve_links(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_note(root, 'First.md', '# First\n\nEveryone always learns. [[Second]] [[Missing]]')
            self.make_note(root, 'Second.md', '# Second\n\nAnother idea.')
            rows = inventory_vault(root, run_id='synthetic')
            self.assertEqual(len(rows), 2)
            row = rows[0]
            validate_inventory_row(row)
            self.assertNotIn('score', row)
            self.assertNotIn('findings', row)
            checks = row['integrity_checks']
            self.assertTrue(any(c['code'] == 'unresolved_link' and c['status'] == 'failed' for c in checks))
            self.assertTrue(any(c['source'] == 'metadata' and c['status'] == 'failed' for c in checks))
            self.assertFalse(any(c['code'] in {'factual_risk', 'invalid_dae', 'weak_dae'} for c in checks))

    def test_duplicate_ids_and_unavailable_anki_remain_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            text = '# Example\nSTART\nBasic\nFront: A\nBack: B\n<!--ID: 123-->\nEND\n'
            for name in ['A.md', 'B.md']:
                self.make_note(root, name, text)
            client = FakeAnki(disconnected=True)
            rows = inventory_vault(root, run_id='synthetic', anki_client=client)
            for row in rows:
                checks = row['integrity_checks']
                self.assertTrue(any(c['code'] == 'shared_anki_id' and c['status'] == 'failed' for c in checks))
                self.assertTrue(any(c['source'] == 'anki' and c['status'] == 'not_checked' for c in checks))
            self.assertEqual(client.actions, ['notesInfo'])

    def test_missing_anki_target_is_read_only_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_note(root, 'Example.md', '# Example\n<!--ID: 123-->')
            client = FakeAnki()
            row = inventory_vault(root, run_id='synthetic', anki_client=client)[0]
            self.assertEqual(client.actions, ['notesInfo'])
            self.assertTrue(any(c['code'] == 'missing_anki_target' for c in row['integrity_checks']))

    def test_explicit_selection_and_source_reader(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            reads = []
            def reader(path):
                reads.append(path)
                return '# Snapshot\n\nSynthetic content.'
            rows = inventory_vault(root, run_id='synthetic', note_paths=['Atomic Notes/Chosen.md'], content_reader=reader, parent_targets=set(), link_resolver=lambda target, source: True)
            self.assertEqual(reads, ['Atomic Notes/Chosen.md'])
            self.assertEqual(rows[0]['note_path'], 'Atomic Notes/Chosen.md')
            with self.assertRaises(ValidationError):
                inventory_vault(root, run_id='synthetic', note_paths=['../outside.md'])

    def test_external_evidence_default_and_one_explicit_vault_directory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'vault'
            root.mkdir()
            self.assertFalse(evidence_directory(root, root.parent / 'run', allow_vault=False).is_relative_to(root))
            with self.assertRaises(ValidationError):
                evidence_directory(root, root / 'run', allow_vault=False)
            self.assertEqual(evidence_directory(root, root / 'run', allow_vault=True), root.resolve() / 'run' / 'Evidence')

    def test_heading_links_and_malformed_card_order(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_note(root, 'First.md', '# First\nEND\nSTART\n[[Second#Existing]] [[Second#Absent]]')
            self.make_note(root, 'Second.md', '# Second\n## Existing\nText.')
            checks = inventory_vault(root, run_id='synthetic')[0]['integrity_checks']
            self.assertTrue(any(c['code'] == 'card_markers' and c['status'] == 'failed' for c in checks))
            self.assertEqual(sum(c['code'] == 'unresolved_link' for c in checks), 1)
