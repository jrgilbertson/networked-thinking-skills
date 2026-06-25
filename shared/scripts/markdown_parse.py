from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re


FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?:(.*?)\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
WIKILINK_RE = re.compile(r"!\[\[([^\[\]\r\n]+)\]\]|\[\[([^\[\]\r\n]+)\]\]")
HEADING_RE = re.compile(r"^[ ]{0,3}#{1,6}[ \t]+([^\r\n]+?)[ \t]*\r?$", re.MULTILINE)
FENCE_START_RE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1)[^\r\n])*?\1")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
LIST_MARKER_RE = re.compile(r"(?:[-*+]|\d+[.)])[ \t]+")
WORD_RE = re.compile(r"\b[\w'-]+\b")
CLOZE_RE = re.compile(r"\{\{c\d+::(.*?)(?:::.*?)?\}\}")
TIMESTAMP_PREFIX_RE = re.compile(r"^\d{12}\s+")
BACK_LINE_RE = re.compile(r"^[ \t]*Back:[ \t]*(.*)$", re.IGNORECASE)
EXTRA_LINE_RE = re.compile(r"^[ \t]*Extra:[ \t]*(.*)$", re.IGNORECASE)
# Matches a plain trailing Reference:/Sources: label line (not a ## heading section).
# Used to clamp DAE section boundaries so label content is not counted as DAE text.
TRAILING_LABEL_LINE_RE = re.compile(
    r"^(?:#{1,6}[ \t]+)?(?:reference|source)s?:?[ \t]*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DaeAnalysis:
    present: bool
    shape: str | None = None
    definition_word_count: int | None = None
    definition_too_short: bool = False
    definition_too_long: bool = False
    has_definition: bool = False
    has_analogy: bool = False
    has_example: bool = False


def extract_frontmatter(markdown: str) -> tuple[str | None, str]:
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return None, markdown
    return match.group(1) or "", markdown[match.end():]


def _line_break(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


def _is_closing_fence(line: str, fence_char: str, fence_length: int) -> bool:
    pattern = rf"^[ ]{{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*(?:\r?\n)?\Z"
    return re.match(pattern, line) is not None


def _find_html_comment_start_outside_inline_code(line: str) -> int:
    search_start = 0
    for match in INLINE_CODE_RE.finditer(line):
        comment_start = line.find("<!--", search_start, match.start())
        if comment_start != -1:
            return comment_start
        search_start = match.end()
    return line.find("<!--", search_start)


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


def _list_marker_prefix(line: str, content: str, list_marker: re.Match[str]) -> str:
    leading_length = len(line) - len(content)
    return line[:leading_length + list_marker.end()]


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
    in_html_comment = False
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

        if in_html_comment:
            masked_lines.append(line)
            if "-->" in line:
                in_html_comment = False
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
                masked_lines.append(_list_marker_prefix(line, content, list_marker) + _line_break(line))
                list_contexts = _update_list_contexts(
                    list_contexts,
                    line,
                    indent_width,
                    content,
                    list_marker,
                    False,
                )
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

        comment_start = _find_html_comment_start_outside_inline_code(line)
        if comment_start != -1 and not (
            _is_indented_code_line(line) and active_content_indent is None
        ):
            in_html_comment = "-->" not in line[comment_start + 4:]

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
    without_fenced_code = _mask_fenced_code_blocks(body)
    without_indented_code = _mask_indented_code_blocks(without_fenced_code)
    without_inline_code = _mask_inline_code_spans(without_indented_code)
    return _mask_html_comments(without_inline_code)


def extract_wikilinks(markdown: str) -> list[str]:
    targets: list[str] = []
    link_markdown = _wikilink_markdown(markdown)
    inline_code_spans = [
        (match.start(), match.end())
        for match in INLINE_CODE_RE.finditer(link_markdown)
    ]
    for match in WIKILINK_RE.finditer(link_markdown):
        if _is_contained_by_any_span(match.start(), match.end(), inline_code_spans):
            continue
        link = match.group(1) or match.group(2)
        target = link.split("|", 1)[0].strip()
        targets.append(target)
    return targets


def _wikilink_markdown(markdown: str) -> str:
    _, body = extract_frontmatter(markdown)
    without_fenced_code = _mask_fenced_code_blocks(body)
    without_indented_code = _mask_indented_code_blocks(without_fenced_code)
    return _mask_html_comments_outside_inline_code(without_indented_code)


def _is_contained_by_any_span(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(span_start <= start and end <= span_end for span_start, span_end in spans)


def _is_position_inside_any_span(position: int, spans: list[tuple[int, int]]) -> bool:
    return any(span_start <= position < span_end for span_start, span_end in spans)


def _mask_html_comments_outside_inline_code(markdown: str) -> str:
    inline_code_spans = [
        (match.start(), match.end())
        for match in INLINE_CODE_RE.finditer(markdown)
    ]
    comment_ranges: list[tuple[int, int]] = []
    position = 0
    while True:
        start = markdown.find("<!--", position)
        if start == -1:
            break
        if _is_position_inside_any_span(start, inline_code_spans):
            position = start + 4
            continue
        end = markdown.find("-->", start + 4)
        if end == -1:
            comment_ranges.append((start, len(markdown)))
            break
        comment_ranges.append((start, end + 3))
        position = end + 3
    if not comment_ranges:
        return markdown
    chunks: list[str] = []
    position = 0
    for start, end in comment_ranges:
        chunks.append(markdown[position:start])
        chunks.append(_mask_text_preserving_line_breaks(markdown[start:end]))
        position = end
    chunks.append(markdown[position:])
    return "".join(chunks)


def _normalize_heading_text(heading: str) -> str:
    return re.sub(r"\s+#+\s*$", "", heading.strip()).strip()


def extract_structural_heading_lines(markdown: str) -> list[tuple[int, int, str]]:
    """Return structural headings as body-relative line number, level, and text."""
    headings: list[tuple[int, int, str]] = []
    for line_number, line in enumerate(_structural_markdown(markdown).splitlines(keepends=True)):
        match = HEADING_RE.match(line)
        if match:
            marker = line.lstrip(" ").split(None, 1)[0]
            headings.append((line_number, len(marker), _normalize_heading_text(match.group(1))))
    return headings


def extract_headings(markdown: str) -> list[str]:
    return [
        heading
        for _, _, heading in extract_structural_heading_lines(markdown)
    ]


def has_dae_sections(markdown: str) -> bool:
    headings = {heading.casefold() for heading in extract_headings(markdown)}
    if {"definition", "analogy", "example"}.issubset(headings):
        return True
    return any(
        analysis.has_definition and analysis.has_analogy and analysis.has_example
        for analysis in (_analyze_anki_card_dae(card) for card in _extract_anki_card_texts(markdown))
    )


def analyze_dae(markdown: str) -> DaeAnalysis:
    analyses = [_analyze_heading_dae(markdown)]
    analyses.extend(_analyze_anki_card_dae(card) for card in _extract_anki_card_texts(markdown))
    return max(analyses, key=_analysis_rank)


def count_rendered_words(markdown: str) -> int:
    text = _render_wikilinks_for_word_count(markdown)
    text = CLOZE_RE.sub(lambda match: match.group(1), text)
    text = HTML_COMMENT_RE.sub(" ", text)
    return len(WORD_RE.findall(text))


def count_anki_blocks(markdown: str) -> dict[str, int]:
    counts = {"START": 0, "END": 0}
    for line in _structural_markdown(markdown).splitlines():
        if line in counts:
            counts[line] += 1
    return counts


def _analysis_rank(analysis: DaeAnalysis) -> tuple[int, int, int, int]:
    return (
        int(analysis.present),
        int(analysis.definition_too_long),
        int(analysis.has_analogy) + int(analysis.has_example),
        analysis.definition_word_count or 0,
    )


def _analyze_heading_dae(markdown: str) -> DaeAnalysis:
    sections = _dae_heading_sections(markdown)
    if not {"definition", "analogy", "example"}.issubset(sections):
        return DaeAnalysis(present=False, shape="headings")
    return _build_dae_analysis(
        "headings",
        definition=sections["definition"],
        analogy_paragraphs=_prose_paragraphs(sections["analogy"]),
        example_paragraphs=_prose_paragraphs(sections["example"]),
    )


def _analyze_anki_card_dae(card_text: str) -> DaeAnalysis:
    card_type, body = _split_card_type(card_text)
    if card_type == "basic":
        return _analyze_basic_card_dae(body)
    if card_type == "cloze":
        return _analyze_cloze_card_dae(body)
    return DaeAnalysis(present=False, shape=card_type or "anki")


def _analyze_basic_card_dae(card_body: str) -> DaeAnalysis:
    back_text = _extract_back_text(card_body)
    if back_text is None:
        return DaeAnalysis(present=False, shape="Basic")
    paragraphs = _prose_paragraphs(back_text)
    if not paragraphs:
        return DaeAnalysis(present=False, shape="Basic")
    return _build_dae_analysis(
        "Basic",
        definition=paragraphs[0],
        analogy_paragraphs=paragraphs[1:],
        example_paragraphs=paragraphs[1:],
    )


def _analyze_cloze_card_dae(card_body: str) -> DaeAnalysis:
    before_extra, extra = _split_extra_text(card_body)
    if extra is None:
        return DaeAnalysis(present=False, shape="Cloze")
    definition_paragraphs = _prose_paragraphs(before_extra)
    if not definition_paragraphs:
        return DaeAnalysis(present=False, shape="Cloze")
    extra_paragraphs = _prose_paragraphs(extra)
    return _build_dae_analysis(
        "Cloze",
        definition=definition_paragraphs[0],
        analogy_paragraphs=extra_paragraphs,
        example_paragraphs=extra_paragraphs,
    )


def _build_dae_analysis(
    shape: str,
    *,
    definition: str,
    analogy_paragraphs: list[str],
    example_paragraphs: list[str],
) -> DaeAnalysis:
    definition_word_count = count_rendered_words(definition)
    has_definition = definition_word_count > 0
    has_analogy = any(_looks_like_analogy(paragraph) for paragraph in analogy_paragraphs)
    has_example = any(_starts_with_example(paragraph) for paragraph in example_paragraphs)
    definition_too_short = has_definition and definition_word_count < 10
    definition_too_long = definition_word_count > 50
    return DaeAnalysis(
        present=(
            has_definition
            and not definition_too_short
            and not definition_too_long
            and has_analogy
            and has_example
        ),
        shape=shape,
        definition_word_count=definition_word_count if has_definition else None,
        definition_too_short=definition_too_short,
        definition_too_long=definition_too_long,
        has_definition=has_definition,
        has_analogy=has_analogy,
        has_example=has_example,
    )


def _dae_heading_sections(markdown: str) -> dict[str, str]:
    _, body = extract_frontmatter(markdown)
    body_lines = body.splitlines()
    heading_lines = [
        (line_number, level, heading.casefold())
        for line_number, level, heading in extract_structural_heading_lines(markdown)
    ]
    # Pre-compute the first trailing-label line index so each section can be
    # clamped to exclude Reference:/Sources: plain labels (not ## headings).
    first_trailing_label: int = len(body_lines)
    for i, line in enumerate(body_lines):
        if TRAILING_LABEL_LINE_RE.match(line):
            first_trailing_label = i
            break
    sections: dict[str, str] = {}
    for index, (line_number, level, heading) in enumerate(heading_lines):
        if heading not in {"definition", "analogy", "example"}:
            continue
        end_line = len(body_lines)
        for next_line, next_level, _ in heading_lines[index + 1:]:
            if next_level <= level:
                end_line = next_line
                break
        # Clamp so plain trailing labels are never included in the section body.
        # Only apply when the trailing label is within (not before) this section.
        if first_trailing_label > line_number:
            end_line = min(end_line, first_trailing_label)
        sections[heading] = "\n".join(body_lines[line_number + 1:end_line]).strip()
    return sections


def _extract_anki_card_texts(markdown: str) -> list[str]:
    _, body = extract_frontmatter(markdown)
    body_lines = body.splitlines()
    structural_lines = _structural_markdown(markdown).splitlines()
    cards: list[str] = []
    start_line: int | None = None

    for index, line in enumerate(structural_lines):
        if line == "START":
            start_line = index
            continue
        if line == "END" and start_line is not None:
            cards.append("\n".join(body_lines[start_line + 1:index]).strip())
            start_line = None

    return cards


def _split_card_type(card_text: str) -> tuple[str | None, str]:
    lines = card_text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped:
            return stripped.casefold(), "\n".join(lines[index + 1:])
    return None, ""


def _extract_back_text(card_body: str) -> str | None:
    lines = card_body.splitlines()
    for index, line in enumerate(lines):
        match = BACK_LINE_RE.match(line)
        if match:
            return "\n".join([match.group(1), *lines[index + 1:]]).strip()
    return None


def _split_extra_text(card_body: str) -> tuple[str, str | None]:
    lines = card_body.splitlines()
    for index, line in enumerate(lines):
        match = EXTRA_LINE_RE.match(line)
        if match:
            return (
                "\n".join(lines[:index]).strip(),
                "\n".join([match.group(1), *lines[index + 1:]]).strip(),
            )
    return card_body.strip(), None


def _prose_paragraphs(markdown: str) -> list[str]:
    markdown = _mask_fenced_code_blocks(markdown)
    markdown = _mask_indented_code_blocks(markdown)
    markdown = _mask_html_comments(markdown)
    paragraphs = []
    for paragraph in re.split(r"(?:\r?\n){2,}", markdown):
        stripped = paragraph.strip()
        if not stripped or _is_display_math_paragraph(stripped):
            continue
        if count_rendered_words(stripped) == 0:
            continue
        paragraphs.append(stripped)
    return paragraphs


def _is_display_math_paragraph(paragraph: str) -> bool:
    stripped = paragraph.strip()
    return stripped.startswith("$$") and stripped.endswith("$$")


def _looks_like_analogy(paragraph: str) -> bool:
    visible = _render_wikilinks_for_word_count(paragraph).casefold()
    return bool(
        re.search(r"\b(is|are|was|were) like\b", visible)
        or re.search(r"\blike (a|an|the)\b", visible)
        or "think of " in visible
        or "consider " in visible
        or "can be compared to" in visible
    )


def _starts_with_example(paragraph: str) -> bool:
    return re.match(r"^[ \t]*(?:[-*+][ \t]+)?For example,(?:\s|$)", paragraph, re.IGNORECASE) is not None


def _render_wikilinks_for_word_count(markdown: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group(1):
            return ""
        link = match.group(2)
        if "|" in link:
            visible = link.split("|", 1)[1]
        else:
            visible = link.split("#", 1)[0].strip()
            if visible.endswith(".md"):
                visible = visible[:-3]
            visible = PurePosixPath(visible).name
            visible = TIMESTAMP_PREFIX_RE.sub("", visible)
        return visible.strip()

    return WIKILINK_RE.sub(replace, markdown)
