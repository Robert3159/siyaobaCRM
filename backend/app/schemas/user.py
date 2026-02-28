from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    """
    规则书 5.1：固定角色枚举，不可随意新增。
    PENDING_MEMBER：待审核，注册后未分配正式角色前使用，不能进入系统。
    """

    ADMIN = "ADMIN"
    SUB_ADMIN = "SUB_ADMIN"
    QGS_DIRECTOR = "QGS_DIRECTOR"
    QGS_LEADER = "QGS_LEADER"
    QGS_MEMBER = "QGS_MEMBER"
    HGS_DIRECTOR = "HGS_DIRECTOR"
    HGS_LEADER = "HGS_LEADER"
    HGS_MEMBER = "HGS_MEMBER"
    PENDING_MEMBER = "PENDING_MEMBER"


class CurrentUser(BaseModel):
    """
    规则书 4.1 中要求的 CurrentUser 定义。
    """

    id: int
    role: Role
    department_id: int | None
    team_id: int | None
    managed_team_ids: list[int] = Field(default_factory=list)
    is_admin: bool

