"""A/B test traffic splitting for prompts.

Uses consistent hashing to deterministically assign users to prompt variants,
ensuring the same user always sees the same variant.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import structlog
from pydantic import BaseModel, Field, model_validator

__all__ = ["ABTest", "ABTestManager"]

logger = structlog.get_logger(__name__)


class ABTest(BaseModel):
    """A/B test definition for prompt variants.

    Attributes:
        name: Unique test identifier.
        prompt_name: The base prompt being tested.
        variants: Mapping of variant name to prompt label (e.g. {"control": "prod", "new_v2": "staging"}).
        traffic_split: Mapping of variant name to traffic percentage (must sum to 100).
        metrics: Metrics to track for evaluation.
        active: Whether the test is currently running.
    """

    name: str
    prompt_name: str
    variants: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of variant name -> prompt label",
    )
    traffic_split: dict[str, float] = Field(
        default_factory=dict,
        description="Mapping of variant name -> traffic percentage (must sum to 100)",
    )
    metrics: list[str] = Field(default_factory=list)
    active: bool = True

    @model_validator(mode="after")
    def _validate_traffic_split(self) -> ABTest:
        """Ensure traffic_split keys match variants and percentages sum to 100."""
        if not self.variants or not self.traffic_split:
            return self

        # All traffic_split keys must be in variants
        for key in self.traffic_split:
            if key not in self.variants:
                raise ValueError(
                    f"Traffic split key '{key}' not found in variants: {list(self.variants.keys())}"
                )

        total = sum(self.traffic_split.values())
        if abs(total - 100.0) > 0.01:
            raise ValueError(
                f"Traffic split must sum to 100, got {total}"
            )

        return self


@dataclass
class ABTestOutcome:
    """Recorded outcome of a variant assignment."""

    test_name: str
    variant: str
    user_id: str
    metric_values: dict[str, float] = field(default_factory=dict)


class ABTestManager:
    """Manages A/B test variant assignment and outcome recording.

    Uses consistent hashing (SHA-256) to deterministically assign users to
    prompt variants based on the test name + user ID combination.

    Args:
        tests: Optional initial list of ABTest definitions.
    """

    def __init__(self, tests: list[ABTest] | None = None) -> None:
        self._tests: dict[str, ABTest] = {}
        self._outcomes: list[ABTestOutcome] = []

        if tests:
            for test in tests:
                self.register_test(test)

    def register_test(self, test: ABTest) -> None:
        """Register an A/B test.

        Args:
            test: The ABTest definition to register.
        """
        self._tests[test.name] = test
        logger.info(
            "ab_test_manager.register",
            test=test.name,
            prompt=test.prompt_name,
            variants=list(test.variants.keys()),
        )

    def get_variant(self, ab_test: ABTest | str, user_id: str) -> str:
        """Determine the variant for a user using consistent hashing.

        The same (test_name, user_id) pair always returns the same variant.

        Args:
            ab_test: ABTest instance or test name string.
            user_id: Unique user identifier for deterministic assignment.

        Returns:
            The selected variant name.

        Raises:
            KeyError: If test name not found (when string is passed).
            ValueError: If the test has no variants or traffic split.
        """
        if isinstance(ab_test, str):
            if ab_test not in self._tests:
                raise KeyError(f"A/B test '{ab_test}' not registered")
            ab_test = self._tests[ab_test]

        if not ab_test.variants or not ab_test.traffic_split:
            raise ValueError(f"A/B test '{ab_test.name}' has no variants or traffic split")

        hash_value = self._consistent_hash(ab_test.name, user_id)

        # Walk through cumulative traffic split to find the variant
        cumulative = 0.0
        sorted_variants = sorted(ab_test.traffic_split.items())
        for variant_name, pct in sorted_variants:
            cumulative += pct
            if hash_value < cumulative:
                logger.debug(
                    "ab_test_manager.assigned",
                    test=ab_test.name,
                    user=user_id,
                    variant=variant_name,
                )
                return variant_name

        # Fallback to last variant (handles floating point edge case)
        return sorted_variants[-1][0]

    def get_label_for_user(self, ab_test: ABTest | str, user_id: str) -> str:
        """Get the prompt label for a user's assigned variant.

        Args:
            ab_test: ABTest instance or test name string.
            user_id: Unique user identifier.

        Returns:
            The prompt label corresponding to the user's variant.
        """
        if isinstance(ab_test, str):
            if ab_test not in self._tests:
                raise KeyError(f"A/B test '{ab_test}' not registered")
            ab_test = self._tests[ab_test]

        variant = self.get_variant(ab_test, user_id)
        return ab_test.variants[variant]

    def record_outcome(
        self,
        test_name: str,
        variant: str,
        user_id: str,
        metric_values: dict[str, float] | None = None,
    ) -> ABTestOutcome:
        """Record an outcome for a variant assignment.

        Args:
            test_name: Name of the A/B test.
            variant: The variant that was assigned.
            user_id: User identifier.
            metric_values: Metric name -> value mappings.

        Returns:
            The recorded ABTestOutcome.
        """
        outcome = ABTestOutcome(
            test_name=test_name,
            variant=variant,
            user_id=user_id,
            metric_values=metric_values or {},
        )
        self._outcomes.append(outcome)
        logger.info(
            "ab_test_manager.record_outcome",
            test=test_name,
            variant=variant,
            user=user_id,
            metrics=metric_values,
        )
        return outcome

    @property
    def outcomes(self) -> list[ABTestOutcome]:
        """Return all recorded outcomes."""
        return list(self._outcomes)

    @property
    def registered_tests(self) -> list[str]:
        """Return names of all registered tests."""
        return list(self._tests.keys())

    @staticmethod
    def _consistent_hash(test_name: str, user_id: str) -> float:
        """Generate a deterministic float in [0, 100) from test name + user ID.

        Uses SHA-256 for uniform distribution.

        Args:
            test_name: The A/B test name.
            user_id: The user identifier.

        Returns:
            A float in the range [0, 100).
        """
        raw = f"{test_name}:{user_id}".encode()
        digest = hashlib.sha256(raw).hexdigest()
        # Take first 8 hex chars (32 bits) -> int -> scale to [0, 100)
        int_val = int(digest[:8], 16)
        return (int_val / 0xFFFFFFFF) * 100.0
