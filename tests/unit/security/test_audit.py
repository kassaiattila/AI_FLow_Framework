"""
@test_registry:
    suite: security-unit
    component: security.audit
    covers: [src/aiflow/security/audit.py]
    phase: 7
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [security, audit, logging, compliance]
"""
import pytest
from datetime import datetime, timezone, timedelta
from aiflow.security.audit import AuditEntry, AuditAction, AuditLogger


class TestAuditAction:
    def test_workflow_run_value(self):
        assert AuditAction.workflow_run == "workflow_run"

    def test_workflow_create_value(self):
        assert AuditAction.workflow_create == "workflow_create"

    def test_skill_install_value(self):
        assert AuditAction.skill_install == "skill_install"

    def test_user_login_value(self):
        assert AuditAction.user_login == "user_login"

    def test_budget_change_value(self):
        assert AuditAction.budget_change == "budget_change"

    def test_data_redacted_value(self):
        assert AuditAction.data_redacted == "data_redacted"

    def test_from_string(self):
        assert AuditAction("user_login") == AuditAction.user_login
        assert AuditAction("workflow_run") == AuditAction.workflow_run


class TestAuditEntry:
    def test_create_entry(self):
        entry = AuditEntry(
            user_id="user-1",
            action=AuditAction.workflow_create,
            resource_type="workflow",
            resource_id="my-wf",
        )
        assert entry.user_id == "user-1"
        assert entry.action == AuditAction.workflow_create
        assert entry.resource_type == "workflow"
        assert entry.resource_id == "my-wf"
        assert entry.id is not None
        assert entry.timestamp is not None

    def test_entry_with_details(self):
        entry = AuditEntry(
            user_id="user-2",
            action=AuditAction.budget_change,
            resource_type="budget",
            details={"old": 100.0, "new": 200.0},
        )
        assert entry.details == {"old": 100.0, "new": 200.0}

    def test_entry_id_is_unique(self):
        e1 = AuditEntry(
            user_id="u1",
            action=AuditAction.user_login,
            resource_type="session",
        )
        e2 = AuditEntry(
            user_id="u1",
            action=AuditAction.user_login,
            resource_type="session",
        )
        assert e1.id != e2.id

    def test_default_details_empty(self):
        entry = AuditEntry(
            action=AuditAction.user_login,
            resource_type="session",
        )
        assert entry.details == {}


class TestAuditLogger:
    @pytest.fixture
    def audit_logger(self):
        return AuditLogger()

    def test_log_entry(self, audit_logger):
        entry = AuditEntry(
            user_id="user-1",
            action=AuditAction.workflow_create,
            resource_type="workflow",
        )
        returned = audit_logger.log(entry)
        assert returned is entry
        assert audit_logger.count() == 1

    def test_log_multiple(self, audit_logger):
        for i in range(5):
            audit_logger.log(
                AuditEntry(
                    user_id=f"user-{i}",
                    action=AuditAction.user_login,
                    resource_type="session",
                )
            )
        assert audit_logger.count() == 5

    def test_query_by_action(self, audit_logger):
        audit_logger.log(AuditEntry(user_id="u1", action=AuditAction.workflow_create, resource_type="workflow"))
        audit_logger.log(AuditEntry(user_id="u1", action=AuditAction.skill_install, resource_type="skill"))
        audit_logger.log(AuditEntry(user_id="u2", action=AuditAction.workflow_create, resource_type="workflow"))
        results = audit_logger.query(action=AuditAction.workflow_create)
        assert len(results) == 2
        assert all(e.action == AuditAction.workflow_create for e in results)

    def test_query_by_user(self, audit_logger):
        audit_logger.log(AuditEntry(user_id="alice", action=AuditAction.user_login, resource_type="session"))
        audit_logger.log(AuditEntry(user_id="bob", action=AuditAction.user_login, resource_type="session"))
        audit_logger.log(AuditEntry(user_id="alice", action=AuditAction.workflow_run, resource_type="workflow"))
        results = audit_logger.query(user_id="alice")
        assert len(results) == 2
        assert all(e.user_id == "alice" for e in results)

    def test_query_by_date_range(self, audit_logger):
        now = datetime.now(timezone.utc)
        old_entry = AuditEntry(
            user_id="u1",
            action=AuditAction.user_login,
            resource_type="session",
            timestamp=now - timedelta(days=10),
        )
        new_entry = AuditEntry(
            user_id="u1",
            action=AuditAction.workflow_run,
            resource_type="workflow",
            timestamp=now,
        )
        audit_logger.log(old_entry)
        audit_logger.log(new_entry)
        results = audit_logger.query(start_date=now - timedelta(days=1))
        assert len(results) == 1
        assert results[0].action == AuditAction.workflow_run

    def test_query_returns_empty_when_no_match(self, audit_logger):
        audit_logger.log(AuditEntry(user_id="u1", action=AuditAction.user_login, resource_type="session"))
        results = audit_logger.query(user_id="nonexistent")
        assert results == []

    def test_count_empty(self, audit_logger):
        assert audit_logger.count() == 0

    def test_clear_removes_all(self, audit_logger):
        audit_logger.log(AuditEntry(user_id="u1", action=AuditAction.user_login, resource_type="session"))
        audit_logger.log(AuditEntry(user_id="u2", action=AuditAction.user_login, resource_type="session"))
        assert audit_logger.count() == 2
        audit_logger.clear()
        assert audit_logger.count() == 0
