"""Sklearn-based intent classifier - TF-IDF + LinearSVC pipeline.

Based on the CFPB reference pipeline (reference/cfpb_pipeline.py).
Uses a pre-trained joblib model if available, otherwise returns
low-confidence fallback predictions.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog

__all__ = ["SklearnClassifier"]

logger = structlog.get_logger(__name__)


class SklearnClassifier:
    """TF-IDF + LinearSVC intent classifier.

    Load a pre-trained sklearn pipeline from a joblib file.
    If no model file is available, returns low-confidence fallback.
    """

    def __init__(self, model_path: str | Path | None = None) -> None:
        self._model: Any | None = None
        self._model_path = Path(model_path) if model_path else None
        self._classes: list[str] = []
        self._loaded = False

        if self._model_path and self._model_path.exists():
            self._load_model()

    def _load_model(self) -> None:
        """Load the pre-trained sklearn pipeline from joblib."""
        try:
            import joblib

            self._model = joblib.load(self._model_path)
            # Extract class labels from the pipeline's classifier
            if hasattr(self._model, "classes_"):
                self._classes = list(self._model.classes_)
            self._loaded = True
            logger.info(
                "sklearn_model_loaded",
                path=str(self._model_path),
                classes=len(self._classes),
            )
        except Exception as e:
            logger.warning(
                "sklearn_model_load_failed",
                path=str(self._model_path),
                error=str(e),
            )
            self._model = None
            self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if a model is loaded and ready."""
        return self._loaded and self._model is not None

    def predict(self, text: str) -> dict[str, Any]:
        """Predict intent for a single text.

        Returns:
            {
                "intent": str,
                "confidence": float,
                "alternatives": [{"intent": str, "confidence": float}, ...]
            }
        """
        if not self.is_loaded:
            return self._fallback_predict(text)

        cleaned = self._clean_text(text)
        if not cleaned:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "alternatives": [],
            }

        try:
            # Try predict_proba first (available with CalibratedClassifierCV)
            if hasattr(self._model, "predict_proba"):
                return self._predict_with_proba(cleaned)
            else:
                # Simple predict without confidence
                prediction = self._model.predict([cleaned])[0]
                return {
                    "intent": str(prediction),
                    "confidence": 0.7,  # Default confidence for non-calibrated models
                    "alternatives": [],
                }
        except Exception as e:
            logger.error("sklearn_predict_failed", error=str(e))
            return self._fallback_predict(text)

    def _predict_with_proba(self, cleaned_text: str) -> dict[str, Any]:
        """Predict with probability estimates."""
        probas = self._model.predict_proba([cleaned_text])[0]
        classes = self._model.classes_

        # Sort by probability descending
        class_proba = sorted(
            zip(classes, probas, strict=False),
            key=lambda x: x[1],
            reverse=True,
        )

        top_intent = str(class_proba[0][0])
        top_confidence = round(float(class_proba[0][1]), 4)

        alternatives = [
            {"intent": str(cls), "confidence": round(float(prob), 4)}
            for cls, prob in class_proba[1:4]  # Top 3 alternatives
        ]

        return {
            "intent": top_intent,
            "confidence": top_confidence,
            "alternatives": alternatives,
        }

    def _fallback_predict(self, text: str) -> dict[str, Any]:
        """Keyword-based fallback when no model is loaded."""
        text_lower = text.lower()

        # Simple keyword matching as fallback
        keyword_map = {
            "complaint": ["reklamacio", "panasz", "elegedetlen", "complaint", "dissatisfied", "problem"],
            "claim": ["karbejelentes", "kar", "baleset", "lopas", "tuz", "claim", "damage", "accident"],
            "cancellation": ["lemondas", "felmondas", "torles", "megszuntetes", "cancel", "terminate"],
            "order": ["rendeles", "szerzodes", "megrendel", "igenyel", "order", "contract", "subscribe"],
            "support": ["nem mukodik", "hiba", "technikai", "segitseg", "error", "not working", "help"],
            "inquiry": ["kerdes", "erdekel", "informacio", "hogyan", "question", "information", "how"],
            "feedback": ["visszajelzes", "velemeny", "javaslat", "koszonom", "feedback", "thanks", "suggestion"],
        }

        best_intent = "inquiry"
        best_score = 0

        for intent, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_intent = intent

        confidence = min(0.4, best_score * 0.15) if best_score > 0 else 0.1

        logger.info(
            "sklearn_fallback_predict",
            intent=best_intent,
            confidence=confidence,
            keyword_matches=best_score,
        )

        return {
            "intent": best_intent,
            "confidence": round(confidence, 4),
            "alternatives": [],
        }

    @staticmethod
    def _clean_text(text: str) -> str:
        """Text preprocessing matching the CFPB pipeline."""
        return clean_text_for_ml(text)


def clean_text_for_ml(text: str) -> str:
    """Clean text for ML classification (shared between training and inference).

    Preserves Hungarian accented characters (á, é, ö, ü, ő, ű, etc.).
    Must be used identically in both training and prediction to avoid mismatch.
    """
    if not text or not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"x{2,}", "redacted", text)
    text = re.sub(r"[^a-z0-9\u00e0-\u017e\s]", " ", text)  # Keep accented chars
    text = re.sub(r"\s+", " ", text).strip()
    return text
