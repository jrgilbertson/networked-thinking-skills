import unittest
import hashlib
from copy import deepcopy
from shared.scripts.schema_validation import ValidationError, validate_audit_row, validate_inventory_row
from shared.scripts.model_contract import build_cache_key


def inventory_row():
    return {
        "artifact_type": "audit_inventory", "schema_version": "1.0.0",
        "run_id": "synthetic", "note_path": "Atomic Notes/Example.md",
        "note_link": "[[Atomic Notes/Example|Example]]", "content": "# Example\n\nA test idea.",
        "content_hash": hashlib.sha256(b"# Example\n\nA test idea.").hexdigest(), "modified_time": "2000-01-01T00:00:00Z",
        "doctrine_version": "1.0.8", "rubric_version": "1.0.4",
        "prompt_version": "2.0.0", "audit_mode": "selected:synthetic",
        "config_snapshot": {}, "integrity_checks": [],
    }


def pending_row():
    i = inventory_row()
    for k in ("artifact_type", "content", "audit_mode"):
        i.pop(k)
    i.update(schema_version="2.0.0", row_status="skipped", review_status="pending",
             score=None, dimensions=None, priority=None, clean=False, pending_model=True,
             findings=[], recommendations=[], model_judgment=None, cache_status="none",
             factual_risk=False, fact_check_required=False)
    return i


class ModelLedContractTest(unittest.TestCase):
    def test_pending_has_no_quality_values(self):
        row = pending_row()
        validate_audit_row(row, default_scan=True)
        for field, value in (("score", 100), ("dimensions", {}), ("clean", True)):
            changed = deepcopy(row)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate_audit_row(changed, default_scan=True)

    def test_unreviewed_cannot_claim_reviewed(self):
        row = pending_row()
        row["review_status"] = "reviewed"
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_inventory_rejects_legacy_row_and_unsafe_paths(self):
        validate_inventory_row(inventory_row())
        with self.assertRaisesRegex(ValidationError, "inventory"):
            validate_inventory_row(pending_row())
        row = inventory_row()
        row["note_path"] = "../outside.md"
        with self.assertRaises(ValidationError):
            validate_inventory_row(row)

    def test_model_identity_and_runner_contract_bind_cache(self):
        args = dict(note_path="a.md", content_hash="h", doctrine_version="1",
                    rubric_version="1", prompt_version="2", audit_mode="all",
                    model_identity="synthetic-model", runner_identity="command:v1")
        key = build_cache_key(**args)
        for field in ("model_identity", "runner_identity", "content_hash"):
            changed = dict(args)
            changed[field] = "different"
            with self.subTest(field=field):
                self.assertNotEqual(key, build_cache_key(**changed))


if __name__ == "__main__":
    unittest.main()
