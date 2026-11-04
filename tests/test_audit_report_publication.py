import json
import shutil
import subprocess
import unittest

from shared.scripts.obsidian_adapter import CommandResult
from shared.scripts.publish_audit_report import publish_report, report_basename
from shared.scripts.audit_review_report import ReviewError, add_item, parse_report, render_report
from shared.scripts.record_audit_outcome import prepare_outcome
from test_audit_outcome_recording import event
from test_audit_review_report import REPORT


NODE_APP = r'''
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0,'utf8'));
const files = new Map(Object.entries(input.files));
const folders = new Set(input.folders || []);
const writes = [];
global.app = {
 vault: {
  getAbstractFileByPath: path => path.split('/').some(p => p.startsWith('.')) ? null : files.has(path) || folders.has(path) ? {path} : null,
  adapter: {exists: async path => files.has(path) || folders.has(path), read: async path => files.get(path)},
  read: async file => {
   if (input.reappearAfterWrite && writes.includes(file.path)) files.set(input.reappearAfterWrite,'Reappeared source.');
   return input.badReadback && writes.includes(file.path) ? files.get(file.path)+'changed' : files.get(file.path);
  },
  process: async (file, callback) => {
   if (input.concurrent) files.set(file.path, input.concurrent);
   const result = callback(files.get(file.path));
   files.set(file.path,result); writes.push(file.path);
  },
  create: async (path, text) => {
   if(files.has(path)) throw Error('already exists');
   files.set(path,text); writes.push(path);
  },
  createFolder: async path => {folders.add(path);}
 },
 metadataCache: {getFirstLinkpathDest: target => input.badLink ? {path:'wrong.md'} : files.has(target) ? {path:target} : null}
};
(async()=>{
 try {const result=await eval(input.code); console.log(JSON.stringify({ok:true,stdout:'=> '+result,files:Object.fromEntries(files),folders:[...folders],writes}));}
 catch(e){console.log(JSON.stringify({ok:false,stderr:String(e),files:Object.fromEntries(files),folders:[...folders],writes}));}
})();
'''


class AppAdapter:
    def __init__(self, files=None, **conditions):
        self.files = {'Atomic Notes/Example|math.md': 'Synthetic source, unchanged.', **(files or {})}
        self.folders = []
        self.writes = []
        self.conditions = conditions

    def run(self, args):
        if self.conditions.get('denied'):
            return CommandResult(False, '', 'transport denied', 1)
        code = next(a[5:] for a in args if a.startswith('code='))
        if self.conditions.get('argLimit') and len(code.encode()) > self.conditions['argLimit']:
            raise OSError('Argument list too long')
        result = subprocess.run(['node', '-e', NODE_APP], input=json.dumps(dict(
            code=code, files=self.files, folders=self.folders, **self.conditions)), text=True, capture_output=True)
        if result.returncode:
            raise AssertionError(result.stderr)
        value = json.loads(result.stdout)
        if self.conditions.get('badReceipt'):
            value['stdout'] = '=> e30='
        self.files, self.folders = value['files'], value['folders']
        self.writes.extend(value['writes'])
        return CommandResult(value['ok'], value.get('stdout',''), value.get('stderr',''), 0 if value['ok'] else 1)


@unittest.skipUnless(shutil.which('node'), 'Node is needed to execute the generated app-boundary JavaScript')
class ReportPublicationTest(unittest.TestCase):
    path = 'Reviews/Atomic Note Audits/203001020304 Atomic note audit.md'

    def test_create_default_report_and_verify_exact_content_and_targets(self):
        adapter = AppAdapter()
        receipt = publish_report(adapter, vault='Synthetic vault', draft=REPORT, timestamp='203001020304')
        self.assertEqual(receipt['path'], self.path)
        self.assertEqual(receipt['links_verified'], 1)
        self.assertEqual(adapter.files[self.path], REPORT)
        self.assertEqual(adapter.writes, [self.path])
        self.assertEqual(adapter.files['Atomic Notes/Example|math.md'], 'Synthetic source, unchanged.')

    def test_configured_output_folder_and_refresh_keep_existing_timestamp(self):
        path = 'Reviews/Audits/203001020304 Atomic note audit.md'
        adapter = AppAdapter({'.networked-thinking/config.json': json.dumps({'audit_output_folder':'Reviews/Audits'})})
        first = publish_report(adapter, vault='Synthetic vault', draft=REPORT, timestamp='203001020304')
        self.assertEqual(first['path'], path)
        edited = REPORT + '\nLearner follow-up.\n'
        publish_report(adapter, vault='Synthetic vault', draft=edited, report_path=path, expected_text=REPORT)
        self.assertEqual(adapter.files[path], edited)
        self.assertEqual([p for p in adapter.files if p.endswith('Atomic note audit.md')], [path])
        before = dict(adapter.files)
        with self.assertRaises(ReviewError):
            publish_report(adapter, vault='Synthetic vault', draft=edited, report_path=path,
                           expected_text=edited, output_folder='Reviews/Old configuration')
        self.assertEqual(adapter.files, before)

    def test_new_report_never_overwrites_a_collision(self):
        adapter = AppAdapter({self.path:'Other report or learner text.'})
        with self.assertRaises(ReviewError):
            publish_report(adapter, vault='Synthetic vault', draft=REPORT, timestamp='203001020304')
        self.assertEqual(adapter.files[self.path], 'Other report or learner text.')
        self.assertEqual(adapter.writes, [])

    def test_concurrent_edits_are_preserved_at_the_app_update_boundary(self):
        adapter = AppAdapter({self.path:REPORT}, concurrent=REPORT+'\nConcurrent edit.\n')
        with self.assertRaises(ReviewError):
            publish_report(adapter, vault='Synthetic vault', draft=REPORT+'\nDraft.\n',
                           report_path=self.path, expected_text=REPORT)
        self.assertTrue(adapter.files[self.path].endswith('Concurrent edit.\n'))
        self.assertEqual(adapter.writes, [])

    def test_denial_bad_readback_or_wrong_link_never_claims_success(self):
        for conditions in [dict(denied=True), dict(badReadback=True), dict(badLink=True), dict(badReceipt=True)]:
            with self.subTest(conditions=conditions):
                adapter = AppAdapter(**conditions)
                with self.assertRaises(ReviewError):
                    publish_report(adapter, vault='Synthetic vault', draft=REPORT, timestamp='203001020304')
                self.assertLessEqual(len(adapter.writes), 1)

    def test_source_path_or_changed_audit_identity_is_not_a_report_update(self):
        adapter = AppAdapter({self.path:REPORT})
        for path, draft in [('Atomic Notes/Example|math.md', REPORT),
                            (self.path, REPORT.replace('run=synthetic ', 'run=other '))]:
            with self.subTest(path=path), self.assertRaises(ReviewError):
                publish_report(adapter, vault='Synthetic vault', draft=draft, report_path=path, expected_text=REPORT)
        self.assertEqual(adapter.writes, [])

    def test_new_reports_reject_bad_timestamps(self):
        for timestamp in ['203002300304','not-a-date','20300102030405']:
            with self.subTest(timestamp=timestamp), self.assertRaises(ReviewError):
                report_basename(timestamp)

    def test_large_report_does_not_exceed_command_argument_limits(self):
        adapter = AppAdapter(argLimit=32000)
        large = REPORT + ('A retained learner observation.\n' * 40000)
        publish_report(adapter, vault='Synthetic vault', draft=large, timestamp='203001020304')
        self.assertEqual(adapter.files[self.path], large)

    def test_verified_deleted_source_retains_history_and_allows_other_item_updates(self):
        retired = prepare_outcome(REPORT, event(retire_target=True,
            previous_path='Atomic Notes/Example|math.md', description='Verified approved source deletion.'))
        report = parse_report(retired)
        add_item(report, 'Atomic Notes/Live.md', 'P2', [('clarify', 'Clarify the live note.')])
        retired = render_report(report)
        adapter = AppAdapter({'Atomic Notes/Live.md': 'Live source, unchanged.'})
        del adapter.files['Atomic Notes/Example|math.md']
        with self.assertRaises(ReviewError):
            publish_report(adapter, vault='Synthetic vault', draft=REPORT, timestamp='203001020304')
        first = publish_report(adapter, vault='Synthetic vault', draft=retired, timestamp='203001020304')
        self.assertEqual(first['links_verified'], 1)
        self.assertEqual(first['retired_targets_verified'], 1)
        updated = prepare_outcome(retired, event(item=8, action_id='clarify', event_id='hold-live',
            status='Held', verification={}, description='Wait for learner input.'))
        publish_report(adapter, vault='Synthetic vault', draft=updated,
                       report_path=self.path, expected_text=retired)
        self.assertIn('Wait for learner input.', adapter.files[self.path])
        self.assertIn('Learner prefers this name.', adapter.files[self.path])
        self.assertNotIn('Atomic Notes/Example|math.md', adapter.files)
        self.assertEqual(adapter.files['Atomic Notes/Live.md'], 'Live source, unchanged.')
        adapter.files['Atomic Notes/Example|math.md'] = 'Source has reappeared.'
        before = adapter.files[self.path]
        with self.assertRaises(ReviewError):
            publish_report(adapter, vault='Synthetic vault', draft=updated,
                           report_path=self.path, expected_text=before)
        self.assertEqual(adapter.files[self.path], before)
        racing = AppAdapter({'Atomic Notes/Live.md': 'Live source.'},
                            reappearAfterWrite='Atomic Notes/Example|math.md')
        del racing.files['Atomic Notes/Example|math.md']
        with self.assertRaisesRegex(ReviewError, 'uncertain'):
            publish_report(racing, vault='Synthetic vault', draft=retired, timestamp='203001020304')
        self.assertEqual(racing.writes, [self.path])
        hidden = REPORT.replace('Atomic%20Notes/Example%7Cmath.md', '.archive/Example.md')
        hidden = prepare_outcome(hidden, event(retire_target=True, previous_path='.archive/Example.md'))
        still_present = AppAdapter({'.archive/Example.md': 'Hidden source still exists.'})
        with self.assertRaisesRegex(ReviewError, 'retired source still exists'):
            publish_report(still_present, vault='Synthetic vault', draft=hidden, timestamp='203001020304')
        self.assertEqual(still_present.writes, [])
