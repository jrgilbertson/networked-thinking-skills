from __future__ import annotations

from shared.scripts.markdown_parse import (
    extract_frontmatter,
    extract_structural_heading_lines,
)


def _line_start_offsets(markdown: str) -> list[int]:
    offsets = [0]
    offset = 0
    for line in markdown.splitlines(keepends=True):
        offset += len(line)
        offsets.append(offset)
    return offsets


def propose_split(note_path: str, markdown: str) -> dict[str, object]:
    _, body = extract_frontmatter(markdown)
    body_start = len(markdown) - len(body)
    body_line_starts = _line_start_offsets(body)
    headings = [
        (line_number, title)
        for line_number, level, title in extract_structural_heading_lines(markdown)
        if level == 1
    ]
    outputs: list[dict[str, str]] = []

    for index, (line_number, title) in enumerate(headings):
        start = body_start + body_line_starts[line_number]
        end = (
            body_start + body_line_starts[headings[index + 1][0]]
            if index + 1 < len(headings)
            else len(markdown)
        )
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
