from pydantic import BaseModel


class CurrentUser(BaseModel):
    """
    规则书 4.1 中要求的 CurrentUser 定义。
    """

    id: int
    role: str
    department_id: int | None
    team_id: int | None
    is_admin: bool

