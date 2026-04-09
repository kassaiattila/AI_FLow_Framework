"""Training data schemas - Pydantic models for labeled email datasets.

Supports YAML and CSV formats for training data, with provenance
tracking (who labeled, how, when) and dataset operations (merge, split).
"""
from __future__ import annotations

import csv
import random
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

__all__ = [
    "TrainingExample",
    "TrainingDataset",
    "load_training_data",
    "save_training_data",
    "merge_datasets",
    "split_dataset",
]


class TrainingExample(BaseModel):
    """A single labeled email for ML training."""

    id: str
    subject: str = ""
    body: str = ""
    sender: str = ""
    intent: str  # intent_id from intents.json
    sub_intent: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "manual"  # manual | llm_labeled | production | corrected
    labeled_by: str = ""  # "human", "gpt-4o", "sklearn_v1"
    labeled_at: str = ""  # ISO timestamp
    notes: str = ""


class TrainingDataset(BaseModel):
    """Collection of labeled training examples with metadata."""

    schema_version: str = "1.0"
    name: str = "unnamed"
    intent_schema_version: str = "v1"
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    samples: list[TrainingExample] = []

    @property
    def intent_distribution(self) -> dict[str, int]:
        """Count samples per intent."""
        dist: dict[str, int] = {}
        for s in self.samples:
            dist[s.intent] = dist.get(s.intent, 0) + 1
        return dict(sorted(dist.items(), key=lambda x: -x[1]))

    @property
    def size(self) -> int:
        return len(self.samples)

    def validate_intents(self, valid_intents: list[str]) -> list[str]:
        """Return list of sample IDs with invalid intent values."""
        valid_set = set(valid_intents)
        return [s.id for s in self.samples if s.intent not in valid_set]

    def filter_by_confidence(self, min_confidence: float = 0.8) -> TrainingDataset:
        """Return new dataset with only high-confidence samples."""
        filtered = [s for s in self.samples if s.confidence >= min_confidence]
        return TrainingDataset(
            name=f"{self.name}_filtered_{min_confidence}",
            intent_schema_version=self.intent_schema_version,
            samples=filtered,
        )

    def get_texts_and_labels(self) -> tuple[list[str], list[str]]:
        """Return (texts, labels) tuple for sklearn training."""
        texts = [f"{s.subject} {s.body}".strip() for s in self.samples]
        labels = [s.intent for s in self.samples]
        return texts, labels


def load_training_data(path: Path) -> TrainingDataset:
    """Load training dataset from YAML or CSV file."""
    path = Path(path)
    if path.suffix in (".yaml", ".yml"):
        return _load_yaml(path)
    elif path.suffix == ".csv":
        return _load_csv(path)
    else:
        raise ValueError(f"Unsupported format: {path.suffix} (use .yaml or .csv)")


def save_training_data(
    dataset: TrainingDataset, path: Path, fmt: str = "yaml"
) -> None:
    """Save training dataset to YAML or CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "yaml":
        _save_yaml(dataset, path)
    elif fmt == "csv":
        _save_csv(dataset, path)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def merge_datasets(*datasets: TrainingDataset) -> TrainingDataset:
    """Merge multiple datasets, deduplicating by sample ID."""
    seen_ids: set[str] = set()
    merged: list[TrainingExample] = []
    for ds in datasets:
        for s in ds.samples:
            if s.id not in seen_ids:
                seen_ids.add(s.id)
                merged.append(s)
    return TrainingDataset(
        name="merged",
        samples=merged,
    )


def split_dataset(
    dataset: TrainingDataset,
    test_ratio: float = 0.2,
    seed: int = 42,
    stratify: bool = True,
) -> tuple[TrainingDataset, TrainingDataset]:
    """Split dataset into train and test sets.

    If stratify=True, maintains intent distribution in both sets.
    """
    if not stratify:
        samples = list(dataset.samples)
        random.Random(seed).shuffle(samples)
        split_idx = int(len(samples) * (1 - test_ratio))
        return (
            TrainingDataset(name=f"{dataset.name}_train", samples=samples[:split_idx]),
            TrainingDataset(name=f"{dataset.name}_test", samples=samples[split_idx:]),
        )

    # Stratified split
    by_intent: dict[str, list[TrainingExample]] = {}
    for s in dataset.samples:
        by_intent.setdefault(s.intent, []).append(s)

    train_samples: list[TrainingExample] = []
    test_samples: list[TrainingExample] = []
    rng = random.Random(seed)

    for _intent, samples in by_intent.items():
        rng.shuffle(samples)
        n_test = max(1, int(len(samples) * test_ratio))
        test_samples.extend(samples[:n_test])
        train_samples.extend(samples[n_test:])

    return (
        TrainingDataset(name=f"{dataset.name}_train", samples=train_samples),
        TrainingDataset(name=f"{dataset.name}_test", samples=test_samples),
    )


# --- Internal helpers ---


def _load_yaml(path: Path) -> TrainingDataset:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    samples = [TrainingExample(**s) for s in data.get("samples", [])]
    return TrainingDataset(
        name=data.get("name", path.stem),
        schema_version=data.get("schema_version", "1.0"),
        intent_schema_version=data.get("intent_schema_version", "v1"),
        created_at=data.get("created_at", ""),
        samples=samples,
    )


def _save_yaml(dataset: TrainingDataset, path: Path) -> None:
    data = {
        "schema_version": dataset.schema_version,
        "name": dataset.name,
        "intent_schema_version": dataset.intent_schema_version,
        "created_at": dataset.created_at,
        "samples": [s.model_dump(mode="json") for s in dataset.samples],
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _load_csv(path: Path) -> TrainingDataset:
    samples: list[TrainingExample] = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append(TrainingExample(
                id=row.get("id", ""),
                subject=row.get("subject", ""),
                body=row.get("body", ""),
                sender=row.get("sender", ""),
                intent=row.get("intent", "unknown"),
                sub_intent=row.get("sub_intent", ""),
                confidence=float(row.get("confidence", 1.0)),
                source=row.get("source", "csv_import"),
                labeled_by=row.get("labeled_by", ""),
            ))
    return TrainingDataset(name=path.stem, samples=samples)


def _save_csv(dataset: TrainingDataset, path: Path) -> None:
    fields = [
        "id", "subject", "body", "sender", "intent", "sub_intent",
        "confidence", "source", "labeled_by", "labeled_at", "notes",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for s in dataset.samples:
            writer.writerow(s.model_dump(mode="json", include=set(fields)))
