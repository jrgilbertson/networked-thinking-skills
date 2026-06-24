import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from shared.scripts.audit_engine import audit_vault, _factual_risk_sentences
from shared.scripts.schema_validation import validate_audit_row


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_VAULT = REPO_ROOT / "tests" / "fixtures" / "tiny-vault"
VALID_DAE_MARKDOWN = """---
aliases: []
title: Test Note
---

# Test Note

START
Basic
Front: What does this test note represent?

Back: A test note represents one small idea with enough context to check audit behavior.

A test note is like a labeled shelf: it gives one item a clear place where a reader can find it.

For example, an audit test can create a temporary note called Test Note and link it from a temporary structure note.
END
"""


def rows_by_stem(rows):
    return {Path(row["note_path"]).stem: row for row in rows}


def finding_codes(row):
    return {finding["code"] for finding in row["findings"]}


class AuditEngineTest(unittest.TestCase):
    def test_audit_vault_scores_every_atomic_note(self):
        rows, manifest = audit_vault(FIXTURE_VAULT, run_id="test-run")

        self.assertEqual(len(rows), 10)
        self.assertEqual(manifest["total_notes"], 10)
        for row in rows:
            validate_audit_row(row, default_scan=True)
            self.assertEqual(row["row_status"], "complete")
            self.assertFalse(row["pending_model"])
            self.assertIsNone(row["model_judgment"])

    def test_structure_parent_match_preserves_periods_in_note_title(self):
        row = self.audit_single_note(
            VALID_DAE_MARKDOWN,
            stem="202601010110 A dotted title has one sentence. A second sentence stays in the title",
        )

        self.assertNotIn("missing_parent", finding_codes(row))

    def test_structure_parent_match_preserves_backticks_in_note_title(self):
        row = self.audit_single_note(
            VALID_DAE_MARKDOWN,
            stem="202601010111 There are multiple ways to use a `for` statement",
        )

        self.assertNotIn("missing_parent", finding_codes(row))

    def test_multi_note_bundle_scores_into_p0(self):
        rows, _ = audit_vault(FIXTURE_VAULT, run_id="test-run")
        row = rows_by_stem(rows)["202601010103 Multi note bundle"]

        self.assertEqual(row["priority"], "P0")
        self.assertLessEqual(row["score"], 49)
        self.assertIn("multi_note", {finding["code"] for finding in row["findings"]})

    def test_clean_dae_note_is_clean(self):
        rows, _ = audit_vault(FIXTURE_VAULT, run_id="test-run")
        row = rows_by_stem(rows)["202601010101 Clean DAE note"]

        self.assertTrue(row["clean"])
        self.assertGreaterEqual(row["score"], 90)

    def test_content_hash_uses_normalized_note_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            atomic_folder = vault / "Atomic Notes"
            structure_folder = vault / "Structure Notes"
            atomic_folder.mkdir()
            structure_folder.mkdir()
            stem = "202601010201 CRLF Note"
            note_path = atomic_folder / f"{stem}.md"
            note_path.write_bytes(VALID_DAE_MARKDOWN.replace("\n", "\r\n").encode("utf-8"))
            (structure_folder / "Atomic Note Quality.md").write_text(f"- [[{stem}]]\n", encoding="utf-8")

            rows, _ = audit_vault(vault, run_id="crlf-test")
            expected_hash = hashlib.sha256(note_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()

        self.assertEqual(rows[0]["content_hash"], expected_hash)

    def test_factual_risk_note_requires_fact_check(self):
        rows, _ = audit_vault(FIXTURE_VAULT, run_id="test-run")
        row = rows_by_stem(rows)["202601010106 Factual risk note"]

        self.assertTrue(row["factual_risk"])
        self.assertTrue(row["fact_check_required"])
        self.assertIn("factual_risk", {finding["code"] for finding in row["findings"]})

    def test_formal_math_definition_does_not_trigger_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - zero exponent rule
---

# Zero Exponent Rule

START
Basic
What is the zero exponent rule?

Back: The zero exponent rule states that any nonzero base raised to the power of zero is equal to one.

The zero exponent rule is like resetting a scale to neutral: no matter the starting nonzero base, the exponent zero returns the multiplicative identity.

For example, $5^0 = 1$, 7^0 = 1, and (-3)^0 = 1.
END
""",
            stem="202601010206 Zero Exponent Rule",
        )

        self.assertFalse(row["factual_risk"])
        self.assertNotIn("factual_risk", {finding["code"] for finding in row["findings"]})

    def test_formal_system_definition_does_not_trigger_factual_risk_from_quantifiers(self):
        row = self.audit_single_note(
            """---
aliases:
  - CAP theorem
---

# CAP Theorem

START
Cloze
The CAP theorem states that a distributed data system can only guarantee two out of three properties simultaneously:

1. {{c1::Consistency}}: All nodes see the same data.
2. {{c2::Availability}}: Every request receives a response.
3. {{c3::Partition tolerance}}: The system continues through network failures.

Extra: This can be compared to note-takers in separate rooms: they can keep identical notes or keep writing while separated, but not both.

For example, during a network partition, a distributed database must choose whether to keep serving requests with possible inconsistency or reject some requests to preserve consistency.
END
""",
            stem="202601010207 CAP Theorem Formal",
        )

        self.assertFalse(row["factual_risk"])

    def test_sampling_definition_quantifiers_do_not_trigger_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - simple random sample
---

# Simple Random Sample

TARGET DECK: General

START
Basic
What is a simple random sample?

Back: Simple random sampling gives every population member and every same-size subset an equal chance of selection.

Simple random sampling is like drawing names from a well-shuffled hat. No name or group of names gets a special path into the sample.

For example, a school with 1,000 students could assign each student a number and use a random-number generator to select 100 students, giving every group of 100 students the same selection chance.
<!--ID: 1-->
END
""",
            stem="202601010208 Simple Random Sample",
        )

        self.assertFalse(row["factual_risk"])
        self.assertNotIn("factual_risk", finding_codes(row))

    def test_sampling_group_quantifier_without_number_does_not_trigger_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - stratified group sample
---

# Stratified Group Sample

TARGET DECK: General

START
Basic
What is a stratified group sample?

Back: A stratified group sample selects groups from strata so each category is represented.

Stratified group sampling is like choosing shelves from each aisle before checking the books on those shelves.

For example, a school could sample classrooms from each grade, giving every group of students the same selection chance.
<!--ID: 1-->
END
""",
            stem="202601010218 Stratified Group Sample",
        )

        self.assertFalse(row["factual_risk"])
        self.assertNotIn("factual_risk", finding_codes(row))

    def test_sampling_direct_human_quantifier_does_not_trigger_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - student sampling chance
---

# Student Sampling Chance

TARGET DECK: General

START
Basic
What is equal selection chance?

Back: Equal selection chance means each eligible unit has the same probability of being selected.

Equal selection chance is like giving every ticket in a drawing the same weight.

For example, every student receives the same selection chance.
<!--ID: 1-->
END
""",
            stem="202601010225 Student Sampling Chance",
        )

        self.assertFalse(row["factual_risk"])
        self.assertNotIn("factual_risk", finding_codes(row))

    def test_sampling_everyone_selection_chance_does_not_trigger_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - everyone sampling chance
---

# Everyone Sampling Chance

TARGET DECK: General

START
Basic
What is equal selection chance?

Back: Equal selection chance means each eligible unit has the same probability of being selected.

Equal selection chance is like giving every ticket in a drawing the same weight.

For example, everyone receives the same selection chance.
<!--ID: 1-->
END
""",
            stem="202601010232 Everyone Sampling Chance",
        )

        self.assertFalse(row["factual_risk"])
        self.assertNotIn("factual_risk", finding_codes(row))

    def test_named_product_claim_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - CAP product example
---

# CAP Product Example

## Definition

A product-specific CAP classification maps a database product to a CAP tradeoff claim.

## Analogy

It is like labeling a tool by the job it usually performs: the label depends on the real tool's behavior.

## Example

For example, ExampleDB in its default configuration is a CP system, while ArchiveStore is an AP system.
""",
            stem="202601010208 CAP Product Example",
        )

        self.assertTrue(row["factual_risk"])

    def test_study_word_in_definition_does_not_trigger_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - dependent variable
---

# Dependent Variable

## Definition

A dependent variable is the factor in an experiment or study that is being tested and measured.

## Analogy

It is like a scoreboard in a game: it records the result affected by what players do.

## Example

For example, in a clinical trial, the dependent variable could be the patient's symptom score after receiving a treatment.
""",
            stem="202601010211 Dependent Variable",
        )

        self.assertFalse(row["factual_risk"])

    def test_domain_show_verb_does_not_trigger_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - class diagram
---

# Class Diagram

## Definition

A class diagram shows software classes and the structural relationships between them.

## Analogy

A class diagram is like an org chart for code: it shows the main units and how they relate without showing every runtime event.

## Example

For example, a payment service class diagram can show an InvoiceService depending on a PaymentGateway and InvoiceRepository.
""",
            stem="202601010212 Class Diagram",
        )

        self.assertFalse(row["factual_risk"])

    def test_quantified_research_claim_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - spaced repetition effect
---

# Spaced Repetition Effect

## Definition

Spaced repetition is a study schedule that reviews material after increasing intervals.

## Analogy

It is like watering a plant before the soil dries out: each timed return sustains the system.

## Example

For example, research found that spaced repetition improved retention by 40% after 30 days.
""",
            stem="202601010209 Spaced Repetition Effect",
        )

        self.assertTrue(row["factual_risk"])

    def test_trial_result_claim_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - retrieval practice effect
---

# Retrieval Practice Effect

## Definition

Retrieval practice is a study method that asks learners to recall information from memory.

## Analogy

It is like checking whether a trail is still visible by walking it again instead of looking at a map.

## Example

A classroom trial showed retrieval practice improved retention compared with restudying.
""",
            stem="202601010215 Retrieval Practice Effect",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_plural_trial_show_claim_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - retrieval practice evidence
---

# Retrieval Practice Evidence

## Definition

Retrieval practice evidence is a claim about how recall exercises affect later memory.

## Analogy

It is like checking a bridge by crossing it instead of only reading the blueprint.

## Example

Trials show retrieval practice improved retention compared with restudying.
""",
            stem="202601010216 Retrieval Practice Evidence",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_numeric_example_claim_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - checkout completion rate
---

# Checkout Completion Rate

## Definition

A checkout completion rate measures the share of started checkout sessions that finish with an order.

## Analogy

It is like counting how many people who enter a checkout lane leave with a receipt.

## Example

For example, an A/B test had a 97% completion rate after the redesign.
""",
            stem="202601010214 Checkout Completion Rate",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_currency_example_claim_triggers_factual_risk(self):
        examples = {
            "202601010234 Monthly Tool Price": "For example, the tool costs $25 per month.",
            "202601010235 Annual Tool Price": "For example, the tool costs $120 per year.",
            "202601010236 Decimal Tool Price": "For example, the tool costs $12.50 per user.",
        }
        for stem, example in examples.items():
            with self.subTest(stem=stem):
                row = self.audit_single_note(
                    f"""---
aliases: []
---

# {stem[13:]}

## Definition

A tool price claim states the cost of a software service.

## Analogy

It is like reading a price tag before deciding whether to buy a tool.

## Example

{example}
""",
                    stem=stem,
                )

                self.assertTrue(row["factual_risk"])
                self.assertIn("factual_risk", finding_codes(row))

    def test_benchmark_attribution_claim_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - cache benchmark claim
---

# Cache Benchmark Claim

## Definition

A cache benchmark claim states that a measured test supports a performance result.

## Analogy

It is like timing two routes before choosing the faster one.

## Example

A benchmark shows the cache improves latency.
""",
            stem="202601010237 Cache Benchmark Claim",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_review_attribution_claim_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - retrieval practice review claim
---

# Retrieval Practice Review Claim

## Definition

A retrieval practice review claim states that summarized evidence supports a retention result.

## Analogy

It is like reading a field report before deciding which study habit to use.

## Example

A systematic review shows retrieval practice improves retention.
""",
            stem="202601010240 Retrieval Practice Review Claim",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_universal_human_example_claim_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - emotional examples effect
---

# Emotional Examples Effect

## Definition

An emotional examples effect is a claim that a worked example's emotional tone affects learning.

## Analogy

It is like adding a brighter color to a sign: the change may alter how strongly someone notices it.

## Example

For example, all learners remember topics better when examples are emotional.
""",
            stem="202601010217 Emotional Examples Effect",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_human_example_with_following_absolute_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - repeated examples effect
---

# Repeated Examples Effect

## Definition

A repeated examples effect is a claim that repeated examples change recall behavior.

## Analogy

It is like hearing a chorus several times: repetition may change what someone remembers.

## Example

For example, learners always remember topics better when examples repeat the same emotion.
""",
            stem="202601010219 Repeated Examples Effect",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_human_example_with_auxiliary_absolute_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - hidden menu confusion
---

# Hidden Menu Confusion

## Definition

A hidden menu confusion effect is a claim that menu visibility changes user comprehension.

## Analogy

It is like hiding a door label: the missing cue may change how someone navigates.

## Example

For example, users are always confused by hidden menus.
""",
            stem="202601010226 Hidden Menu Confusion",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_human_example_with_of_the_quantifier_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - learner memory claim
---

# Learner Memory Claim

## Definition

A learner memory claim states that an example style changes recall.

## Analogy

It is like changing the color of a reminder: the cue may alter what people remember.

## Example

For example, all of the learners remember topics better when examples are emotional.
""",
            stem="202601010227 Learner Memory Claim",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_multi_word_human_class_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - high school examples effect
---

# High School Examples Effect

## Definition

A high school examples effect claims that example wording changes student recall.

## Analogy

It is like changing the lighting in a classroom: the change may alter what students notice.

## Example

For example, all high school students remember topics better when examples are emotional.
""",
            stem="202601010238 High School Examples Effect",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_selection_chance_does_not_hide_separate_human_generalization(self):
        row = self.audit_single_note(
            """---
aliases:
  - mixed sampling and memory claim
---

# Mixed Sampling And Memory Claim

## Definition

A mixed sampling and memory claim combines selection-chance wording with a learner outcome.

## Analogy

It is like drawing names fairly and then making a separate claim about what those people remember.

## Example

For example, every student receives the same selection chance, and all learners remember topics better when examples are emotional.
""",
            stem="202601010229 Mixed Sampling And Memory Claim",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_human_generalization_before_selection_chance_still_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - memory then sampling claim
---

# Memory Then Sampling Claim

## Definition

A memory then sampling claim combines a learner outcome with selection-chance wording.

## Analogy

It is like making one claim about what people remember and another about how they are selected.

## Example

For example, all learners remember topics better, and every student receives the same selection chance.
""",
            stem="202601010233 Memory Then Sampling Claim",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_selection_chance_followed_by_same_subject_outcome_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - sampling then memory claim
---

# Sampling Then Memory Claim

## Definition

A sampling then memory claim combines a fair-selection statement with a learner outcome.

## Analogy

It is like explaining who enters a study and then making a separate claim about what they learned.

## Example

For example, every student receives the same selection chance and remembers topics better after the lesson.
""",
            stem="202601010239 Sampling Then Memory Claim",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_singular_human_example_claim_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - individual examples effect
---

# Individual Examples Effect

## Definition

An individual examples effect is a claim that example wording changes a learner's recall.

## Analogy

It is like changing one instruction on a sign: the new wording may change what someone does next.

## Example

For example, every learner remembers topics better when examples are emotional.
""",
            stem="202601010220 Individual Examples Effect",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_everyone_example_claim_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - everyone examples effect
---

# Everyone Examples Effect

## Definition

An everyone examples effect is a claim that example wording affects recall across all readers.

## Analogy

It is like changing a sign for a crowd: the wording may alter how people respond.

## Example

For example, everyone remembers topics better when examples are emotional.
""",
            stem="202601010221 Everyone Examples Effect",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_plural_human_example_with_modifier_word_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - shared recording pattern
---

# Shared Recording Pattern

## Definition

A shared recording pattern is a claim that people document information in the same way.

## Analogy

It is like giving a room one template: the template may shape what people write down.

## Example

For example, all users record notes in the same order.
""",
            stem="202601010224 Shared Recording Pattern",
        )

        self.assertTrue(row["factual_risk"])
        self.assertIn("factual_risk", finding_codes(row))

    def test_nonhuman_modifier_examples_do_not_trigger_factual_risk(self):
        examples = {
            "202601010222 Child Node Inheritance": "For example, all child nodes inherit the parent label.",
            "202601010223 User Account Permissions": "For example, all user accounts receive default permissions.",
            "202601010228 Customer Record Retention": "For example, all customer records inherit the retention label.",
            "202601010230 Customer Order Retention": "For example, all customer orders inherit the retention label.",
            "202601010231 User Event Inheritance": "For example, all user events inherit the parent label.",
        }
        for stem, example in examples.items():
            with self.subTest(stem=stem):
                row = self.audit_single_note(
                    f"""---
aliases: []
---

# {stem[13:]}

## Definition

This note describes a technical inheritance rule for a system object.

## Analogy

It is like copying a folder setting to the items stored inside that folder.

## Example

{example}
""",
                    stem=stem,
                )

                self.assertFalse(row["factual_risk"])
                self.assertNotIn("factual_risk", finding_codes(row))

    def test_legal_universal_claim_triggers_factual_risk(self):
        row = self.audit_single_note(
            """---
aliases:
  - gdpr deletion rule
---

# GDPR Deletion Rule

## Definition

A legal deletion rule specifies when an organization must erase stored personal data.

## Analogy

It is like a document-retention schedule: the rule controls when records must leave the archive.

## Example

For example, GDPR requires every company to delete user data within 30 days.
""",
            stem="202601010210 GDPR Deletion Rule",
        )

        self.assertTrue(row["factual_risk"])

    def test_cli_jsonl_validates_and_prints_valid_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            jsonl_path = Path(tmp) / "audit.jsonl"
            manifest_path = Path(tmp) / "manifest.json"

            audit_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.audit_notes",
                    "--vault",
                    str(FIXTURE_VAULT),
                    "--run-id",
                    "test-run",
                    "--jsonl",
                    str(jsonl_path),
                    "--manifest",
                    str(manifest_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(audit_result.returncode, 0, audit_result.stderr)
            self.assertEqual(audit_result.stdout.strip(), "rows=10")

            validation_result = subprocess.run(
                [sys.executable, "-m", "shared.scripts.validate_jsonl", str(jsonl_path)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(validation_result.returncode, 0, validation_result.stderr)
            self.assertEqual(validation_result.stdout.strip(), "valid_rows=10")

    def test_manifest_includes_all_count_keys(self):
        _, manifest = audit_vault(FIXTURE_VAULT, run_id="test-run")

        self.assertEqual(
            set(manifest["row_status_counts"]),
            {"complete", "reused_cache", "error", "skipped"},
        )
        self.assertEqual(set(manifest["priority_counts"]), {"P0", "P1", "P2", "P3", "no_change"})
        self.assertEqual(manifest["validation_status"], "not_run")

    def test_recommendations_are_objects(self):
        rows, _ = audit_vault(FIXTURE_VAULT, run_id="test-run")

        for row in rows:
            for recommendation in row["recommendations"]:
                self.assertIsInstance(recommendation, dict)
                self.assertEqual(set(recommendation), {"mode", "message"})

    def test_basic_card_dae_with_sources_is_valid(self):
        row = self.audit_single_note(
            """---
aliases:
  - stateless protocol
---

# Stateless Protocol

TARGET DECK: General

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
""",
            stem="202601010201 Stateless Protocol",
        )

        codes = {finding["code"] for finding in row["findings"]}
        self.assertNotIn("invalid_dae", codes)
        self.assertNotIn("misfiled_reference", codes)

    def test_cloze_card_with_extra_dae_is_valid(self):
        row = self.audit_single_note(
            """---
aliases:
  - CAP theorem
---

# CAP Theorem

START
Cloze
The CAP theorem states that a distributed data system can only guarantee two out of three properties simultaneously:

1. {{c1::Consistency}}: Nodes see the same data.
2. {{c2::Availability}}: Requests receive responses.
3. {{c3::Partition tolerance}}: The system continues through network failures.

Extra: This can be compared to note-takers in separate rooms: they can keep identical notes or keep writing while separated, but not both.

For example, during a network partition, one database may stay available with temporary inconsistency while another may reject some requests to preserve consistency.
END
""",
            stem="202601010202 CAP Theorem",
        )

        self.assertNotIn("invalid_dae", {finding["code"] for finding in row["findings"]})

    def test_overlong_definition_gets_specific_finding(self):
        row = self.audit_single_note(
            """---
aliases:
  - replication
---

# Replication

START
Basic
What is replication?

Back: Replication is the process of maintaining identical copies of data across multiple servers or storage devices, with synchronization mechanisms ensuring changes propagate to all replicas. This technique serves multiple purposes including fault tolerance, improved read performance, reduced latency by placing data closer to users, disaster recovery, regional availability, and operational resilience during hardware failures or network outages.

Replication is like a library maintaining identical books at several branches: each branch can serve readers while updates spread.

For example, a streaming service stores popular shows in multiple regions so viewers in different cities can stream from nearby replicas.
END
""",
            stem="202601010203 Replication",
        )

        codes = {finding["code"] for finding in row["findings"]}
        self.assertIn("definition_too_long", codes)
        self.assertNotIn("invalid_dae", codes)

    def test_code_blocks_do_not_create_multi_note_findings(self):
        row = self.audit_single_note(
            """---
aliases:
  - list extension
---

# Extend Method

TARGET DECK: General

START
Basic
What does list.extend do?

Back: The `.extend()` method mutates one list by appending every element from another iterable.

```python
# This comment is not a Markdown heading.
items = [1]
items.extend([2, 3])
```
END
""",
            stem="202601010204 Extend Method",
        )

        codes = {finding["code"] for finding in row["findings"]}
        self.assertIn("invalid_dae", codes)
        self.assertNotIn("multi_note", codes)

    def test_duplicate_overlap_ignores_ordinary_prose(self):
        row = self.audit_single_note(
            """---
aliases:
  - relational model
---

# Relational Model

## Definition

The relational model represents database information as named relations whose tuples can be queried with relational operations.

## Analogy

It is like standardized ledgers: each ledger keeps one kind of record, and shared identifiers connect related ledgers.

## Example

For example, a SQL database may permit duplicate rows even though formal relational theory treats relation bodies as sets of tuples.
""",
            stem="202601010212 Relational Model",
        )

        self.assertNotIn("duplicate_overlap", finding_codes(row))

    def test_duplicate_overlap_ignores_domain_overlap_phrase(self):
        row = self.audit_single_note(
            """---
aliases:
  - sequence race probability
---

# Pattern-Race Probability

TARGET DECK: General

START
Basic
Why can one coin-flip pattern beat another in a sequence race?

Back: Pattern-race probability depends on how each target pattern overlaps with recent outcomes, so equally long patterns need not have equal chances of appearing first.

Pattern-race probability is like watching for license-plate endings in traffic. A partial match can either help the same pattern continue or hand an advantage to a competing pattern.

For example, in a fair-coin race between HH and TH, the HH player wins only when the first two flips are HH.
END
""",
            stem="202601010213 Pattern-Race Probability",
        )

        self.assertNotIn("duplicate_overlap", finding_codes(row))

    def test_interview_template_is_misfiled_reference(self):
        row = self.audit_single_note(
            """---
aliases: []
---

# Tell Me About a Time Your Team Was Falling Behind a Deadline

This template will help you add structure and clarity to your answer.

## Brainstorm

- Success
- Failure

## STAR Method

Use situation, task, action, and result.
""",
            stem="202601010205 Interview Template",
            parent=False,
        )

        self.assertIn("misfiled_reference", {finding["code"] for finding in row["findings"]})

    def test_cli_writes_manifest_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            jsonl_path = Path(tmp) / "audit.jsonl"
            manifest_path = Path(tmp) / "manifest.json"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.audit_notes",
                    "--vault",
                    str(FIXTURE_VAULT),
                    "--run-id",
                    "test-run",
                    "--jsonl",
                    str(jsonl_path),
                    "--manifest",
                    str(manifest_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_id"], "test-run")
            self.assertEqual(manifest["outputs"]["audit_rows"], str(jsonl_path))
            self.assertEqual(manifest["outputs"]["manifest"], str(manifest_path))

    def test_deterministic_fixture_cli_output_is_reproducible_across_paths(self):
        with tempfile.TemporaryDirectory() as first_tmp, tempfile.TemporaryDirectory() as second_tmp:
            first_jsonl = Path(first_tmp) / "audit.jsonl"
            first_manifest = Path(first_tmp) / "manifest.json"
            second_jsonl = Path(second_tmp) / "audit.jsonl"
            second_manifest = Path(second_tmp) / "manifest.json"

            first_result = self.run_audit_cli(
                first_jsonl,
                first_manifest,
                extra_args=["--deterministic-fixture-output"],
            )
            second_result = self.run_audit_cli(
                second_jsonl,
                second_manifest,
                extra_args=["--deterministic-fixture-output"],
            )
            self.assertEqual(first_result.returncode, 0, first_result.stderr)
            self.assertEqual(second_result.returncode, 0, second_result.stderr)

            self.assertEqual(first_jsonl.read_bytes(), second_jsonl.read_bytes())
            self.assertEqual(first_manifest.read_bytes(), second_manifest.read_bytes())

            manifest = json.loads(first_manifest.read_text(encoding="utf-8"))
            self.assertEqual(manifest["outputs"]["audit_rows"], "audit.jsonl")
            self.assertEqual(manifest["outputs"]["manifest"], "manifest.json")

    def run_audit_cli(
        self,
        jsonl_path: Path,
        manifest_path: Path,
        *,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "shared.scripts.audit_notes",
                "--vault",
                str(FIXTURE_VAULT),
                "--run-id",
                "test-run",
                "--jsonl",
                str(jsonl_path),
                "--manifest",
                str(manifest_path),
                *(extra_args or []),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    def test_factual_risk_skips_reference_and_sources_sections(self):
        body = (
            "A concept is one clear idea stated plainly.\n\n"
            "Reference:\n"
            "- The Earth formed about 4.5 billion years ago.\n\n"
            "Sources:\n"
            "1. A source claiming the Great Wall is visible from orbit.\n"
        )
        joined = " ".join(_factual_risk_sentences(body))
        self.assertNotIn("4.5 billion", joined)   # Reference: content stripped
        self.assertNotIn("Great Wall", joined)    # Sources: content stripped

    def test_basic_card_dae_with_reference_and_sources_is_valid(self):
        content = (
            "---\naliases:\n  - concept\ntags:\n  - atomic-note\n---\n\n"
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
        row = self.audit_single_note(content, stem="202601010110 Reference and sources note")
        codes = {finding["code"] for finding in row["findings"]}
        self.assertNotIn("invalid_dae", codes)
        self.assertNotIn("misfiled_reference", codes)

    def audit_single_note(self, content: str, *, stem: str, parent: bool = True) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            atomic_folder = vault / "Atomic Notes"
            structure_folder = vault / "Structure Notes"
            atomic_folder.mkdir()
            structure_folder.mkdir()
            (atomic_folder / f"{stem}.md").write_text(content, encoding="utf-8")
            if parent:
                (structure_folder / "Atomic Note Quality.md").write_text(f"- [[{stem}]]\n", encoding="utf-8")
            rows, _ = audit_vault(vault, run_id="single-note-test")
        return rows[0]


if __name__ == "__main__":
    unittest.main()
