"""
@test_registry:
    suite: security-unit
    component: security.rbac
    covers: [src/aiflow/security/rbac.py]
    phase: 5
    priority: critical
    estimated_duration_ms: 100
    requires_services: []
    tags: [security, rbac, roles, permissions]
"""
import pytest

from aiflow.security.rbac import Permission, RBACManager, Role


class TestRole:
    def test_role_values(self):
        assert Role.ADMIN == "admin"
        assert Role.DEVELOPER == "developer"
        assert Role.OPERATOR == "operator"
        assert Role.VIEWER == "viewer"

    def test_role_from_string(self):
        assert Role("admin") == Role.ADMIN


class TestPermission:
    def test_permission_values(self):
        assert Permission.WORKFLOW_READ == "workflow:read"
        assert Permission.WORKFLOW_WRITE == "workflow:write"
        assert Permission.ADMIN_ALL == "admin:all"


class TestRBACManager:
    @pytest.fixture
    def rbac(self):
        return RBACManager()

    def test_admin_has_all_permissions(self, rbac):
        perms = rbac.get_permissions(Role.ADMIN)
        assert Permission.ADMIN_ALL in perms
        assert Permission.WORKFLOW_READ in perms
        assert Permission.WORKFLOW_WRITE in perms
        assert Permission.WORKFLOW_DELETE in perms
        assert Permission.USER_DELETE in perms

    def test_viewer_read_only(self, rbac):
        perms = rbac.get_permissions(Role.VIEWER)
        assert Permission.WORKFLOW_READ in perms
        assert Permission.TEAM_READ in perms
        assert Permission.WORKFLOW_WRITE not in perms
        assert Permission.WORKFLOW_DELETE not in perms
        assert Permission.ADMIN_ALL not in perms

    def test_developer_permissions(self, rbac):
        perms = rbac.get_permissions(Role.DEVELOPER)
        assert Permission.WORKFLOW_READ in perms
        assert Permission.WORKFLOW_WRITE in perms
        assert Permission.WORKFLOW_EXECUTE in perms
        assert Permission.WORKFLOW_DELETE not in perms

    def test_check_permission_true(self, rbac):
        assert rbac.check_permission(Role.ADMIN, Permission.ADMIN_ALL) is True

    def test_check_permission_false(self, rbac):
        assert rbac.check_permission(Role.VIEWER, Permission.WORKFLOW_WRITE) is False

    def test_check_permission_with_strings(self, rbac):
        assert rbac.check_permission("admin", "admin:all") is True
        assert rbac.check_permission("viewer", "workflow:write") is False

    def test_has_any(self, rbac):
        assert rbac.has_any(Role.VIEWER, Permission.WORKFLOW_READ, Permission.WORKFLOW_WRITE) is True
        assert rbac.has_any(Role.VIEWER, Permission.WORKFLOW_WRITE, Permission.ADMIN_ALL) is False

    def test_has_all(self, rbac):
        assert rbac.has_all(Role.ADMIN, Permission.WORKFLOW_READ, Permission.ADMIN_ALL) is True
        assert rbac.has_all(Role.VIEWER, Permission.WORKFLOW_READ, Permission.WORKFLOW_WRITE) is False
