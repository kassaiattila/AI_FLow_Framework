"""Test dataset management for the evaluation framework.

Datasets are collections of EvalCases that can be loaded from and saved
to JSON files, organized by skill and test type.
"""
from __future__ import annotations

import json
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from aiflow.evaluation.framework import EvalCase

__all__ = ["Dataset", "DatasetManager", "load_from_json", "save_to_json"]

logger = structlog.get_logger(__name__)


class Dataset(BaseModel):
    """A named collection of evaluation test cases."""

    name: str
    skill_name: str = ""
    test_type: str = "unit"
    cases: list[EvalCase] = Field(default_factory=list)


def load_from_json(path: Path) -> Dataset:
    """Load a Dataset from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed Dataset instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in dataset file {path}: {exc}") from exc

    try:
        dataset = Dataset(**data)
    except Exception as exc:
        raise ValueError(f"Invalid dataset format in {path}: {exc}") from exc

    logger.info("dataset_loaded", name=dataset.name, cases=len(dataset.cases), path=str(path))
    return dataset


def save_to_json(dataset: Dataset, path: Path) -> None:
    """Save a Dataset to a JSON file.

    Args:
        dataset: Dataset to save.
        path: Output file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dataset.model_dump(mode="json")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("dataset_saved", name=dataset.name, cases=len(dataset.cases), path=str(path))


class DatasetManager:
    """Manages multiple datasets with load, list, and merge operations."""

    def __init__(self) -> None:
        self._datasets: dict[str, Dataset] = {}

    def load(self, path: Path) -> Dataset:
        """Load a dataset from JSON and register it.

        Args:
            path: Path to the JSON file.

        Returns:
            Loaded Dataset.
        """
        dataset = load_from_json(path)
        self._datasets[dataset.name] = dataset
        return dataset

    def add(self, dataset: Dataset) -> None:
        """Register a dataset directly.

        Args:
            dataset: Dataset instance to register.
        """
        self._datasets[dataset.name] = dataset

    def get(self, name: str) -> Dataset:
        """Get a registered dataset by name.

        Args:
            name: Dataset name.

        Returns:
            The Dataset.

        Raises:
            KeyError: If not found.
        """
        if name not in self._datasets:
            raise KeyError(f"Dataset '{name}' not found. Available: {list(self._datasets.keys())}")
        return self._datasets[name]

    def list_datasets(self) -> list[str]:
        """Return names of all registered datasets."""
        return list(self._datasets.keys())

    def merge(self, name: str, *dataset_names: str) -> Dataset:
        """Merge multiple datasets into a new one.

        Args:
            name: Name for the merged dataset.
            *dataset_names: Names of datasets to merge.

        Returns:
            New merged Dataset.

        Raises:
            KeyError: If any source dataset is not found.
        """
        merged_cases: list[EvalCase] = []
        for ds_name in dataset_names:
            ds = self.get(ds_name)
            merged_cases.extend(ds.cases)

        merged = Dataset(name=name, cases=merged_cases)
        self._datasets[name] = merged

        logger.info(
            "datasets_merged",
            name=name,
            sources=list(dataset_names),
            total_cases=len(merged_cases),
        )
        return merged

    def clear(self) -> None:
        """Remove all registered datasets (for testing)."""
        self._datasets.clear()
