import unittest

from shared.scripts.markdown_parse import (
    dae_section_paragraphs,
    dae_section_starts_lowercase,
    analyze_dae,
    count_rendered_words,
    count_anki_blocks,
    decayed_latex_commands,
    extract_frontmatter,
    extract_headings,
    extract_wikilinks,
    has_dae_sections,
    _dae_heading_sections,
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

    def test_has_dae_sections_returns_true_for_plain_prose_dae(self):
        markdown = """# Plain Prose Note

A plain prose note explains one durable idea in visible paragraphs so deterministic review can inspect the concept.

A plain prose note is like a labeled jar in a pantry: one container holds one kind of ingredient.

For example, a note about atomic-note quality defines the quality, compares it to a familiar label, and links a review hub.
"""
        self.assertTrue(has_dae_sections(markdown))

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

    def test_extract_wikilinks_preserves_inline_code_inside_target(self):
        self.assertEqual(
            extract_wikilinks("[[There are multiple ways to use a `for` statement]]"),
            ["There are multiple ways to use a `for` statement"],
        )

    def test_extract_wikilinks_ignores_links_inside_inline_code(self):
        self.assertEqual(
            extract_wikilinks("Ignore `[[Inline Code Link]]` but keep [[Real Link]]."),
            ["Real Link"],
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

    def test_extract_headings_supports_crlf_line_endings(self):
        markdown = "## Definition\r\n## Analogy\r\n## Example\r\n"
        self.assertEqual(extract_headings(markdown), ["Definition", "Analogy", "Example"])
        self.assertFalse(has_dae_sections(markdown))

    def test_heading_only_dae_is_not_an_accepted_dae_shape(self):
        markdown = "## definition\n\n## ANALOGY\n\n## Example\n"
        self.assertFalse(has_dae_sections(markdown))

    def test_heading_only_dae_with_closing_hashes_is_not_an_accepted_dae_shape(self):
        markdown = "## Definition ##\n\n## Analogy ##\n\n## Example ##\n"
        self.assertFalse(has_dae_sections(markdown))

    def test_analyze_dae_accepts_plain_prose_note_shape(self):
        markdown = """---
title: Plain Prose Note
---

# Plain Prose Note

A plain prose note explains one durable idea in visible paragraphs so deterministic review can inspect the concept.

A plain prose note is like a labeled jar in a pantry: one container holds one kind of ingredient.

For example, a note about atomic-note quality defines the quality, compares it to a familiar label, and links a review hub.
"""
        analysis = analyze_dae(markdown)

        self.assertTrue(analysis.present)
        self.assertEqual(analysis.shape, "plain-prose")
        self.assertEqual(analysis.definition_word_count, 18)
        self.assertEqual(analysis.analogy_word_count, 19)
        self.assertEqual(analysis.example_word_count, 21)

    def test_analyze_dae_plain_prose_requires_analogy(self):
        markdown = """# Plain Prose Note

A plain prose note explains one durable idea in visible paragraphs so deterministic review can inspect the concept.

This paragraph describes the concept again without mapping it to a familiar concrete referent.

For example, a note about atomic-note quality defines the quality, compares it to a familiar label, and links a review hub.
"""
        analysis = analyze_dae(markdown)

        self.assertFalse(analysis.present)
        self.assertFalse(analysis.has_analogy)
        self.assertTrue(analysis.has_example)

    def test_analyze_dae_plain_prose_requires_for_example_prefix(self):
        markdown = """# Plain Prose Note

A plain prose note explains one durable idea in visible paragraphs so deterministic review can inspect the concept.

A plain prose note is like a labeled jar in a pantry: one container holds one kind of ingredient.

One note about atomic-note quality defines the quality, compares it to a familiar label, and links a review hub.
"""
        analysis = analyze_dae(markdown)

        self.assertFalse(analysis.present)
        self.assertTrue(analysis.has_analogy)
        self.assertFalse(analysis.has_example)

    def test_analyze_dae_plain_prose_requires_distinct_analogy_and_example_paragraphs(self):
        markdown = """# Plain Prose Note

A plain prose note explains one durable idea in visible paragraphs so deterministic review can inspect the concept.

For example, a plain prose note is like a labeled jar with one kind of ingredient.
"""
        analysis = analyze_dae(markdown)

        self.assertFalse(analysis.present)
        self.assertFalse(analysis.has_analogy)
        self.assertTrue(analysis.has_example)

    def test_analyze_dae_flags_overlong_plain_prose_definition(self):
        markdown = """# Replication

Replication keeps matching copies of data across multiple machines, storage systems, or regions so a service can keep serving readers, survive hardware failure, place information closer to users, recover from disasters, compare versions during repair, continue operating while individual replicas are unavailable, and rebuild safely after an outage damages local storage.

Replication is like keeping the same emergency manual in several offices: each office can use its copy while updates spread.

For example, a streaming service can store a popular video in several regions so viewers can fetch it nearby.
"""
        analysis = analyze_dae(markdown)

        self.assertFalse(analysis.present)
        self.assertTrue(analysis.definition_too_long)

    def test_analyze_dae_rejects_heading_only_non_anki_shape(self):
        markdown = """# Heading DAE Note

## Definition

A heading note explains one durable idea with DAE headings that are no longer the accepted non-Anki shape.

## Analogy

A heading note is like a labeled jar with dividers inside it: the labels are visible, but the prose shape is not plain.

## Example

For example, this note has all three headings but should still fail non-Anki DAE validation.
"""
        analysis = analyze_dae(markdown)

        self.assertFalse(analysis.present)

    def test_analyze_dae_plain_prose_stops_before_trailing_labels(self):
        markdown = """# Plain Prose Note

A plain prose note explains one durable idea in visible paragraphs so deterministic review can inspect the concept.

A plain prose note is like a labeled jar in a pantry: one container holds one kind of ingredient.

Reference:

For example, this trailing reference prose should not count as the DAE example paragraph.
"""
        analysis = analyze_dae(markdown)

        self.assertFalse(analysis.present)
        self.assertFalse(analysis.has_example)

    def test_analyze_dae_plain_prose_ignores_start_inside_code_block(self):
        markdown = """# Plain Prose Note

```text
START
```

A plain prose note explains one durable idea in visible paragraphs so deterministic review can inspect the concept.

A plain prose note is like a labeled jar in a pantry: one container holds one kind of ingredient.

For example, a note about atomic-note quality defines the quality, compares it to a familiar label, and links a review hub.
"""
        analysis = analyze_dae(markdown)

        self.assertTrue(analysis.present)

    def test_analyze_dae_plain_prose_skips_target_deck_before_definition(self):
        markdown = """# Optional Card Note

TARGET DECK: General

A plain prose note explains one durable idea in visible paragraphs so deterministic review can inspect the concept.

A plain prose note is like a labeled jar in a pantry: one container holds one kind of ingredient.

For example, a note about atomic-note quality defines the quality, compares it to a familiar label, and links a review hub.

START
Basic
What does the note show?
Back: It shows one idea.
END
"""
        analysis = analyze_dae(markdown)

        self.assertTrue(analysis.present)
        self.assertEqual(analysis.shape, "plain-prose")
        self.assertEqual(analysis.definition_word_count, 18)

    def test_analyze_dae_accepts_reference_and_sources_sections(self):
        content = (
            "# Concept\n\n"
            "TARGET DECK: General\n\nSTART\n\nBasic\n\n"
            "What is the concept?\n\n"
            "Back: A concept is one clear idea stated plainly so it can be tested.\n\n"
            "It is like one labeled jar in a pantry.\n\n"
            "For example, a note names the idea and shows a concrete case.\n\n"
            "END\n\n"
            "Reference:\n- Related: [[Atomic Note Quality]].\n\n"
            "Sources:\n1. Synthetic source.\n"
        )
        analysis = analyze_dae(content)
        self.assertTrue(analysis.present)

    def test_analyze_dae_accepts_basic_card_shape(self):
        markdown = """---
title: Stateless Protocol
---

# Stateless Protocol

START
Basic
What is a stateless protocol?

Back: A stateless protocol treats each transaction independently and does not retain session information from previous interactions.

A stateless protocol is like a vending machine: each purchase starts fresh without memory of previous purchases.

For example, HTTP processes each browser request without remembering which pages that browser previously requested.
<!--ID: 1-->
END

Sources:

1. Synthetic source.
"""
        analysis = analyze_dae(markdown)

        self.assertTrue(analysis.present)
        self.assertEqual(analysis.shape, "Basic")
        self.assertFalse(analysis.definition_too_long)

    def test_analyze_dae_counts_wikilink_aliases_as_rendered_words(self):
        markdown = """START
Basic
What is eventual consistency?
Back: Eventual consistency is a [[202201191901 Long note title|consistency]] guarantee where replicas in a [[202212171827 Long distributed title|distributed system]] temporarily diverge before converging after writes stop.

Eventual consistency is like ripples spreading across a pond: close areas change first, while distant areas settle later.

For example, Twitter followers in New York might see a post seconds before followers in Tokyo during replication lag.
END
"""
        analysis = analyze_dae(markdown)

        self.assertTrue(analysis.present)
        self.assertEqual(analysis.definition_word_count, 19)
        self.assertEqual(count_rendered_words("[[202201010101 Very long target|short alias]]"), 2)

    def test_analyze_dae_flags_overlong_basic_definition(self):
        markdown = """START
Basic
What is replication?
Back: Replication is the process of maintaining identical copies of data across multiple servers or storage devices, with synchronization mechanisms ensuring changes propagate to all replicas. This technique serves multiple purposes including fault tolerance, improved read performance, reduced latency by placing data closer to users, disaster recovery, regional availability, and operational resilience during hardware failures or network outages.

Replication is like a library maintaining identical books at several branches: each branch can serve readers while updates spread.

For example, a streaming service stores popular shows in multiple regions so viewers in different cities can stream from nearby replicas.
END
"""
        analysis = analyze_dae(markdown)

        self.assertFalse(analysis.present)
        self.assertTrue(analysis.definition_too_long)

    def test_analyze_dae_accepts_cloze_extra_shape(self):
        markdown = """START
Cloze
The CAP theorem states that a distributed data system can only guarantee two out of three properties simultaneously:

1. {{c1::Consistency}}: All nodes see the same data.
2. {{c2::Availability}}: Every request receives a response.
3. {{c3::Partition tolerance}}: The system continues through network failures.

Extra: This can be compared to note-takers in separate rooms: they can keep identical notes or keep writing while separated, but not both.

For example, during a network partition, one database may stay available with temporary inconsistency while another may reject some requests to preserve consistency.
END
"""
        analysis = analyze_dae(markdown)

        self.assertTrue(analysis.present)
        self.assertEqual(analysis.shape, "Cloze")

    def test_dae_sentence_case_flags_lowercase_analogy_alias(self):
        markdown = """# Creatine

Creatine helps muscles regenerate adenosine triphosphate during short bursts of work.

[[202411271638 Creatine is a naturally occurring compound|creatine]] is like a backup power generator for muscles.

For example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.
"""
        self.assertTrue(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_analogy_accepts_capitalized_wikilink_alias(self):
        markdown = """# Noise

Noise in data hides the underlying pattern a model is trying to learn.

[[202312261341 Noise refers to random variation|Noise]] is like a blurry lens on a camera.

For example, sensor jitter can hide a slow temperature trend in a lab log.
"""
        self.assertFalse(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_analogy_allows_leading_inline_math(self):
        markdown = """# Sample size

Sample size n is the number of independent observations in a dataset.

$n$ is like the number of survey responses because each independent response adds evidence.

For example, a poll of 1,000 voters has more stable estimates than a poll of 40 voters.
"""
        self.assertFalse(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_analogy_allows_emphasized_inline_math(self):
        markdown = """# Sample size

Sample size n is the number of independent observations in a dataset.

**$n$** is like the number of survey responses because each independent response adds evidence.

For example, a poll of 1,000 voters has more stable estimates than a poll of 40 voters.
"""
        self.assertFalse(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_analogy_flags_unclosed_leading_dollar(self):
        markdown = """# Creatine

Creatine helps muscles regenerate adenosine triphosphate during short bursts of work.

$creatine is like a backup power generator for muscles.

For example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.
"""
        self.assertTrue(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_analogy_ignores_leading_html_tags(self):
        markdown = """# Capital

Capital is money used to produce more value.

<span>Capital</span> is like seed grain saved to plant next season's crop.

For example, a baker spends cash on an oven that later bakes more loaves.
"""
        self.assertFalse(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_analogy_flags_lowercase_after_html_tags(self):
        markdown = """# Capital

Capital is money used to produce more value.

<span>capital</span> is like seed grain saved to plant next season's crop.

For example, a baker spends cash on an oven that later bakes more loaves.
"""
        self.assertTrue(dae_section_starts_lowercase(markdown))

    def test_anki_basic_labels_lowercase_example_as_example_not_analogy(self):
        markdown = """# Creatine

Creatine helps muscles regenerate adenosine triphosphate during short bursts of work.

Creatine is like a backup power generator for muscles.

For example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.

START
Basic
How does creatine help muscles?

Back: Creatine helps muscles regenerate adenosine triphosphate during short bursts of work.

Creatine is like a backup power generator for muscles.

for example, a sprinter is like a car that taps a small battery for a 10-second start.
END
"""
        lowercase = [
            section
            for section, paragraph in dae_section_paragraphs(markdown)
            if paragraph.lstrip().startswith("for example,")
        ]
        self.assertEqual(lowercase, ["example"])
        self.assertTrue(dae_section_starts_lowercase(markdown))

    def test_anki_cloze_extra_labels_lowercase_example_as_example_not_analogy(self):
        markdown = """# Creatine

Creatine helps muscles regenerate adenosine triphosphate during short bursts of work.

Creatine is like a backup power generator for muscles.

For example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.

START
Cloze
{{c1::Creatine}} helps muscles regenerate adenosine triphosphate during short bursts of work.

Extra: Creatine is like a backup power generator for muscles.

for example, a sprinter is like a car that taps a small battery for a 10-second start.
END
"""
        lowercase = [
            section
            for section, paragraph in dae_section_paragraphs(markdown)
            if paragraph.lstrip().startswith("for example,")
        ]
        self.assertEqual(lowercase, ["example"])
        self.assertTrue(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_flags_lowercase_definition_alias(self):
        markdown = """# Creatine

[[202411271638 Creatine is a naturally occurring compound|creatine]] is a compound that helps muscles regenerate adenosine triphosphate.

Creatine is like a backup power generator for muscles.

For example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.
"""
        self.assertTrue(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_flags_lowercase_example(self):
        markdown = """# Creatine

Creatine helps muscles regenerate adenosine triphosphate during short bursts of work.

Creatine is like a backup power generator for muscles.

for example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.
"""
        self.assertTrue(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_checks_cloze_definition(self):
        template = """# Creatine

START
Cloze
{deletion} helps muscles regenerate adenosine triphosphate during short bursts of work.

Extra: Creatine is like a backup power generator for muscles.

For example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.
END
"""
        self.assertTrue(dae_section_starts_lowercase(template.format(deletion="{{c1::creatine}}")))
        self.assertFalse(dae_section_starts_lowercase(template.format(deletion="{{c1::Creatine::hint}}")))
        self.assertFalse(dae_section_starts_lowercase(template.format(deletion="{{c1::$n$}}")))

    def test_dae_sentence_case_checks_cloze_definition_without_extra(self):
        markdown = """# Creatine

START
Cloze
{{c1::creatine}} helps muscles regenerate adenosine triphosphate during short bursts of work.
END
"""
        self.assertTrue(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_reads_headed_section_bodies_not_heading_lines(self):
        template = """# Creatine

## Definition

{definition} helps muscles regenerate adenosine triphosphate during short bursts of work.

## Analogy

Creatine is like a backup power generator for muscles.

## Example

For example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.
"""
        self.assertTrue(dae_section_starts_lowercase(template.format(definition="creatine")))
        clean = template.format(definition="Creatine")
        self.assertFalse(dae_section_starts_lowercase(clean))
        self.assertEqual(
            [section for section, _ in dae_section_paragraphs(clean)],
            ["definition", "analogy", "example"],
        )

    def test_dae_sentence_case_flags_lowercase_back_definition_when_prose_is_capitalized(self):
        markdown = """# Creatine

Creatine helps muscles regenerate adenosine triphosphate during short bursts of work.

Creatine is like a backup power generator for muscles.

For example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.

START
Basic
How does creatine help muscles?

Back: creatine helps muscles regenerate adenosine triphosphate during short bursts of work.

Creatine is like a backup power generator for muscles.

For example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.
END
"""
        self.assertTrue(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_clean_openers_in_definition_and_example(self):
        for opener in (
            "[[202312261341 Noise refers to random variation|Noise]]",
            "$n$",
            "**$n$**",
            "<span>Capital</span>",
        ):
            markdown = f"""# Term

{opener} is the quantity a model is trying to estimate from data.

Noise is like a blurry lens on a camera.

For example, sensor jitter can hide a slow temperature trend in a lab log.
"""
            with self.subTest(opener=opener):
                self.assertFalse(dae_section_starts_lowercase(markdown))

    def test_dae_sentence_case_exempts_mixed_case_first_word(self):
        template = """# Term

{definition} a widely used tool in its field.

{analogy} is like a shared phone line between two offices.

For example, a service can call another service as if it were a local function.
"""
        for word in ("gRPC is", "pH is", "iOS is", "[[202401011200 Messenger RNA carries instructions|mRNA]] is"):
            with self.subTest(word=word):
                self.assertFalse(
                    dae_section_starts_lowercase(template.format(definition=word, analogy=word.rsplit(" ", 1)[0]))
                )
        for word in ("curl is", "k-means is", "e.g. this is"):
            with self.subTest(word=word):
                self.assertTrue(
                    dae_section_starts_lowercase(template.format(definition=word, analogy="Term"))
                )

    def test_dae_sentence_case_exempts_leading_inline_code(self):
        template = """# Range

The range function generates a sequence of integers one at a time.

{analogy} is like a ticket dispenser that hands out the next number on request.

For example, a loop over ten items asks for each index only when it needs it.
"""
        for opener in ("`range`", "**`range`**", "`.join()`"):
            with self.subTest(opener=opener):
                self.assertFalse(dae_section_starts_lowercase(template.format(analogy=opener)))
        for opener in ("`range is", "range"):
            with self.subTest(opener=opener):
                self.assertTrue(dae_section_starts_lowercase(template.format(analogy=opener)))

    def test_dae_sentence_case_exempts_leading_multi_backtick_inline_code(self):
        template = """# Range

The range function generates a sequence of integers one at a time.

{analogy} is like a ticket dispenser that hands out the next number on request.

For example, a loop over ten items asks for each index only when it needs it.
"""
        for opener in ("``range``", "``a `b` c``", "**``range``**", "```range```"):
            with self.subTest(opener=opener):
                self.assertFalse(dae_section_starts_lowercase(template.format(analogy=opener)))
        # An unclosed run is not a code span, so the first word is still judged.
        for opener in ("``range", "``range`"):
            with self.subTest(opener=opener):
                self.assertTrue(dae_section_starts_lowercase(template.format(analogy=opener)))

    def test_dae_sentence_case_skips_non_prose_openers_in_headed_sections(self):
        template = """# Creatine

## Definition

#topic/supplements

{definition} helps muscles regenerate adenosine triphosphate during short bursts of work.

## Analogy

> [!note]
> Kept for reviewers.

Creatine is like a backup power generator for muscles.

## Example

![[creatine-chart.png]]

For example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.
"""
        clean = template.format(definition="Creatine")
        self.assertFalse(dae_section_starts_lowercase(clean))
        self.assertEqual(
            [paragraph.split(None, 1)[0] for _, paragraph in dae_section_paragraphs(clean)],
            ["Creatine", "Creatine", "For"],
        )
        self.assertTrue(dae_section_starts_lowercase(template.format(definition="creatine")))

    def test_dae_sentence_case_skips_non_prose_openers_in_cloze_body(self):
        template = """# Creatine

START
Cloze
{opener}

{deletion} helps muscles regenerate adenosine triphosphate during short bursts of work.

Extra: Creatine is like a backup power generator for muscles.

For example, a sprinter can use stored phosphocreatine to recharge ATP during a 10-second start.
END
"""
        openers = (
            "#topic/supplements",
            "up:: [[Supplements]]",
            "> [!note]\n> Kept for reviewers.",
            "| Dose | 5 g |",
            "- Kept for reviewers.",
        )
        for opener in openers:
            with self.subTest(opener=opener):
                # A non-prose line above the Definition is not the Definition, so it
                # neither earns a finding of its own nor hides a lowercase Definition.
                self.assertFalse(
                    dae_section_starts_lowercase(
                        template.format(opener=opener, deletion="{{c1::Creatine::hint}}")
                    )
                )
                self.assertTrue(
                    dae_section_starts_lowercase(
                        template.format(opener=opener, deletion="{{c1::creatine}}")
                    )
                )
        clean = template.format(opener="#topic/supplements", deletion="{{c1::Creatine::hint}}")
        self.assertEqual(
            [(section, paragraph.split(None, 1)[0]) for section, paragraph in dae_section_paragraphs(clean)],
            [("definition", "{{c1::Creatine::hint}}"), ("analogy", "Creatine"), ("example", "For")],
        )

    def test_dae_sentence_case_ignores_numeral_and_url_openers(self):
        template = """# Term

{definition} the thing a reader looks up when a page cannot be found.

Term is like a wrong street address on an envelope.

For example, a typo in a link sends the browser to a page that does not exist.
"""
        for opener in ("404 is", "80/20 thinking is", "https://example.com is"):
            with self.subTest(opener=opener):
                self.assertFalse(dae_section_starts_lowercase(template.format(definition=opener)))
        for opener in ("the 404 status is", "(a) status is"):
            with self.subTest(opener=opener):
                self.assertTrue(dae_section_starts_lowercase(template.format(definition=opener)))

    def test_dae_section_paragraphs_empty_without_dae(self):
        self.assertEqual(dae_section_paragraphs("# Title\n"), [])
        self.assertFalse(dae_section_starts_lowercase("# Title\n"))

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
        self.assertFalse(has_dae_sections(markdown))

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
        self.assertFalse(has_dae_sections(markdown))
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
        self.assertFalse(has_dae_sections(markdown))
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
        self.assertFalse(has_dae_sections(markdown))


class DaeHeadingSectionsTest(unittest.TestCase):
    def test_trailing_reference_and_sources_labels_excluded_from_example_section(self):
        # Bug 1: Reference:/Sources: plain labels (not ## headings) must NOT be
        # included in the example section word count; they are trailing markers.
        md = (
            "---\ntags:\n  - atomic-note\n---\n\n"
            "# My Note\n\n"
            "## Definition\n\n"
            "A concept is one clear idea.\n\n"
            "## Analogy\n\n"
            "It is like a labeled jar.\n\n"
            "## Example\n\n"
            "For example, a concept applies here.\n\n"
            "Reference:\n"
            "- [[Related]]\n\n"
            "Sources:\n"
            "1. A source.\n"
        )
        sections = _dae_heading_sections(md)
        self.assertEqual(sections.get("example"), "For example, a concept applies here.")


TAB = "\t"

# The six tab-borne decayed forms, each inside an inline math span. The
# seventh form is newline-borne and cannot sit inside one line, so it has its
# own tests.
DECAYED_INLINE_SPANS = (
    (r"\times", "$2 " + TAB + "imes 3$"),
    (r"\text", "$" + TAB + "ext{kg}$"),
    (r"\tfrac", "$" + TAB + "frac{1}{2}$"),
    (r"\theta", "$" + TAB + "heta$"),
    (r"\to", "$x " + TAB + "o y$"),
    (r"\tan", "$" + TAB + "an x$"),
)

CORRECT_INLINE_SPANS = (
    "$2 \\times 3$",
    "$\\text{kg}$",
    "$\\tfrac{1}{2}$",
    "$\\theta$",
    "$x \\to y$",
    "$\\tan x$",
    "$a \\neq b$",
)


class DecayedLatexCommandsTest(unittest.TestCase):
    # A decoder turned the backslash escape into the character it denotes, so
    # `\times` reaches disk as TAB + "imes" and `\neq` as a line break + "eq".
    # Fixtures build that shape explicitly rather than relying on Python's own
    # escape decoding, so the control character is visible in the source.

    def test_tab_before_imes_inside_inline_math_names_times(self):
        markdown = "# Note\n\nThe area is $2 " + TAB + "imes 3$ square units.\n"
        self.assertEqual(decayed_latex_commands(markdown), [r"\times"])

    def test_correct_times_command_in_same_position_does_not_match(self):
        markdown = "# Note\n\nThe area is $2 \\times 3$ square units.\n"
        self.assertEqual(decayed_latex_commands(markdown), [])

    def test_open_inline_math_split_across_lines_names_neq(self):
        markdown = "\n".join(
            [
                "# Note",
                "",
                "The bound holds while $a ",
                "eq b$ for every pair.",
                "",
            ]
        )
        self.assertEqual(decayed_latex_commands(markdown), [r"\neq"])

    def test_control_character_adjacent_to_math_span_matches(self):
        markdown = "# Note\n\nThe product $a$ " + TAB + "imes $b$ grows.\n"
        self.assertEqual(decayed_latex_commands(markdown), [r"\times"])

    def test_tab_inside_fenced_code_block_does_not_match(self):
        markdown = (
            "# Note\n\n```text\nrate" + TAB + "imes 3\n```\n\nPlain prose.\n"
        )
        self.assertEqual(decayed_latex_commands(markdown), [])

    def test_tab_inside_table_cell_does_not_match(self):
        markdown = (
            "# Note\n\n"
            "| Term | Value |\n"
            "| --- | --- |\n"
            "| speed | 3" + TAB + "imes 4 |\n"
        )
        self.assertEqual(decayed_latex_commands(markdown), [])

    def test_tab_followed_by_letter_does_not_match(self):
        markdown = (
            "# Note\n\nDisplay $x " + TAB + "overline{y}$ and $p " + TAB + "answer$.\n"
        )
        self.assertEqual(decayed_latex_commands(markdown), [])

    def test_line_beginning_with_equation_does_not_match(self):
        markdown = "\n".join(
            [
                "# Note",
                "",
                "The bound holds for every pair.",
                "equation 4 states the same thing.",
                "",
            ]
        )
        self.assertEqual(decayed_latex_commands(markdown), [])

    def test_tab_before_ext_inside_anki_back_block_matches(self):
        markdown = (
            "# Note\n\n"
            "Clean prose with no corruption at all.\n\n"
            "START\n"
            "Basic\n"
            "Front: What carries the unit?\n"
            "Back: The mass is $5 " + TAB + "ext{kg}$ exactly.\n"
            "END\n"
        )
        self.assertEqual(decayed_latex_commands(markdown), [r"\text"])

    def test_display_math_line_beginning_with_tab_names_tfrac(self):
        markdown = "\n".join(
            [
                "# Note",
                "",
                "$$",
                TAB + "frac{a}{b} + 1",
                "$$",
                "",
            ]
        )
        self.assertEqual(decayed_latex_commands(markdown), [r"\tfrac"])

    def test_display_math_line_beginning_with_space_then_tab_matches(self):
        markdown = "\n".join(
            [
                "# Note",
                "",
                "$$",
                " " + TAB + "ext{total} = 5",
                "$$",
                "",
            ]
        )
        self.assertEqual(decayed_latex_commands(markdown), [r"\text"])

    def test_space_then_tab_indented_line_outside_math_does_not_match(self):
        # The partner of the test above it: outside display math a line whose
        # tab follows a space is still indented code, so a tab-only reading of
        # the indent would report it.
        markdown = "\n".join(
            [
                "# Note",
                "",
                "Example code:",
                "",
                " " + TAB + "ext{total} = 5",
                "",
            ]
        )
        self.assertEqual(decayed_latex_commands(markdown), [])

    def test_tab_indented_line_outside_math_does_not_match(self):
        markdown = "\n".join(
            [
                "# Note",
                "",
                "Example code:",
                "",
                TAB + "an = compute(3)",
                "",
            ]
        )
        self.assertEqual(decayed_latex_commands(markdown), [])

    def test_prose_dollars_do_not_silence_a_later_display_block(self):
        # `$$$` carries an odd count of `$$`, so reading display math by parity
        # leaves the real block below it closed and the corruption unreported.
        markdown = "\n".join(
            [
                "# Note",
                "",
                "Price tiers run from $ to $$$ in the guide.",
                "",
                "$$",
                TAB + "frac{a}{b} + 1",
                "$$",
                "",
            ]
        )
        self.assertEqual(decayed_latex_commands(markdown), [r"\tfrac"])

    def test_prose_dollars_do_not_open_math_over_a_later_indented_line(self):
        # The same parity inversion the other way: indented code after the
        # prose reads as display math and its tab reports a command.
        markdown = "\n".join(
            [
                "# Note",
                "",
                "Price tiers run from $ to $$$ in the guide.",
                "",
                "Example code:",
                "",
                TAB + "an = compute(3)",
                "",
            ]
        )
        self.assertEqual(decayed_latex_commands(markdown), [])

    def test_prose_beginning_with_eq_and_a_period_does_not_match(self):
        # Nothing opened a math span, so `eq.` here is ordinary prose rather
        # than the tail of an equation broken across a line.
        markdown = "\n".join(
            [
                "# Note",
                "",
                "The bound holds for every pair.",
                "eq. 3 shows the result.",
                "",
            ]
        )
        self.assertEqual(decayed_latex_commands(markdown), [])

    def test_note_with_two_decayed_commands_returns_both(self):
        markdown = (
            "# Note\n\n"
            "We have $2 " + TAB + "imes 3$ and the angle $" + TAB + "heta$ is fixed.\n"
        )
        self.assertEqual(decayed_latex_commands(markdown), [r"\theta", r"\times"])

    def test_every_decayed_form_is_detected(self):
        for command, span in DECAYED_INLINE_SPANS:
            with self.subTest(command=command):
                markdown = "# Note\n\nThe value " + span + " holds.\n"
                self.assertEqual(decayed_latex_commands(markdown), [command])

    def test_every_correct_spelling_is_left_alone(self):
        for span in CORRECT_INLINE_SPANS:
            with self.subTest(span=span):
                markdown = "# Note\n\nThe value " + span + " holds.\n"
                self.assertEqual(decayed_latex_commands(markdown), [])

    def test_newline_borne_form_survives_alongside_a_tab_borne_form(self):
        markdown = "\n".join(
            [
                "# Note",
                "",
                "The angle $" + TAB + "heta$ satisfies $a ",
                "eq b$ throughout.",
                "",
            ]
        )
        self.assertEqual(decayed_latex_commands(markdown), [r"\neq", r"\theta"])


if __name__ == "__main__":
    unittest.main()
