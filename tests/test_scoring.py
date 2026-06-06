import unittest

from shared.scripts.scoring import (
    bucket_for_score,
    canonicalize_findings,
    compute_clean,
    compute_final_score,
    compute_loss,
)


class ScoringTest(unittest.TestCase):
    def test_clean_note_scores_100(self):
        score = compute_final_score([])
        self.assertEqual(score, 100)

    def test_invalid_dae_suppresses_dae_component_losses(self):
        findings = [
            {"code": "invalid_dae"},
            {"code": "weak_dae"},
            {"code": "weak_analogy"},
        ]
        self.assertEqual(compute_loss(findings), 35)
        self.assertEqual(compute_final_score(findings), 65)

    def test_dae_component_losses_are_capped(self):
        findings = [
            {"code": "definition_too_long"},
            {"code": "weak_definition"},
            {"code": "weak_analogy"},
            {"code": "weak_example"},
        ]
        self.assertEqual(compute_loss(findings), 35)
        self.assertEqual(compute_final_score(findings), 65)

    def test_duplicate_codes_count_once(self):
        findings = [
            {"code": "factual_risk"},
            {"code": "factual_risk"},
        ]
        self.assertEqual(canonicalize_findings(findings), {"factual_risk"})
        self.assertEqual(compute_final_score(findings), 92)

    def test_multi_note_suppresses_generic_not_atomic(self):
        findings = [
            {"code": "multi_note"},
            {"code": "not_atomic"},
        ]
        self.assertEqual(canonicalize_findings(findings), {"multi_note"})
        self.assertEqual(compute_final_score(findings), 55)

    def test_unknown_finding_code_fails(self):
        findings = [{"code": "future_quality_signal"}]
        with self.assertRaises(ValueError):
            compute_final_score(findings)

    def test_score_never_drops_below_one(self):
        findings = [
            {"code": code}
            for code in [
                "multi_note",
                "invalid_dae",
                "misfiled_reference",
                "not_atomic",
                "malformed_anki",
                "unclear",
            ]
        ]
        self.assertEqual(compute_final_score(findings), 1)

    def test_priority_is_derived_from_score_bands(self):
        self.assertEqual(bucket_for_score(1), "P0")
        self.assertEqual(bucket_for_score(49), "P0")
        self.assertEqual(bucket_for_score(50), "P1")
        self.assertEqual(bucket_for_score(69), "P1")
        self.assertEqual(bucket_for_score(70), "P2")
        self.assertEqual(bucket_for_score(84), "P2")
        self.assertEqual(bucket_for_score(85), "P3")
        self.assertEqual(bucket_for_score(99), "P3")
        self.assertIsNone(bucket_for_score(100))

    def test_clean_requires_score_100(self):
        self.assertFalse(compute_clean(99, pending_model=False, fact_check_required=False))
        self.assertTrue(compute_clean(100, pending_model=False, fact_check_required=False))

    def test_clean_rejects_pending_model(self):
        self.assertFalse(compute_clean(100, pending_model=True, fact_check_required=False))

    def test_clean_rejects_fact_check_required(self):
        self.assertFalse(compute_clean(100, pending_model=False, fact_check_required=True))


if __name__ == "__main__":
    unittest.main()
