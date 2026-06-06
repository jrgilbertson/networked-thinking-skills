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

    def test_score_uses_finding_loss_not_priority_label(self):
        findings = [{"priority": "P0", "code": "missing_parent"}]
        self.assertEqual(compute_final_score(findings), 92)

    def test_invalid_dae_suppresses_dae_component_losses(self):
        findings = [
            {"priority": "P1", "code": "missing_dae"},
            {"priority": "P2", "code": "weak_dae"},
            {"priority": "P2", "code": "model_weak_analogy"},
        ]
        self.assertEqual(compute_loss(findings), 35)
        self.assertEqual(compute_final_score(findings), 65)

    def test_dae_component_losses_are_capped(self):
        findings = [
            {"priority": "P1", "code": "definition_too_long"},
            {"priority": "P2", "code": "model_weak_definition"},
            {"priority": "P2", "code": "model_weak_analogy"},
            {"priority": "P2", "code": "model_weak_example"},
        ]
        self.assertEqual(compute_loss(findings), 35)
        self.assertEqual(compute_final_score(findings), 65)

    def test_factual_risk_aliases_count_once(self):
        findings = [
            {"priority": "P2", "code": "factual_risk"},
            {"priority": "P2", "code": "model_factual_risk"},
        ]
        self.assertEqual(canonicalize_findings(findings), {"factual_risk"})
        self.assertEqual(compute_final_score(findings), 92)

    def test_multi_note_suppresses_generic_not_atomic(self):
        findings = [
            {"priority": "P0", "code": "multi_note_file"},
            {"priority": "P0", "code": "model_not_atomic"},
        ]
        self.assertEqual(canonicalize_findings(findings), {"multi_note"})
        self.assertEqual(compute_final_score(findings), 55)

    def test_unknown_finding_code_gets_default_loss(self):
        findings = [{"priority": "P3", "code": "future_quality_signal"}]
        self.assertEqual(compute_final_score(findings), 92)

    def test_score_never_drops_below_one(self):
        findings = [{"priority": "P0", "code": f"unknown_{index}"} for index in range(20)]
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
