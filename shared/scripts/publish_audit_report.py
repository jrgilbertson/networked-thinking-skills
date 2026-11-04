"""Publish only the selected audit report through the running Obsidian app."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.scripts.audit_review_report import RETIRED_NOTE_PREFIX, ReviewError, TABLE_HEADER, note_target, parse_report
from shared.scripts.config import DEFAULT_CONFIG
from shared.scripts.obsidian_adapter import ObsidianAdapter, decode_eval_base64_output, ObsidianTransportError


def report_basename(timestamp: str | None = None) -> str:
    captured = timestamp if timestamp is not None else datetime.now().astimezone().strftime("%Y%m%d%H%M")
    if not isinstance(captured, str) or re.fullmatch(r"[0-9]{12}", captured) is None:
        raise ReviewError("Report timestamp must be YYYYMMDDHHMM in the user's local time")
    try:
        datetime.strptime(captured, "%Y%m%d%H%M")
    except ValueError as exc:
        raise ReviewError("Report timestamp is not a valid local date and minute") from exc
    return f"{captured} Atomic note audit.md"


def _relative_path(path: str) -> bool:
    return bool(path) and not path.startswith("/") and not any(c in path for c in ("\\", ":", "\n", "\r")) and all(
        part not in {"", ".", ".."} for part in path.split("/"))


def build_publish_code(payload_path: Path) -> str:
    encoded = base64.b64encode(json.dumps(str(payload_path), ensure_ascii=True).encode("utf-8")).decode("ascii")
    return '(async () => { const payloadPath = JSON.parse(atob("' + encoded + '"));' + '''
 const payload = JSON.parse(require('fs').readFileSync(payloadPath,'utf8'));
 const configFile = app.vault.getAbstractFileByPath('.networked-thinking/config.json');
 const config = configFile ? JSON.parse(await app.vault.read(configFile)) : {};
 const configured = config.audit_output_folder || payload.defaultFolder;
 const folder = payload.folder || configured;
 if (config.audit_output_folder && folder !== configured) throw Error('configured report folder changed');
 if (typeof folder !== 'string' || !folder || folder.startsWith('/') || folder.includes(':') || folder.includes(String.fromCharCode(92)) || folder.split('/').some(p => !p || p === '.' || p === '..')) throw Error('invalid audit output folder');
 const path = payload.path || folder + '/' + payload.basename;
 if (!path.startsWith(folder + '/') || (payload.expected === null && path !== folder + '/' + payload.basename)) throw Error('unexpected report destination');
 const verifyTargets = () => {
  for (const target of [...payload.targets,...payload.retiredTargets]) {
   if (target === path) throw Error('report cannot overwrite an audited source note');
  }
  for (const target of payload.targets) {
   const dest = app.metadataCache.getFirstLinkpathDest(target,path);
   if (!dest || dest.path !== target) throw Error('unresolved or wrong report link: ' + target);
  }
  for (const target of payload.retiredTargets) {
   if (app.vault.getAbstractFileByPath(target)) throw Error('retired source still exists: ' + target);
  }
 };
 verifyTargets();
 const file = app.vault.getAbstractFileByPath(path);
 if (payload.expected === null) {
  if (file) throw Error('report destination already exists; inspect before retrying');
  const parts = folder.split('/');
  for (let i=1; i<=parts.length; i++) {
   const parent = parts.slice(0,i).join('/');
   if (!app.vault.getAbstractFileByPath(parent)) await app.vault.createFolder(parent);
  }
  await app.vault.create(path,payload.draft);
 } else {
  if (!file) throw Error('selected report is missing; reconcile before publication');
  await app.vault.process(file, data => {
   if (data !== payload.expected) throw Error('report changed after read; reconcile current text');
   return payload.draft;
  });
 }
 const published = app.vault.getAbstractFileByPath(path);
 if (!published || await app.vault.read(published) !== payload.draft) throw Error('report readback mismatch; inspect before retrying');
 verifyTargets();
 const value = {path,links_verified:payload.targets.length,retired_targets_verified:payload.retiredTargets.length};
 const bytes = new TextEncoder().encode(JSON.stringify(value));
 let binary = ''; for (const byte of bytes) binary += String.fromCharCode(byte);
 return btoa(binary);
})()'''


def publish_report(adapter: ObsidianAdapter, *, vault: str, draft: str, timestamp: str | None = None,
                   output_folder: str | None = None, report_path: str | None = None,
                   expected_text: str | None = None) -> dict[str, object]:
    report = parse_report(draft)
    if not isinstance(vault, str) or not vault.strip():
        raise ReviewError("An explicit Obsidian vault is required")
    if output_folder is not None and not _relative_path(output_folder):
        raise ReviewError("Expected a configured vault-relative output folder")
    if report_path is not None:
        if not _relative_path(report_path) or not report_path.endswith(".md") or expected_text is None:
            raise ReviewError("Selected report updates require a relative Markdown path and current snapshot")
        if timestamp is not None:
            raise ReviewError("A refresh keeps the selected report's timestamp and path")
    elif expected_text is not None:
        raise ReviewError("An expected snapshot requires its selected report path")
    if expected_text is not None:
        if '<!-- atomic-note-audit:' in expected_text:
            parse_report(expected_text, run_id=report.run_id, scope=report.scope)
        elif TABLE_HEADER not in expected_text:
            raise ReviewError("Selected legacy input is not a numbered audit report")
    payload = dict(draft=draft, expected=expected_text, path=report_path,
                   basename=report_basename(timestamp) if report_path is None else PurePosixPath(report_path).name,
                   folder=output_folder, defaultFolder=DEFAULT_CONFIG["audit_output_folder"],
                   targets=[note_target(item.note) for item in report.items if not item.note.startswith(RETIRED_NOTE_PREFIX)],
                   retiredTargets=[note_target(item.note) for item in report.items if item.note.startswith(RETIRED_NOTE_PREFIX)])
    with tempfile.TemporaryDirectory(prefix="atomic-audit-publish-") as temporary:
        payload_path = Path(temporary) / "payload.json"
        payload_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        result = adapter.run([f"vault={vault}", "eval", f"code={build_publish_code(payload_path)}"])
    if not result.ok:
        raise ReviewError("Report publication failed or is uncertain; inspect the actual report before retrying: "
                          + (result.stderr or result.stdout or str(result.returncode)).strip())
    try:
        receipt = json.loads(decode_eval_base64_output(result.stdout))
        if (not isinstance(receipt, dict) or set(receipt) != {"path", "links_verified", "retired_targets_verified"}
                or not isinstance(receipt["path"], str) or not _relative_path(receipt["path"])
                or type(receipt["links_verified"]) is not int or receipt["links_verified"] != len(payload["targets"])
                or type(receipt["retired_targets_verified"]) is not int
                or receipt["retired_targets_verified"] != len(payload["retiredTargets"])
                or (report_path is not None and receipt["path"] != report_path)):
            raise ReviewError("Invalid publication acknowledgement")
    except (ValueError, ObsidianTransportError) as exc:
        raise ReviewError("Publication response is uncertain; inspect the actual report before retrying") from exc
    receipt["content_hash"] = hashlib.sha256(draft.encode("utf-8")).hexdigest()
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish an audit report through Obsidian and verify readback and links.")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--draft", type=Path, required=True, help="External Markdown draft")
    parser.add_argument("--timestamp", help="Initial YYYYMMDDHHMM in user local time; default is this machine's local time")
    parser.add_argument("--output-folder", help="Resolved audit_output_folder; otherwise read app configuration")
    parser.add_argument("--report-path", help="Existing selected vault-relative report; never rename on refresh")
    parser.add_argument("--expected-snapshot", type=Path, help="Fresh external snapshot of the selected report")
    parser.add_argument("--obsidian-binary", default="obsidian")
    args = parser.parse_args(argv)
    try:
        receipt = publish_report(ObsidianAdapter(args.obsidian_binary, timeout_seconds=30), vault=args.vault,
            draft=args.draft.read_text(encoding="utf-8"), timestamp=args.timestamp, output_folder=args.output_folder,
            report_path=args.report_path,
            expected_text=args.expected_snapshot.read_text(encoding="utf-8") if args.expected_snapshot else None)
    except (OSError, ValueError, ObsidianTransportError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
