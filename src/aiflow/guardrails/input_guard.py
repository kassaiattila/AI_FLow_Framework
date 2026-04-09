"""Input guardrail — validates user input before it reaches the LLM.

Checks for prompt injection attempts, PII exposure, input length,
and optionally language constraints.
"""

from __future__ import annotations

import re

import structlog

from aiflow.guardrails.base import (
    GuardrailBase,
    GuardrailResult,
    GuardrailViolation,
    PIIMatch,
    Severity,
)

__all__ = ["InputGuard"]

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt injection patterns
# ---------------------------------------------------------------------------
INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+(previous|all|above|prior)\s+instructions", "ignore_instructions"),
    (r"disregard\s+(previous|all|above|prior)", "disregard_instructions"),
    (r"you\s+are\s+now\s+", "role_override"),
    (r"act\s+as\s+(if\s+you\s+are|a)\s+", "role_override"),
    (r"system\s*:\s*", "system_prompt_inject"),
    (r"<\s*system\s*>", "system_tag_inject"),
    (r"\[INST\]", "inst_tag_inject"),
    (r"```\s*system", "code_block_system"),
    (r"jailbreak", "jailbreak_keyword"),
    (r"DAN\s+mode", "dan_mode"),
    (r"<script[\s>]", "xss_script"),
    (r"javascript\s*:", "xss_javascript"),
    (r"prompt\s*leak", "prompt_leak"),
    (r"repeat\s+(the\s+)?(system|initial)\s+prompt", "prompt_extraction"),
]

# ---------------------------------------------------------------------------
# PII patterns — Hungarian + US formats
# ---------------------------------------------------------------------------
PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Email
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "email"),
    # US SSN (xxx-xx-xxxx)
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "us_ssn"),
    # HU tax number (xxxxxxxxxx or xxxxxxxx-x-xx)
    (re.compile(r"\b\d{8}-\d-\d{2}\b"), "hu_tax_number"),
    # HU personal ID (TAJ: xxx-xxx-xxx)
    (re.compile(r"\b\d{3}-\d{3}-\d{3}\b"), "hu_taj"),
    # Phone — international or local HU/US
    (re.compile(r"\b\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}\b"), "phone"),
    # Credit card (16 digits with optional separators)
    (re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), "credit_card"),
    # HU bank account (xxxxxxxx-xxxxxxxx or xxxxxxxx-xxxxxxxx-xxxxxxxx)
    (
        re.compile(r"\b\d{8}-\d{8}(-\d{8})?\b"),
        "hu_bank_account",
    ),
]

# Simple language detection heuristics (character-set based)
_LANG_HINTS: dict[str, re.Pattern[str]] = {
    "hu": re.compile(r"[áéíóöőúüű]", re.IGNORECASE),
    "en": re.compile(r"\b(the|is|are|was|were|have|has|with|from|this|that)\b", re.IGNORECASE),
}


class InputGuard(GuardrailBase):
    """Validates user input before LLM processing.

    Args:
        max_length: Maximum allowed character count.
        check_pii: Whether to detect PII patterns.
        pii_masking: Legacy bool toggle (kept for backward compat).
        pii_masking_mode: Tri-state PII masking — ``"on"``/``"partial"``/``"off"``.
        allowed_pii_types: PII type names that pass through in PARTIAL mode.
        pii_logging: If True, log which PII types were detected (audit trail).
        check_injection: Whether to detect prompt injection.
        allowed_languages: Optional list of ISO-639-1 codes (e.g. ``["hu", "en"]``).
        injection_patterns: Extra injection patterns ``(regex, label)`` to append.
    """

    def __init__(
        self,
        *,
        max_length: int = 10_000,
        check_pii: bool = True,
        pii_masking: bool = False,
        pii_masking_mode: str = "on",
        allowed_pii_types: list[str] | None = None,
        pii_logging: bool = False,
        check_injection: bool = True,
        allowed_languages: list[str] | None = None,
        injection_patterns: list[tuple[str, str]] | None = None,
    ) -> None:
        self._max_length = max_length
        self._check_pii = check_pii
        self._pii_masking = pii_masking
        self._pii_masking_mode = (
            pii_masking_mode.value if hasattr(pii_masking_mode, "value") else str(pii_masking_mode)
        )
        self._allowed_pii_types = set(allowed_pii_types or [])
        self._pii_logging = pii_logging
        self._check_injection = check_injection
        self._allowed_languages = allowed_languages
        self._extra_injection = injection_patterns or []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, text: str, **kwargs: object) -> GuardrailResult:
        """Run all input guardrail checks."""
        violations: list[GuardrailViolation] = []
        pii_matches: list[PIIMatch] = []
        sanitized = text

        # 1. Length
        if len(text) > self._max_length:
            violations.append(
                GuardrailViolation(
                    rule="input_length",
                    message=f"Input exceeds maximum length ({len(text)} > {self._max_length})",
                    severity=Severity.WARNING,
                    details={"length": len(text), "max": self._max_length},
                )
            )

        # 2. Injection detection
        if self._check_injection:
            violations.extend(self._detect_injection(text))

        # 3. PII detection (respects pii_masking_mode: on/partial/off)
        if self._check_pii and self._pii_masking_mode != "off":
            found = self._detect_pii(text)
            pii_matches.extend(found)
            if found:
                if self._pii_logging:
                    logger.info(
                        "pii_detected_audit",
                        pii_types=[m.pattern_name for m in found],
                        mode=self._pii_masking_mode,
                    )
                if self._pii_masking_mode == "on":
                    # Mask ALL PII
                    to_mask = found
                elif self._pii_masking_mode == "partial":
                    # Mask only PII types NOT in allowed list.
                    # If an allowed match overlaps a non-allowed match at the
                    # same position, the non-allowed match is also skipped
                    # (e.g. TAJ "123-456-789" also matches phone pattern).
                    allowed_ranges: set[tuple[int, int]] = set()
                    for m in found:
                        if m.pattern_name in self._allowed_pii_types:
                            allowed_ranges.add((m.start, m.end))
                    to_mask = [
                        m
                        for m in found
                        if m.pattern_name not in self._allowed_pii_types
                        and not any(m.start < ae and m.end > as_ for as_, ae in allowed_ranges)
                    ]
                else:
                    to_mask = []

                if to_mask:
                    violations.append(
                        GuardrailViolation(
                            rule="pii_detected",
                            message=f"PII detected in input: {', '.join(m.pattern_name for m in to_mask)}",
                            severity=Severity.WARNING,
                            details={"pii_types": [m.pattern_name for m in to_mask]},
                        )
                    )
                    sanitized = self._mask_pii(sanitized, to_mask)
        elif self._check_pii and self._pii_masking_mode == "off" and self._pii_logging:
            # OFF mode: still detect for audit logging, but don't mask or violate
            found = self._detect_pii(text)
            pii_matches.extend(found)
            if found:
                logger.info(
                    "pii_detected_audit",
                    pii_types=[m.pattern_name for m in found],
                    mode="off",
                )

        # 4. Language check
        if self._allowed_languages:
            lang_violation = self._check_language(text)
            if lang_violation:
                violations.append(lang_violation)

        passed = not any(v.severity == Severity.CRITICAL for v in violations) and not violations

        if not passed:
            logger.warning(
                "input_guard_violation",
                violation_count=len(violations),
                rules=[v.rule for v in violations],
            )

        return GuardrailResult(
            passed=passed,
            violations=violations,
            sanitized_text=sanitized if sanitized != text else None,
            pii_matches=pii_matches,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_injection(self, text: str) -> list[GuardrailViolation]:
        violations: list[GuardrailViolation] = []
        all_patterns = INJECTION_PATTERNS + self._extra_injection
        for pattern, label in all_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(
                    GuardrailViolation(
                        rule="prompt_injection",
                        message=f"Prompt injection detected: {label}",
                        severity=Severity.CRITICAL,
                        details={"pattern_label": label},
                    )
                )
        return violations

    def _detect_pii(self, text: str) -> list[PIIMatch]:
        matches: list[PIIMatch] = []
        for compiled, name in PII_PATTERNS:
            for m in compiled.finditer(text):
                matches.append(
                    PIIMatch(
                        pattern_name=name,
                        matched_text=m.group(),
                        start=m.start(),
                        end=m.end(),
                    )
                )
        return matches

    @staticmethod
    def _mask_pii(text: str, matches: list[PIIMatch]) -> str:
        """Replace PII matches with masked placeholders, processing right-to-left."""
        result = text
        for m in sorted(matches, key=lambda x: x.start, reverse=True):
            placeholder = f"[{m.pattern_name.upper()}]"
            result = result[: m.start] + placeholder + result[m.end :]
        return result

    def _check_language(self, text: str) -> GuardrailViolation | None:
        """Heuristic language check based on character patterns."""
        if not self._allowed_languages:
            return None

        detected: set[str] = set()
        for lang, pattern in _LANG_HINTS.items():
            if pattern.search(text):
                detected.add(lang)

        # If we couldn't detect any language, pass (don't block unknown scripts)
        if not detected:
            return None

        # If any detected language is allowed, pass
        if detected & set(self._allowed_languages):
            return None

        return GuardrailViolation(
            rule="language_check",
            message=f"Detected language(s) {detected} not in allowed: {self._allowed_languages}",
            severity=Severity.INFO,
            details={"detected": list(detected), "allowed": self._allowed_languages},
        )
