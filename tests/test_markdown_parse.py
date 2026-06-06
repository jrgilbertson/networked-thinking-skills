import unittest

from shared.scripts.markdown_parse import (
    count_anki_blocks,
    extract_frontmatter,
    extract_headings,
    extract_wikilinks,
    has_dae_sections,
)


BASE_MARKDOWN = """---
title: Example
aliases:
  - sample
---

# Example

## Definition
Definition text.

## Analogy
Analogy text.

## Example
Example text linking to [[Atomic Note Quality|quality]] and ![[Embedded Note]].

START
Basic
Front: Question?
Back: Answer.
END
"""


class MarkdownParseTest(unittest.TestCase):
    def test_extract_frontmatter_returns_frontmatter_and_body(self):
        frontmatter, body = extract_frontmatter(BASE_MARKDOWN)
        self.assertEqual(frontmatter, "title: Example\naliases:\n  - sample")
        self.assertIn("# Example\n\n## Definition", body)

    def test_extract_wikilinks_returns_targets_for_links_and_embeds(self):
        self.assertEqual(
            extract_wikilinks(BASE_MARKDOWN),
            ["Atomic Note Quality", "Embedded Note"],
        )

    def test_extract_headings_includes_definition(self):
        self.assertIn("Definition", extract_headings(BASE_MARKDOWN))

    def test_has_dae_sections_returns_true_for_definition_analogy_example(self):
        self.assertTrue(has_dae_sections(BASE_MARKDOWN))

    def test_count_anki_blocks_returns_start_and_end_counts(self):
        self.assertEqual(count_anki_blocks(BASE_MARKDOWN), {"START": 1, "END": 1})

    def test_malformed_frontmatter_returns_none_and_original_body(self):
        markdown = "---\ntitle: Example\n\n# Example\n"
        frontmatter, body = extract_frontmatter(markdown)
        self.assertIsNone(frontmatter)
        self.assertEqual(body, markdown)

    def test_frontmatter_closing_fence_must_be_own_line(self):
        markdown = "---\ntitle: X\n---oops\n# Body\n"
        frontmatter, body = extract_frontmatter(markdown)
        self.assertIsNone(frontmatter)
        self.assertEqual(body, markdown)

    def test_extract_frontmatter_supports_crlf_line_endings(self):
        frontmatter, body = extract_frontmatter("---\r\ntitle: X\r\n---\r\n# Body\r\n")
        self.assertEqual(frontmatter, "title: X")
        self.assertEqual(body, "# Body\r\n")

    def test_empty_frontmatter_returns_empty_string_and_body(self):
        frontmatter, body = extract_frontmatter("---\n---\n# Body\n")
        self.assertEqual(frontmatter, "")
        self.assertEqual(body, "# Body\n")

    def test_no_frontmatter_returns_none_and_original_body(self):
        markdown = "# Example\n\nNo frontmatter here.\n"
        frontmatter, body = extract_frontmatter(markdown)
        self.assertIsNone(frontmatter)
        self.assertEqual(body, markdown)

    def test_extract_wikilinks_strips_alias_from_target(self):
        self.assertEqual(
            extract_wikilinks("[[Atomic Note Quality|quality]]"),
            ["Atomic Note Quality"],
        )

    def test_extract_wikilinks_ignores_four_space_indented_code(self):
        markdown = "    [[Not a real link]]\n\n[[Real Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_extract_wikilinks_ignores_tab_indented_code(self):
        markdown = "\t[[Not real]]\n[[Real Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_extract_wikilinks_preserves_nested_list_links(self):
        markdown = "- Parent\n    - [[Nested Note]]\n[[Top Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Nested Note", "Top Note"])

    def test_extract_wikilinks_preserves_list_continuation_links(self):
        markdown = "- Parent\n    [[Continuation Note]]\n[[Top Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Continuation Note", "Top Note"])

    def test_extract_wikilinks_preserves_deeper_space_indented_list_links(self):
        markdown = "- L1\n    - L2\n        - [[Deep Note]]\n[[Top Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Deep Note", "Top Note"])

    def test_extract_wikilinks_preserves_deeper_nested_list_after_list_code_masking(self):
        markdown = "- L1\n      [[Not real code]]\n    - L2\n        - [[Deep Note]]\n[[Top Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Deep Note", "Top Note"])

    def test_extract_wikilinks_preserves_deeper_tab_indented_list_links(self):
        markdown = "- L1\n\t- L2\n\t\t- [[Deep Note]]\n[[Top Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Deep Note", "Top Note"])

    def test_extract_wikilinks_preserves_parenthesized_ordered_list_context(self):
        markdown = "1) Parent\n    - [[Nested Note]]\n[[Top Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Nested Note", "Top Note"])

    def test_extract_wikilinks_ignores_list_contained_indented_code(self):
        markdown = "- item\n      [[Not real code]]\n[[Real]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real"])

    def test_extract_wikilinks_ignores_list_contained_indented_code_after_blank_line(self):
        markdown = "- Parent\n\n      [[Code Link]]\n[[Real]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real"])

    def test_extract_wikilinks_ignores_list_contained_tilde_fence(self):
        markdown = """- item
    ~~~markdown
    [[Not real tilde fence link]]
    ~~~
[[Real]]
"""
        self.assertEqual(extract_wikilinks(markdown), ["Real"])

    def test_extract_wikilinks_ignores_same_line_list_backtick_fence(self):
        markdown = """- ```markdown
  [[Leaked Link]]
  ```
[[Real Link]]
"""
        self.assertEqual(extract_wikilinks(markdown), ["Real Link"])

    def test_extract_wikilinks_ignores_same_line_list_tilde_fence(self):
        markdown = """- ~~~markdown
  [[Leaked Tilde Link]]
  ~~~
[[Real Link]]
"""
        self.assertEqual(extract_wikilinks(markdown), ["Real Link"])

    def test_same_line_list_backtick_fence_preserves_later_list_continuation(self):
        markdown = """- ```markdown
  [[Hidden]]
  ```
    [[Continuation Note]]
[[Top Note]]
"""
        self.assertEqual(extract_wikilinks(markdown), ["Continuation Note", "Top Note"])

    def test_same_line_list_tilde_fence_preserves_later_list_continuation(self):
        markdown = """- ~~~markdown
  [[Hidden]]
  ~~~
    [[Continuation Note]]
[[Top Note]]
"""
        self.assertEqual(extract_wikilinks(markdown), ["Continuation Note", "Top Note"])

    def test_same_line_list_backtick_fence_hides_later_continuation_fence(self):
        markdown = """- ```markdown
  [[Hidden 1]]
  ```
    ```markdown
    [[Hidden 2]]
    ```
[[Real]]
"""
        self.assertEqual(extract_wikilinks(markdown), ["Real"])

    def test_same_line_list_tilde_fence_hides_later_continuation_fence(self):
        markdown = """- ~~~markdown
  [[Hidden 1]]
  ~~~
    ~~~markdown
    [[Hidden 2]]
    ~~~
[[Real]]
"""
        self.assertEqual(extract_wikilinks(markdown), ["Real"])

    def test_standalone_indented_list_marker_backtick_fence_does_not_hide_structure(self):
        markdown = "    - ```markdown\n## Definition\n[[Real Note]]\n"
        self.assertEqual(extract_headings(markdown), ["Definition"])
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_standalone_tab_indented_list_marker_backtick_fence_does_not_hide_links(self):
        markdown = "\t- ```markdown\n[[Real Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_standalone_indented_list_marker_tilde_fence_does_not_hide_structure(self):
        markdown = "    - ~~~markdown\n## Definition\n[[Real Note]]\n"
        self.assertEqual(extract_headings(markdown), ["Definition"])
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_standalone_tab_indented_list_marker_tilde_fence_does_not_hide_links(self):
        markdown = "\t- ~~~markdown\n[[Real Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_extract_wikilinks_ignores_true_tab_indented_code(self):
        markdown = "\t[[Still not real]]\n[[Top Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Top Note"])

    def test_extract_wikilinks_ignores_standalone_space_indented_list_marker_code(self):
        markdown = "    - [[Not a real link]]\n[[Real Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_extract_wikilinks_ignores_standalone_tab_indented_list_marker_code(self):
        markdown = "\t- [[Not a real link]]\n[[Real Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_extract_wikilinks_ignores_mixed_space_tab_indented_code(self):
        markdown = " \t[[Mixed tab code]]\n[[Real Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_extract_wikilinks_ignores_mixed_space_tab_list_marker_code(self):
        markdown = " \t- [[Mixed tab list code]]\n[[Real Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_extract_wikilinks_ignores_broken_multiline_opener(self):
        markdown = "[[Broken\n[[Real Note]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_extract_headings_strips_optional_closing_hashes(self):
        self.assertEqual(extract_headings("## Definition ##\n"), ["Definition"])

    def test_has_dae_sections_is_case_insensitive(self):
        markdown = "## definition\n\n## ANALOGY\n\n## Example\n"
        self.assertTrue(has_dae_sections(markdown))

    def test_has_dae_sections_supports_closing_hashes(self):
        markdown = "## Definition ##\n\n## Analogy ##\n\n## Example ##\n"
        self.assertTrue(has_dae_sections(markdown))

    def test_has_dae_sections_returns_false_without_example(self):
        markdown = "## Definition\n\n## Analogy\n"
        self.assertFalse(has_dae_sections(markdown))

    def test_bare_heading_markers_do_not_consume_next_lines(self):
        markdown = "##\nDefinition\n##\nAnalogy\n##\nExample\n"
        headings = extract_headings(markdown)
        self.assertNotIn("Definition", headings)
        self.assertNotIn("Analogy", headings)
        self.assertNotIn("Example", headings)
        self.assertFalse(has_dae_sections(markdown))

    def test_indented_atx_headings_up_to_three_spaces_are_supported(self):
        markdown = "   ## Definition\n   ## Analogy\n   ## Example\n"
        self.assertEqual(extract_headings(markdown), ["Definition", "Analogy", "Example"])
        self.assertTrue(has_dae_sections(markdown))

    def test_four_space_indented_atx_markers_are_not_headings(self):
        markdown = "    ## Definition\n    ## Analogy\n    ## Example\n"
        self.assertEqual(extract_headings(markdown), [])
        self.assertFalse(has_dae_sections(markdown))

    def test_count_anki_blocks_counts_multiple_blocks(self):
        markdown = "START\nCard one\nEND\n\nSTART\nCard two\nEND\n"
        self.assertEqual(count_anki_blocks(markdown), {"START": 2, "END": 2})

    def test_count_anki_blocks_counts_malformed_blocks(self):
        markdown = "START\nCard without end\n"
        self.assertEqual(count_anki_blocks(markdown), {"START": 1, "END": 0})

    def test_fenced_code_block_contents_are_not_note_structure(self):
        markdown = """```markdown
## Definition
## Analogy
## Example
[[Not a real link]]
START
END
```
"""
        self.assertEqual(extract_headings(markdown), [])
        self.assertEqual(extract_wikilinks(markdown), [])
        self.assertEqual(count_anki_blocks(markdown), {"START": 0, "END": 0})
        self.assertFalse(has_dae_sections(markdown))

    def test_tilde_fenced_code_block_contents_are_not_note_structure(self):
        markdown = """~~~markdown
## Definition
[[Not a real link]]
START
END
~~~
"""
        self.assertEqual(extract_headings(markdown), [])
        self.assertEqual(extract_wikilinks(markdown), [])
        self.assertEqual(count_anki_blocks(markdown), {"START": 0, "END": 0})

    def test_html_comment_contents_are_not_note_structure(self):
        markdown = """<!--
## Definition
## Analogy
## Example
[[Hidden]]
START
END
-->
"""
        self.assertEqual(extract_headings(markdown), [])
        self.assertEqual(extract_wikilinks(markdown), [])
        self.assertEqual(count_anki_blocks(markdown), {"START": 0, "END": 0})
        self.assertFalse(has_dae_sections(markdown))

    def test_html_comment_opener_inside_fenced_code_does_not_hide_later_structure(self):
        markdown = """```markdown
<!--
```
## Definition
## Analogy
## Example
[[Outside Fence]]
-->
[[After Closer]]
"""
        self.assertEqual(extract_headings(markdown), ["Definition", "Analogy", "Example"])
        self.assertTrue(has_dae_sections(markdown))
        self.assertEqual(extract_wikilinks(markdown), ["Outside Fence", "After Closer"])

    def test_fence_inside_html_comment_does_not_hide_later_structure(self):
        markdown = """<!--
```markdown
[[Hidden]]
-->
## Definition
[[Real]]
"""
        self.assertEqual(extract_headings(markdown), ["Definition"])
        self.assertEqual(extract_wikilinks(markdown), ["Real"])

    def test_tab_indented_fence_marker_does_not_hide_later_structure(self):
        markdown = "\t```\n## Definition\n[[Real Note]]\n"
        self.assertEqual(extract_headings(markdown), ["Definition"])
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_real_note_structure_outside_fenced_blocks_still_works(self):
        markdown = """```markdown
## Not Real
[[Not Real]]
START
END
```

## Definition
Outside text linking to [[Atomic Note Quality]].

START
Basic
END
"""
        self.assertEqual(extract_headings(markdown), ["Definition"])
        self.assertEqual(extract_wikilinks(markdown), ["Atomic Note Quality"])
        self.assertEqual(count_anki_blocks(markdown), {"START": 1, "END": 1})

    def test_count_anki_blocks_ignores_inline_start_and_end_text(self):
        markdown = "This line mentions START inline.\nThis line mentions END inline.\n"
        self.assertEqual(count_anki_blocks(markdown), {"START": 0, "END": 0})

    def test_frontmatter_contents_are_not_note_structure(self):
        markdown = """---
# Definition
# Analogy
# Example
parent: [[Frontmatter Parent]]
---

# Body
"""
        self.assertFalse(has_dae_sections(markdown))
        self.assertEqual(extract_wikilinks(markdown), [])

    def test_body_structure_after_frontmatter_still_works(self):
        markdown = """---
title: Example
parent: [[Frontmatter Parent]]
---

## Definition
Definition text linking to [[Body Note]].

## Analogy
Analogy text.

## Example
Example text.
"""
        self.assertTrue(has_dae_sections(markdown))
        self.assertEqual(extract_wikilinks(markdown), ["Body Note"])

    def test_extract_wikilinks_ignores_inline_code_spans(self):
        markdown = "Ignore `[[Literal Example]]` but keep [[Real Note]].\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real Note"])

    def test_extract_wikilinks_ignores_long_inline_code_with_shorter_backticks(self):
        markdown = "Ignore ``[[Hidden]] ` literal`` keep [[Real]].\n"
        self.assertEqual(extract_wikilinks(markdown), ["Real"])

    def test_html_comment_opener_inside_inline_code_does_not_hide_later_links(self):
        markdown = "`<!--` [[Outside Inline]] --> [[After Closer]]\n"
        self.assertEqual(extract_wikilinks(markdown), ["Outside Inline", "After Closer"])

    def test_stray_inline_code_ticks_do_not_mask_note_structure_across_blocks(self):
        markdown = """`stray

## Definition
Definition.

## Analogy
Analogy.

## Example
Example.

[[Parent Note]]

`other
"""
        self.assertEqual(extract_headings(markdown), ["Definition", "Analogy", "Example"])
        self.assertEqual(extract_wikilinks(markdown), ["Parent Note"])
        self.assertTrue(has_dae_sections(markdown))


if __name__ == "__main__":
    unittest.main()
