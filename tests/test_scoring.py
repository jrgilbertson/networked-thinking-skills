import unittest

from shared.scripts.scoring import (
    DIMENSION_WEIGHTS,
    compute_clean,
    compute_final_score,
    highest_priority,
    priority_for_score,
)


BASE_DIMENSIONS = {
    "structure": 100,
    "atomicity": 100,
    "dae_quality": 100,
    "clarity": 100,
    "connections": 100,
    "metadata_card_safety": 100,
}


class ScoringTest(unittest.TestCase):
    def test_weights_sum_to_one(self):
        self.assertEqual(sum(DIMENSION_WEIGHTS.values()), 1.0)

    def test_clean_note_scores_100(self):
        score = compute_final_score(BASE_DIMENSIONS, [])
        self.assertEqual(score, 100)

    def test_p1_finding_lands_perfect_note_at_p1_boundary(self):
        findings = [{"priority": "P1", "code": "missing_parent"}]
        self.assertEqual(compute_final_score(BASE_DIMENSIONS, findings), 69)

    def test_p0_finding_lands_perfect_note_at_p0_boundary(self):
        findings = [{"priority": "P0"}]
        self.assertEqual(compute_final_score(BASE_DIMENSIONS, findings), 49)

    def test_p2_finding_lands_perfect_note_at_p2_boundary(self):
        findings = [{"priority": "P2"}]
        self.assertEqual(compute_final_score(BASE_DIMENSIONS, findings), 89)

    def test_additional_findings_lower_score_without_hard_caps(self):
        findings = [
            {"priority": "P1"},
            {"priority": "P2"},
            {"priority": "P3"},
        ]
        self.assertEqual(compute_final_score(BASE_DIMENSIONS, findings), 65)

    def test_score_never_drops_below_one(self):
        findings = [{"priority": "P0"} for _ in range(20)]
        self.assertEqual(
            compute_final_score({key: 0 for key in BASE_DIMENSIONS}, findings),
            1,
        )

    def test_priority_is_derived_from_score_bands(self):
        self.assertEqual(priority_for_score(1), "P0")
        self.assertEqual(priority_for_score(49), "P0")
        self.assertEqual(priority_for_score(50), "P1")
        self.assertEqual(priority_for_score(69), "P1")
        self.assertEqual(priority_for_score(70), "P2")
        self.assertEqual(priority_for_score(89), "P2")
        self.assertEqual(priority_for_score(90), "P3")
        self.assertEqual(priority_for_score(100), "P3")

    def test_highest_priority_uses_urgency_order(self):
        findings = [{"priority": "P3"}, {"priority": "P1"}, {"priority": "P2"}]
        self.assertEqual(highest_priority(findings), "P1")

    def test_clean_allows_p3_only(self):
        findings = [{"priority": "P3"}]
        self.assertTrue(compute_clean(92, findings, pending_model=False, fact_check_required=False))

    def test_clean_rejects_p2(self):
        findings = [{"priority": "P2"}]
        self.assertFalse(compute_clean(90, findings, pending_model=False, fact_check_required=False))

    def test_clean_rejects_pending_model(self):
        self.assertFalse(compute_clean(100, [], pending_model=True, fact_check_required=False))

    def test_clean_rejects_fact_check_required(self):
        self.assertFalse(compute_clean(100, [], pending_model=False, fact_check_required=True))


if __name__ == "__main__":
    unittest.main()
