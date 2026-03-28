"""
@test_registry:
    suite: engine-unit
    component: engine.checkpoint
    covers: [src/aiflow/engine/checkpoint.py]
    phase: 2
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [engine, checkpoint, resume, state]
"""
from aiflow.engine.checkpoint import Checkpoint, CheckpointManager


class TestCheckpoint:
    def test_create(self):
        cp = Checkpoint(
            workflow_run_id="run-001",
            step_name="extract",
            step_index=2,
            completed_steps=["classify", "extract"],
            step_outputs={"classify": {"category": "process"}},
        )
        assert cp.step_name == "extract"
        assert cp.version == 1
        assert len(cp.completed_steps) == 2

    def test_to_dict_and_back(self):
        cp = Checkpoint(
            workflow_run_id="run-002",
            step_name="review",
            step_index=3,
            version=3,
            completed_steps=["a", "b", "c"],
            step_outputs={"a": {"x": 1}},
            accumulated_cost_usd=0.05,
        )
        d = cp.to_dict()
        assert d["step_name"] == "review"
        assert d["version"] == 3

        restored = Checkpoint.from_dict(d)
        assert restored.step_name == "review"
        assert restored.accumulated_cost_usd == 0.05
        assert restored.completed_steps == ["a", "b", "c"]


class TestCheckpointManager:
    def test_save_and_get_latest(self):
        mgr = CheckpointManager()
        cp1 = Checkpoint(workflow_run_id="run-1", step_name="a", step_index=0, version=1)
        cp2 = Checkpoint(workflow_run_id="run-1", step_name="b", step_index=1, version=2)
        mgr.save(cp1)
        mgr.save(cp2)
        latest = mgr.get_latest("run-1")
        assert latest is not None
        assert latest.step_name == "b"
        assert latest.version == 2

    def test_get_latest_no_checkpoints(self):
        mgr = CheckpointManager()
        assert mgr.get_latest("nonexistent") is None

    def test_get_by_step(self):
        mgr = CheckpointManager()
        mgr.save(Checkpoint(workflow_run_id="r1", step_name="a", step_index=0, version=1))
        mgr.save(Checkpoint(workflow_run_id="r1", step_name="b", step_index=1, version=2))
        result = mgr.get_by_step("r1", "a")
        assert result is not None
        assert result.step_name == "a"

    def test_get_by_step_not_found(self):
        mgr = CheckpointManager()
        assert mgr.get_by_step("r1", "missing") is None

    def test_get_all_ordered(self):
        mgr = CheckpointManager()
        mgr.save(Checkpoint(workflow_run_id="r1", step_name="b", step_index=1, version=2))
        mgr.save(Checkpoint(workflow_run_id="r1", step_name="a", step_index=0, version=1))
        all_cps = mgr.get_all("r1")
        assert all_cps[0].version == 1
        assert all_cps[1].version == 2

    def test_clear(self):
        mgr = CheckpointManager()
        mgr.save(Checkpoint(workflow_run_id="r1", step_name="a", step_index=0))
        mgr.clear("r1")
        assert mgr.get_latest("r1") is None

    def test_clear_all(self):
        mgr = CheckpointManager()
        mgr.save(Checkpoint(workflow_run_id="r1", step_name="a", step_index=0))
        mgr.save(Checkpoint(workflow_run_id="r2", step_name="b", step_index=0))
        mgr.clear_all()
        assert mgr.get_latest("r1") is None
        assert mgr.get_latest("r2") is None
