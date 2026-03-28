"""
@test_registry:
    suite: core-unit
    component: evaluation.datasets
    covers: [src/aiflow/evaluation/datasets.py]
    phase: 4
    priority: high
    estimated_duration_ms: 150
    requires_services: []
    tags: [evaluation, datasets, json, loading, merging]
"""
import json
from pathlib import Path

import pytest

from aiflow.evaluation.datasets import Dataset, DatasetManager, load_from_json, save_to_json
from aiflow.evaluation.framework import EvalCase


@pytest.fixture
def sample_dataset() -> Dataset:
    return Dataset(
        name="test-dataset",
        skill_name="classifier",
        test_type="unit",
        cases=[
            EvalCase(name="case-1", input_data={"text": "hello"}, expected_output="greeting"),
            EvalCase(name="case-2", input_data={"text": "bye"}, expected_output="farewell"),
        ],
    )


@pytest.fixture
def dataset_json(tmp_path: Path, sample_dataset: Dataset) -> Path:
    f = tmp_path / "dataset.json"
    data = sample_dataset.model_dump(mode="json")
    f.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return f


class TestDatasetModel:
    def test_create_full_dataset(self, sample_dataset: Dataset):
        assert sample_dataset.name == "test-dataset"
        assert sample_dataset.skill_name == "classifier"
        assert sample_dataset.test_type == "unit"
        assert len(sample_dataset.cases) == 2

    def test_create_minimal_dataset(self):
        ds = Dataset(name="empty")
        assert ds.name == "empty"
        assert ds.skill_name == ""
        assert ds.test_type == "unit"
        assert ds.cases == []

    def test_dataset_cases_are_eval_cases(self, sample_dataset: Dataset):
        for case in sample_dataset.cases:
            assert isinstance(case, EvalCase)


class TestLoadSaveJson:
    def test_load_from_json(self, dataset_json: Path):
        ds = load_from_json(dataset_json)
        assert ds.name == "test-dataset"
        assert len(ds.cases) == 2
        assert ds.cases[0].name == "case-1"

    def test_load_nonexistent_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_from_json(tmp_path / "missing.json")

    def test_load_invalid_json_raises(self, tmp_path: Path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid json}", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_from_json(f)

    def test_save_to_json(self, tmp_path: Path, sample_dataset: Dataset):
        out = tmp_path / "output" / "saved.json"
        save_to_json(sample_dataset, out)

        assert out.exists()
        loaded = load_from_json(out)
        assert loaded.name == sample_dataset.name
        assert len(loaded.cases) == len(sample_dataset.cases)

    def test_roundtrip(self, tmp_path: Path, sample_dataset: Dataset):
        f = tmp_path / "roundtrip.json"
        save_to_json(sample_dataset, f)
        loaded = load_from_json(f)
        assert loaded.model_dump() == sample_dataset.model_dump()


class TestDatasetManager:
    @pytest.fixture
    def manager(self) -> DatasetManager:
        m = DatasetManager()
        yield m
        m.clear()

    def test_add_and_get(self, manager: DatasetManager, sample_dataset: Dataset):
        manager.add(sample_dataset)
        retrieved = manager.get("test-dataset")
        assert retrieved.name == "test-dataset"

    def test_get_missing_raises(self, manager: DatasetManager):
        with pytest.raises(KeyError, match="not found"):
            manager.get("nonexistent")

    def test_list_datasets(self, manager: DatasetManager):
        manager.add(Dataset(name="ds-a"))
        manager.add(Dataset(name="ds-b"))
        assert sorted(manager.list_datasets()) == ["ds-a", "ds-b"]

    def test_load_from_file(self, manager: DatasetManager, dataset_json: Path):
        ds = manager.load(dataset_json)
        assert ds.name == "test-dataset"
        assert "test-dataset" in manager.list_datasets()

    def test_merge_datasets(self, manager: DatasetManager):
        ds1 = Dataset(
            name="alpha",
            cases=[EvalCase(name="a1", input_data={"x": 1})],
        )
        ds2 = Dataset(
            name="beta",
            cases=[
                EvalCase(name="b1", input_data={"x": 2}),
                EvalCase(name="b2", input_data={"x": 3}),
            ],
        )
        manager.add(ds1)
        manager.add(ds2)

        merged = manager.merge("combined", "alpha", "beta")
        assert merged.name == "combined"
        assert len(merged.cases) == 3
        assert "combined" in manager.list_datasets()
