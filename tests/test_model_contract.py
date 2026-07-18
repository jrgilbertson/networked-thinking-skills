import json
from copy import deepcopy
from pathlib import Path
import unittest

from shared.scripts.model_contract import build_cache_key, validate_model_judgment
from shared.scripts.schema_validation import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_JUDGMENT_SCHEMA_PATH = REPO_ROOT / "shared" / "schemas" / "model-judgment.schema.json"
CLEAN_NOTE_PATH = (
    "Atomic Notes/202601010101 A clean atomic note explains one durable idea in plain language "
    "and keeps the claim small enough to test against examples.md"
)


BASE_CACHE_KEY_ARGS = {
    "note_path": CLEAN_NOTE_PATH,
    "content_hash": "abc123",
    "doctrine_version": "1.0.0",
    "rubric_version": "1.0.0",
    "prompt_version": "1.0.0",
    "audit_mode": "default",
}

VALID_JUDGMENT = {
    "schema_version": "2.0.0",
    "prompt_version": "1.0.2",
    "note_path": CLEAN_NOTE_PATH,
    "dimension_adjustments": {
        "clarity": -5,
        "connections": 10,
    },
    "findings": [
        {
            "code": "missing_parent",
            "message": "The note needs a clearer parent link.",
            "evidence": [
                {
                    "excerpt": "This idea is useful across several notes.",
                    "reason": "The excerpt gestures at connections without naming a target.",
                }
            ],
        }
    ],
    "factual_risk": False,
    "factual_risk_reason": None,
    "fact_check_required": False,
    "evidence": [
        {
            "excerpt": "Definition: A compact, self-contained idea.",
            "reason": "Shows the note has a clear definition section.",
        }
    ],
}


class ModelContractTest(unittest.TestCase):
    def test_cache_key_is_stable_and_changes_with_each_field(self):
        base_key = build_cache_key(**BASE_CACHE_KEY_ARGS)
        self.assertEqual(base_key, build_cache_key(**BASE_CACHE_KEY_ARGS))

        replacements = {
            "note_path": "Atomic Notes/202601010102 Weak DAE note.md",
            "content_hash": "def456",
            "doctrine_version": "1.0.4",
            "rubric_version": "1.0.1",
            "prompt_version": "1.0.2",
            "audit_mode": "model",
        }
        for field, replacement in replacements.items():
            with self.subTest(field=field):
                changed_args = dict(BASE_CACHE_KEY_ARGS)
                changed_args[field] = replacement
                self.assertNotEqual(base_key, build_cache_key(**changed_args))

    def test_valid_model_judgment_passes(self):
        validate_model_judgment(deepcopy(VALID_JUDGMENT))

    def test_factual_risk_true_requires_non_empty_reason(self):
        for reason in (None, ""):
            with self.subTest(reason=reason):
                judgment = deepcopy(VALID_JUDGMENT)
                judgment["factual_risk"] = True
                judgment["factual_risk_reason"] = reason
                with self.assertRaises(ValidationError):
                    validate_model_judgment(judgment)

    def test_evidence_excerpt_over_40_words_fails(self):
        judgment = deepcopy(VALID_JUDGMENT)
        judgment["evidence"][0]["excerpt"] = " ".join(f"word{i}" for i in range(41))
        with self.assertRaises(ValidationError):
            validate_model_judgment(judgment)

    def test_invalid_dimension_key_fails(self):
        judgment = deepcopy(VALID_JUDGMENT)
        judgment["dimension_adjustments"]["formatting"] = 5
        with self.assertRaises(ValidationError):
            validate_model_judgment(judgment)

    def test_invalid_finding_code_fails(self):
        judgment = deepcopy(VALID_JUDGMENT)
        judgment["findings"][0]["code"] = "weak_connection"
        with self.assertRaises(ValidationError):
            validate_model_judgment(judgment)

    def test_extra_top_level_key_fails(self):
        judgment = deepcopy(VALID_JUDGMENT)
        judgment["unexpected"] = True
        with self.assertRaises(ValidationError):
            validate_model_judgment(judgment)

    def test_schema_allows_null_factual_risk_reason_and_excerpt_reason_evidence(self):
        schema = json.loads(MODEL_JUDGMENT_SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(schema["properties"]["schema_version"]["const"], "2.0.0")
        self.assertIn("prompt_version", schema["required"])
        self.assertEqual(set(schema["properties"]["factual_risk_reason"]["type"]), {"string", "null"})

        finding = schema["$defs"]["finding"]
        self.assertEqual(finding["required"], ["code", "message"])
        self.assertNotIn("priority", finding["properties"])

        evidence = schema["$defs"]["evidence"]
        self.assertEqual(evidence["required"], ["excerpt", "reason"])
        self.assertEqual(set(evidence["properties"]), {"excerpt", "reason"})
        self.assertNotIn("source", evidence["properties"])
        self.assertNotIn("quote", evidence["properties"])


if __name__ == "__main__":
    unittest.main()
