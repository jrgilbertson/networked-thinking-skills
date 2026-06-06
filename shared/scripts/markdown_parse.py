from __future__ import annotations

import re


FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
WIKILINK_RE = re.compile(r"!\[\[([^\[\]\r\n]+)\]\]|\[\[([^\[\]\r\n]+)\]\]")
HEADING_RE = re.compile(r"^[ ]{0,3}#{1,6}[ \t]+([^\r\n]+?)[ \t]*$", re.MULTILINE)
FENCE_START_RE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1)[^\r\n])*?\1")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
LIST_MARKER_RE = re.compile(r"(?:[-*+]|\d+[.)])[ \t]+")


def extract_frontmatter(markdown: str) -> tuple[str | None, str]:
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return None, markdown
    return match.group(1), markdown[match.end():]


def _line_break(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


def _is_closing_fence(line: str, fence_char: str, fence_length: int) -> bool:
    pattern = rf"^[ ]{{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*(?:\r?\n)?\Z"
    return re.match(pattern, line) is not None


def _active_list_content_indent(
    indent_width: int, list_contexts: list[tuple[int, int]]
) -> int | None:
    active_indents = [
        content_indent
        for _, content_indent in list_contexts
        if content_indent <= indent_width and indent_width - content_indent < 4
    ]
    if not active_indents:
        return None
    return max(active_indents)


def _list_marker_content_indent(
    line: str, content: str, list_marker: re.Match[str]
) -> int:
    leading_length = len(line) - len(content)
    marker_end = leading_length + list_marker.end()
    return len(line[:marker_end].expandtabs(4))


def _list_item_text(line: str, content: str, list_marker: re.Match[str]) -> str:
    leading_length = len(line) - len(content)
    return line[leading_length + list_marker.end():]


def _strip_indent_width(line: str, indent_width: int) -> str:
    index = 0
    width = 0
    while index < len(line) and width < indent_width:
        if line[index] == " ":
            width += 1
        elif line[index] == "\t":
            width += 4
        else:
            break
        index += 1
    if width >= indent_width:
        return line[index:]
    return line


def _update_list_contexts(
    list_contexts: list[tuple[int, int]],
    line: str,
    indent_width: int,
    content: str,
    list_marker: re.Match[str] | None,
    should_skip_update: bool,
) -> list[tuple[int, int]]:
    if should_skip_update or content.strip(" \t\r\n") == "":
        return list_contexts
    if list_marker is not None:
        content_indent = _list_marker_content_indent(line, content, list_marker)
        return [
            context
            for context in list_contexts
            if context[0] < indent_width
        ] + [(indent_width, content_indent)]
    return [
        context
        for context in list_contexts
        if context[1] <= indent_width
    ]


def _mask_fenced_code_blocks(markdown: str) -> str:
    masked_lines: list[str] = []
    in_fence = False
    fence_char = ""
    fence_length = 0
    fence_content_indent: int | None = None
    list_contexts: list[tuple[int, int]] = []

    for line in markdown.splitlines(keepends=True):
        indent_width = _indent_width(line)
        content = line.lstrip(" \t")
        list_marker = LIST_MARKER_RE.match(content)
        active_content_indent = _active_list_content_indent(indent_width, list_contexts)

        if in_fence:
            masked_lines.append(_line_break(line))
            fence_line = line
            if fence_content_indent is not None:
                fence_line = _strip_indent_width(line, fence_content_indent)
            if _is_closing_fence(fence_line, fence_char, fence_length):
                in_fence = False
                fence_content_indent = None
            continue

        if list_marker is not None and (
            not _is_indented_code_line(line) or active_content_indent is not None
        ):
            list_content_indent = _list_marker_content_indent(line, content, list_marker)
            list_fence_line = _list_item_text(line, content, list_marker)
            match = FENCE_START_RE.match(list_fence_line)
            if match:
                fence = match.group(1)
                in_fence = True
                fence_char = fence[0]
                fence_length = len(fence)
                fence_content_indent = list_content_indent
                masked_lines.append(_line_break(line))
                continue

        fence_line = line
        if active_content_indent is not None:
            fence_line = _strip_indent_width(line, active_content_indent)
        match = FENCE_START_RE.match(fence_line)
        if match:
            fence = match.group(1)
            in_fence = True
            fence_char = fence[0]
            fence_length = len(fence)
            fence_content_indent = active_content_indent
            masked_lines.append(_line_break(line))
            continue

        masked_lines.append(line)
        list_contexts = _update_list_contexts(
            list_contexts,
            line,
            indent_width,
            content,
            list_marker,
            _is_indented_code_line(line) and active_content_indent is None,
        )

    return "".join(masked_lines)


def _mask_indented_code_blocks(markdown: str) -> str:
    masked_lines: list[str] = []
    list_contexts: list[tuple[int, int]] = []

    for line in markdown.splitlines(keepends=True):
        indent_width = _indent_width(line)
        content = line.lstrip(" \t")
        list_marker = LIST_MARKER_RE.match(content)
        active_content_indent = _active_list_content_indent(indent_width, list_contexts)
        should_mask = _is_indented_code_line(line) and active_content_indent is None

        if should_mask:
            masked_lines.append(_line_break(line))
        else:
            masked_lines.append(line)

        list_contexts = _update_list_contexts(
            list_contexts,
            line,
            indent_width,
            content,
            list_marker,
            should_mask,
        )

    return "".join(masked_lines)


def _is_indented_code_line(line: str) -> bool:
    leading_whitespace = line[: len(line) - len(line.lstrip(" \t"))]
    return leading_whitespace.startswith("    ") or "\t" in leading_whitespace


def _indent_width(line: str) -> int:
    width = 0
    for char in line:
        if char == " ":
            width += 1
        elif char == "\t":
            width += 4
        else:
            break
    return width


def _mask_text_preserving_line_breaks(text: str) -> str:
    return "".join(char if char in "\r\n" else " " for char in text)


def _mask_html_comments(markdown: str) -> str:
    return HTML_COMMENT_RE.sub(lambda match: _mask_text_preserving_line_breaks(match.group(0)), markdown)


def _mask_inline_code_spans(markdown: str) -> str:
    return INLINE_CODE_RE.sub(lambda match: _mask_text_preserving_line_breaks(match.group(0)), markdown)


def _structural_markdown(markdown: str) -> str:
    _, body = extract_frontmatter(markdown)
    without_html_comments = _mask_html_comments(body)
    without_fenced_code = _mask_fenced_code_blocks(without_html_comments)
    without_indented_code = _mask_indented_code_blocks(without_fenced_code)
    return _mask_inline_code_spans(without_indented_code)


def extract_wikilinks(markdown: str) -> list[str]:
    targets: list[str] = []
    for match in WIKILINK_RE.finditer(_structural_markdown(markdown)):
        link = match.group(1) or match.group(2)
        target = link.split("|", 1)[0].strip()
        targets.append(target)
    return targets


def _normalize_heading_text(heading: str) -> str:
    return re.sub(r"\s+#+\s*$", "", heading.strip()).strip()


def extract_headings(markdown: str) -> list[str]:
    return [
        _normalize_heading_text(match.group(1))
        for match in HEADING_RE.finditer(_structural_markdown(markdown))
    ]


def has_dae_sections(markdown: str) -> bool:
    headings = {heading.casefold() for heading in extract_headings(markdown)}
    return {"definition", "analogy", "example"}.issubset(headings)


def count_anki_blocks(markdown: str) -> dict[str, int]:
    counts = {"START": 0, "END": 0}
    for line in _structural_markdown(markdown).splitlines():
        if line in counts:
            counts[line] += 1
    return counts
