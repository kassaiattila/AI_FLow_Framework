"""
@test_registry:
    suite: prompts-unit
    component: prompts.ab_testing
    covers: [src/aiflow/prompts/ab_testing.py]
    phase: 3
    priority: medium
    estimated_duration_ms: 200
    requires_services: []
    tags: [prompts, ab_testing, consistent_hashing, traffic_split]
"""

import pytest

from aiflow.prompts.ab_testing import ABTest, ABTestManager, ABTestOutcome


@pytest.fixture
def basic_ab_test():
    """Standard 50/50 A/B test."""
    return ABTest(
        name="tone-test",
        prompt_name="greeting",
        variants={"control": "prod", "friendly": "staging"},
        traffic_split={"control": 50.0, "friendly": 50.0},
        metrics=["satisfaction", "completion_rate"],
    )


@pytest.fixture
def three_way_test():
    """Three-way traffic split."""
    return ABTest(
        name="model-test",
        prompt_name="summarizer",
        variants={"v1": "prod", "v2": "staging", "v3": "dev"},
        traffic_split={"v1": 60.0, "v2": 30.0, "v3": 10.0},
        metrics=["latency", "quality_score"],
    )


class TestABTestModel:
    def test_basic_creation(self, basic_ab_test):
        assert basic_ab_test.name == "tone-test"
        assert basic_ab_test.prompt_name == "greeting"
        assert len(basic_ab_test.variants) == 2
        assert basic_ab_test.active is True

    def test_traffic_split_must_sum_to_100(self):
        with pytest.raises(ValueError, match="sum to 100"):
            ABTest(
                name="bad-split",
                prompt_name="test",
                variants={"a": "prod", "b": "dev"},
                traffic_split={"a": 40.0, "b": 40.0},
            )

    def test_traffic_split_keys_must_match_variants(self):
        with pytest.raises(ValueError, match="not found in variants"):
            ABTest(
                name="mismatched",
                prompt_name="test",
                variants={"a": "prod"},
                traffic_split={"a": 50.0, "nonexistent": 50.0},
            )

    def test_empty_variants_allowed(self):
        """Empty variants/traffic_split is allowed (validation skipped)."""
        test = ABTest(name="empty", prompt_name="test")
        assert test.variants == {}
        assert test.traffic_split == {}


class TestABTestManagerVariantSelection:
    def test_consistent_hashing_is_deterministic(self, basic_ab_test):
        mgr = ABTestManager()
        v1 = mgr.get_variant(basic_ab_test, "user-42")
        v2 = mgr.get_variant(basic_ab_test, "user-42")
        assert v1 == v2

    def test_different_users_can_get_different_variants(self, basic_ab_test):
        mgr = ABTestManager()
        # With enough users, both variants should appear
        variants_seen = set()
        for i in range(200):
            v = mgr.get_variant(basic_ab_test, f"user-{i}")
            variants_seen.add(v)
        assert len(variants_seen) == 2, "Both variants should appear across 200 users"

    def test_three_way_split_covers_all_variants(self, three_way_test):
        mgr = ABTestManager()
        variants_seen = set()
        for i in range(500):
            v = mgr.get_variant(three_way_test, f"user-{i}")
            variants_seen.add(v)
        assert variants_seen == {"v1", "v2", "v3"}

    def test_get_variant_by_test_name(self, basic_ab_test):
        mgr = ABTestManager(tests=[basic_ab_test])
        v = mgr.get_variant("tone-test", "user-1")
        assert v in ("control", "friendly")

    def test_get_variant_unknown_test_raises(self):
        mgr = ABTestManager()
        with pytest.raises(KeyError, match="not registered"):
            mgr.get_variant("nonexistent", "user-1")

    def test_get_label_for_user(self, basic_ab_test):
        mgr = ABTestManager(tests=[basic_ab_test])
        label = mgr.get_label_for_user("tone-test", "user-42")
        assert label in ("prod", "staging")


class TestABTestManagerOutcomes:
    def test_record_outcome(self, basic_ab_test):
        mgr = ABTestManager(tests=[basic_ab_test])
        outcome = mgr.record_outcome(
            test_name="tone-test",
            variant="control",
            user_id="user-42",
            metric_values={"satisfaction": 0.9},
        )
        assert isinstance(outcome, ABTestOutcome)
        assert outcome.test_name == "tone-test"
        assert outcome.variant == "control"
        assert outcome.metric_values["satisfaction"] == 0.9
        assert len(mgr.outcomes) == 1

    def test_multiple_outcomes(self, basic_ab_test):
        mgr = ABTestManager(tests=[basic_ab_test])
        mgr.record_outcome("tone-test", "control", "u1", {"score": 0.8})
        mgr.record_outcome("tone-test", "friendly", "u2", {"score": 0.95})
        assert len(mgr.outcomes) == 2
