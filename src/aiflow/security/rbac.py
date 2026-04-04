"""Role-Based Access Control (RBAC) for AIFlow."""

from __future__ import annotations

from enum import StrEnum

import structlog

__all__ = ["Role", "Permission", "RBACManager"]

logger = structlog.get_logger(__name__)


class Role(StrEnum):
    """User roles."""

    ADMIN = "admin"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(StrEnum):
    """Available permissions."""

    # Workflow permissions
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_WRITE = "workflow:write"
    WORKFLOW_EXECUTE = "workflow:execute"
    WORKFLOW_DELETE = "workflow:delete"

    # Team permissions
    TEAM_READ = "team:read"
    TEAM_WRITE = "team:write"
    TEAM_DELETE = "team:delete"

    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"

    # Admin
    ADMIN_ALL = "admin:all"
    AUDIT_READ = "audit:read"
    SETTINGS_WRITE = "settings:write"


# Role -> permissions mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),  # All permissions
    Role.DEVELOPER: {
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_WRITE,
        Permission.WORKFLOW_EXECUTE,
        Permission.TEAM_READ,
        Permission.USER_READ,
        Permission.AUDIT_READ,
    },
    Role.OPERATOR: {
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_EXECUTE,
        Permission.TEAM_READ,
        Permission.USER_READ,
    },
    Role.VIEWER: {
        Permission.WORKFLOW_READ,
        Permission.TEAM_READ,
        Permission.USER_READ,
    },
}


class RBACManager:
    """Manages role-based access control."""

    def __init__(self) -> None:
        self._role_permissions = dict(ROLE_PERMISSIONS)

    def get_permissions(self, role: Role | str) -> set[Permission]:
        """Get all permissions for a role."""
        if isinstance(role, str):
            role = Role(role)
        return self._role_permissions.get(role, set())

    def check_permission(self, role: Role | str, permission: Permission | str) -> bool:
        """Check if a role has a specific permission."""
        if isinstance(role, str):
            role = Role(role)
        if isinstance(permission, str):
            permission = Permission(permission)
        permissions = self.get_permissions(role)
        return permission in permissions

    def has_any(self, role: Role | str, *permissions: Permission | str) -> bool:
        """Check if a role has any of the given permissions."""
        return any(self.check_permission(role, p) for p in permissions)

    def has_all(self, role: Role | str, *permissions: Permission | str) -> bool:
        """Check if a role has all of the given permissions."""
        return all(self.check_permission(role, p) for p in permissions)
