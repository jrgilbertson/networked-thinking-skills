from __future__ import annotations

import re


TOP_HEADING_RE = re.compile(r"(?m)^#\s+(.+)$")


def propose_split(note_path: str, markdown: str) -> dict[str, object]:
    matches = list(TOP_HEADING_RE.finditer(markdown))
    outputs: list[dict[str, str]] = []

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        title = match.group(1).strip()
        safe_title = title.replace("/", "-")
        outputs.append(
            {
                "note_path": f"Atomic Notes/{safe_title}.md",
                "content": markdown[start:end].strip() + "\n",
            }
        )

    return {
        "source_note_path": note_path,
        "operation": "split",
        "delete_original": bool(outputs),
        "proposed_outputs": outputs,
    }
