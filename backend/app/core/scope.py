from enum import Enum
from typing import Any

from app.schemas.user import CurrentUser, Role


class DataScope(str, Enum):
    """Visibility scope levels."""

    SELF = "SELF"
    TEAM = "TEAM"
    DEPARTMENT = "DEPARTMENT"
    ALL = "ALL"


def get_data_scope_for_role(role: Role) -> DataScope:
    """Map role to default data scope."""
    if role == Role.PENDING_MEMBER:
        return DataScope.SELF
    if role in (Role.ADMIN, Role.SUB_ADMIN):
        return DataScope.ALL
    if role in (Role.QGS_DIRECTOR, Role.HGS_DIRECTOR):
        return DataScope.DEPARTMENT
    if role in (Role.QGS_LEADER, Role.HGS_LEADER):
        return DataScope.TEAM
    if role in (Role.QGS_MEMBER, Role.HGS_MEMBER):
        return DataScope.SELF
    return DataScope.SELF


def build_scope_filter(user: CurrentUser, resource: str) -> dict[str, Any]:
    """Build SQLAlchemy filter kwargs for row-level visibility."""
    if resource == "project":
        return {}

    scope = get_data_scope_for_role(user.role)

    if scope == DataScope.ALL:
        return {}

    def _self() -> dict[str, Any]:
        return {"owner_id": user.id}

    def _team() -> dict[str, Any]:
        if user.team_id is None:
            return {"owner_id": -1}
        return {"team_id": user.team_id}

    def _department() -> dict[str, Any]:
        if user.department_id is None:
            return {"owner_id": -1}
        return {"department_id": user.department_id}

    for res in ("customer", "project", "player"):
        if resource == res:
            if scope == DataScope.SELF:
                return _self()
            if scope == DataScope.TEAM:
                return _team()
            if scope == DataScope.DEPARTMENT:
                return _department()
            return {"owner_id": -1}

    return {"owner_id": user.id}
