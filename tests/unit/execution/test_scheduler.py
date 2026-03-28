"""
@test_registry:
    suite: execution-unit
    component: execution.scheduler
    covers: [src/aiflow/execution/scheduler.py]
    phase: 7
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [execution, scheduler, trigger, cron]
"""
import pytest
from datetime import datetime, timezone
from aiflow.execution.scheduler import (
    TriggerType,
    ScheduleDefinition,
    CronTrigger,
    Scheduler,
)


class TestTriggerType:
    def test_cron_value(self):
        assert TriggerType.cron == "cron"

    def test_event_value(self):
        assert TriggerType.event == "event"

    def test_webhook_value(self):
        assert TriggerType.webhook == "webhook"

    def test_manual_value(self):
        assert TriggerType.manual == "manual"

    def test_from_string(self):
        assert TriggerType("cron") == TriggerType.cron
        assert TriggerType("event") == TriggerType.event


class TestScheduleDefinition:
    def test_create_cron_schedule(self):
        sd = ScheduleDefinition(
            name="nightly-report",
            workflow_name="generate-report",
            trigger_type=TriggerType.cron,
            cron_expression="0 0 * * *",
        )
        assert sd.name == "nightly-report"
        assert sd.workflow_name == "generate-report"
        assert sd.trigger_type == TriggerType.cron
        assert sd.cron_expression == "0 0 * * *"
        assert sd.enabled is True

    def test_create_event_schedule(self):
        sd = ScheduleDefinition(
            name="on-upload",
            workflow_name="process-doc",
            trigger_type=TriggerType.event,
            event_pattern="document.uploaded",
        )
        assert sd.trigger_type == TriggerType.event
        assert sd.event_pattern == "document.uploaded"

    def test_default_enabled(self):
        sd = ScheduleDefinition(
            name="test",
            workflow_name="wf",
            trigger_type=TriggerType.cron,
            cron_expression="* * * * *",
        )
        assert sd.enabled is True

    def test_default_input_data_empty(self):
        sd = ScheduleDefinition(
            name="test",
            workflow_name="wf",
            trigger_type=TriggerType.manual,
        )
        assert sd.input_data == {}

    def test_default_priority(self):
        sd = ScheduleDefinition(
            name="test",
            workflow_name="wf",
            trigger_type=TriggerType.manual,
        )
        assert sd.priority == 0


class TestCronTrigger:
    def test_wildcard_fires_always(self):
        trigger = CronTrigger("* * * * *")
        assert trigger.should_fire() is True

    def test_specific_minute_match(self):
        trigger = CronTrigger("30 * * * *")
        dt = datetime(2026, 3, 28, 10, 30, 0, tzinfo=timezone.utc)
        assert trigger.should_fire(dt) is True

    def test_specific_minute_no_match(self):
        trigger = CronTrigger("30 * * * *")
        dt = datetime(2026, 3, 28, 10, 15, 0, tzinfo=timezone.utc)
        assert trigger.should_fire(dt) is False

    def test_invalid_expression_raises(self):
        with pytest.raises(ValueError, match="5 fields"):
            CronTrigger("* * *")

    def test_expression_property(self):
        trigger = CronTrigger("0 12 * * *")
        assert trigger.expression == "0 12 * * *"


class TestScheduler:
    @pytest.fixture
    def scheduler(self):
        return Scheduler()

    @pytest.fixture
    def sample_schedule(self):
        return ScheduleDefinition(
            name="my-schedule",
            workflow_name="test-wf",
            trigger_type=TriggerType.cron,
            cron_expression="0 * * * *",
        )

    def test_add_schedule(self, scheduler, sample_schedule):
        scheduler.add_schedule(sample_schedule)
        assert scheduler.get_schedule("my-schedule") is not None

    def test_add_duplicate_name_raises(self, scheduler, sample_schedule):
        scheduler.add_schedule(sample_schedule)
        with pytest.raises(ValueError, match="already exists"):
            scheduler.add_schedule(sample_schedule)

    def test_remove_schedule(self, scheduler, sample_schedule):
        scheduler.add_schedule(sample_schedule)
        scheduler.remove_schedule("my-schedule")
        with pytest.raises(KeyError):
            scheduler.get_schedule("my-schedule")

    def test_remove_nonexistent_raises(self, scheduler):
        with pytest.raises(KeyError, match="not found"):
            scheduler.remove_schedule("nonexistent")

    def test_list_schedules(self, scheduler):
        for i in range(3):
            sd = ScheduleDefinition(
                name=f"sched-{i}",
                workflow_name=f"wf-{i}",
                trigger_type=TriggerType.cron,
                cron_expression="0 * * * *",
            )
            scheduler.add_schedule(sd)
        result = scheduler.list_schedules()
        assert len(result) == 3

    def test_get_existing(self, scheduler, sample_schedule):
        scheduler.add_schedule(sample_schedule)
        found = scheduler.get_schedule("my-schedule")
        assert found.name == "my-schedule"
        assert found.workflow_name == "test-wf"

    def test_get_nonexistent_raises(self, scheduler):
        with pytest.raises(KeyError, match="not found"):
            scheduler.get_schedule("nonexistent")

    def test_enable_schedule(self, scheduler, sample_schedule):
        sample_schedule.enabled = False
        scheduler.add_schedule(sample_schedule)
        scheduler.enable_schedule("my-schedule")
        sched = scheduler.get_schedule("my-schedule")
        assert sched.enabled is True

    def test_disable_schedule(self, scheduler, sample_schedule):
        scheduler.add_schedule(sample_schedule)
        scheduler.disable_schedule("my-schedule")
        sched = scheduler.get_schedule("my-schedule")
        assert sched.enabled is False

    def test_count_property(self, scheduler, sample_schedule):
        assert scheduler.count == 0
        scheduler.add_schedule(sample_schedule)
        assert scheduler.count == 1
