"""
@test_registry:
    suite: integration-ingestion
    component: ingestion.parsers.docling_parser (FU-4 warmup real-path)
    covers: [src/aiflow/ingestion/parsers/docling_parser.py]
    phase: sprint-o-fu-4
    priority: high
    estimated_duration_ms: 90000
    requires_services: []
    tags: [integration, ingestion, docling, warmup, sprint-o, fu-4]

Sprint O FU-4 — asserts the warmup actually moves the cost: a second
``parse()`` on the warmed instance completes meaningfully faster than
the very first parse would have absorbing the model load.

Skipped automatically when docling or reportlab is unavailable — those
environments already don't need warmup.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from aiflow.ingestion.parsers.docling_parser import DoclingParser

pytestmark = pytest.mark.integration


def _minimal_pdf() -> Path:
    """Write a 1-page PDF to tmp and return its path."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab missing — warmup speedup test requires it")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fp:
        c = canvas.Canvas(fp.name, pagesize=A4)
        c.setFont("Helvetica", 11)
        c.drawString(72, 750, "FU-4 integration — second parse after warmup.")
        c.showPage()
        c.save()
        return Path(fp.name)


class TestWarmupSpeedup:
    """Warmup demonstrably moves the cold-start cost to startup time."""

    def test_subsequent_parse_faster_than_warmup(self) -> None:
        parser = DoclingParser()

        # Try the warmup. Skip gracefully if docling itself isn't installed.
        warmup = parser.warmup()
        if not warmup.warmed:
            pytest.skip(f"warmup failed: {warmup.reason}")

        pdf = _minimal_pdf()
        try:
            # Second parse on the same instance — converter is hot.
            t0 = time.perf_counter()
            result = parser.parse(pdf)
            second_elapsed = time.perf_counter() - t0
        finally:
            pdf.unlink(missing_ok=True)

        assert result.text
        # The warmup should absorb the model-load cost (usually ~10-70 s
        # depending on hardware); a subsequent parse should complete in
        # a fraction of that. We assert a loose lower bound so the test
        # is robust across slow CI runners: "at least 20% faster".
        speedup_ratio = warmup.elapsed_seconds / max(second_elapsed, 0.01)
        assert speedup_ratio >= 1.2, (
            f"Warmup did not produce a measurable speedup on second parse: "
            f"warmup={warmup.elapsed_seconds:.2f}s vs "
            f"second_parse={second_elapsed:.2f}s "
            f"(ratio={speedup_ratio:.2f}x, expected >= 1.2x)"
        )
