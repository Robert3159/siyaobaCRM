import asyncio
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

QGS_AUTHOR_KEY = "qgs_author"

FIELD_CANDIDATES: dict[str, tuple[str, ...]] = {
    "country": (
        "country",
        "nation",
        "country_name",
        "countryName",
        "nationality",
        "国家",
        "国籍",
    ),
    "age": (
        "age",
        "age_years",
        "age_year",
        "ageYears",
        "years",
        "年龄",
        "年纪",
        "岁",
        "年龄段",
    ),
    "server": (
        "server",
        "server_name",
        "serverName",
        "server_id",
        "serverId",
        "zone",
        "zone_id",
        "qufu",
        "region",
        "region_name",
        "area",
        "区服",
        "服务器",
        "服务器名",
        "大区",
        "区",
        "服",
    ),
    "token": (
        "token",
        "token_code",
        "tokenCode",
        "invite_code",
        "invitation_code",
        "邀请码",
        "激活码",
        "兑换码",
        "token码",
    ),
}

FIELD_LABEL_HINTS: dict[str, tuple[str, ...]] = {
    "country": ("country", "国家", "国籍"),
    "age": ("age", "年龄", "岁", "年纪", "年龄段"),
    "server": ("server", "zone", "region", "qufu", "区服", "服务器", "大区"),
    "token": ("token", "invite", "code", "邀请码", "激活码", "兑换码", "token码"),
}


@dataclass
class NotificationMessage:
    id: str
    player_id: int
    submitter: str
    country: str
    age: str
    server: str
    token: str
    summary: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().lower()


def _normalize_text(value: Any) -> str:
    text = _normalize_key(value)
    if not text:
        return ""
    return "".join(ch for ch in text if ch.isalnum())


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("label", "name", "value", "id", "code"):
            if key in value and value[key] is not None:
                return _format_value(value[key])
        try:
            return json.dumps(value, ensure_ascii=False)
        except TypeError:
            return str(value)
    if isinstance(value, (list, tuple, set)):
        items = [_format_value(item) for item in value]
        items = [item for item in items if item]
        return ", ".join(items)
    return str(value)


def _trim_value(value: str, max_len: int = 120) -> str:
    if len(value) <= max_len:
        return value
    return f"{value[:max_len]}..."


def _find_value_by_normalized_key(payload: Any, target_key: str) -> Any:
    if not target_key:
        return None

    stack: list[Any] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if _normalize_key(key) == target_key:
                    return value
            for value in current.values():
                if isinstance(value, (dict, list, tuple, set)):
                    stack.append(value)
            continue

        if isinstance(current, (list, tuple, set)):
            for item in current:
                if isinstance(item, (dict, list, tuple, set)):
                    stack.append(item)
    return None


def _is_label_matched(field_key: str, field_label: str, hints: tuple[str, ...]) -> bool:
    key_norm = _normalize_text(field_key)
    label_norm = _normalize_text(field_label)

    for hint in hints:
        hint_norm = _normalize_text(hint)
        if not hint_norm:
            continue
        if key_norm and (key_norm == hint_norm or hint_norm in key_norm):
            return True
        if label_norm and (label_norm == hint_norm or hint_norm in label_norm):
            return True
    return False


def _build_schema_candidates(schema_fields: list[dict[str, Any]] | None) -> dict[str, tuple[str, ...]]:
    extras: dict[str, list[str]] = {name: [] for name in FIELD_CANDIDATES}

    for field in schema_fields or []:
        if not isinstance(field, dict):
            continue

        key = str(field.get("key") or "").strip()
        if not key:
            continue
        label = str(field.get("label") or "").strip()

        for name, hints in FIELD_LABEL_HINTS.items():
            if _is_label_matched(key, label, hints):
                extras[name].append(key)

    return {
        name: FIELD_CANDIDATES[name] + tuple(extras[name])
        for name in FIELD_CANDIDATES
    }


def _extract_fields(content: dict[str, Any], submitter: str, schema_fields: list[dict[str, Any]] | None = None) -> dict[str, str]:
    normalized = {_normalize_key(k): v for k, v in (content or {}).items()}
    merged_candidates = _build_schema_candidates(schema_fields)

    def pick(keys: tuple[str, ...]) -> str:
        for key in keys:
            normalized_key = _normalize_key(key)
            value = normalized.get(normalized_key)
            if value is None:
                value = _find_value_by_normalized_key(content, normalized_key)
            formatted = _format_value(value)
            if formatted:
                return _trim_value(formatted)
        return ""

    return {
        "submitter": _trim_value(submitter),
        "country": pick(merged_candidates["country"]),
        "age": pick(merged_candidates["age"]),
        "server": pick(merged_candidates["server"]),
        "token": pick(merged_candidates["token"]),
    }


def build_notification_message(
    content: dict[str, Any],
    submitter: str,
    player_id: int,
    schema_fields: list[dict[str, Any]] | None = None,
) -> NotificationMessage:
    fields = _extract_fields(content, submitter, schema_fields=schema_fields)
    fallback = "-"
    summary = " | ".join(
        [
            fields["submitter"] or fallback,
            fields["country"] or fallback,
            fields["age"] or fallback,
            fields["server"] or fallback,
            fields["token"] or fallback,
        ]
    )
    return NotificationMessage(
        id=str(uuid.uuid4()),
        player_id=player_id,
        submitter=fields["submitter"] or fallback,
        country=fields["country"] or fallback,
        age=fields["age"] or fallback,
        server=fields["server"] or fallback,
        token=fields["token"] or fallback,
        summary=summary,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


class NotificationHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._messages: list[NotificationMessage] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        await self._send_snapshot(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def _send_snapshot(self, websocket: WebSocket) -> None:
        async with self._lock:
            payload = {"type": "snapshot", "messages": [m.to_dict() for m in self._messages]}
        await websocket.send_json(payload)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not self._connections:
            return
        stale: list[WebSocket] = []
        for conn in list(self._connections):
            try:
                await conn.send_json(payload)
            except Exception:
                stale.append(conn)
        for conn in stale:
            await self.disconnect(conn)

    async def enqueue_message(self, message: NotificationMessage) -> None:
        async with self._lock:
            self._messages.append(message)
        await self.broadcast({"type": "new", "message": message.to_dict()})

    async def claim_message(self, message_id: str) -> NotificationMessage | None:
        removed: NotificationMessage | None = None
        async with self._lock:
            for idx, msg in enumerate(self._messages):
                if msg.id == message_id:
                    removed = self._messages.pop(idx)
                    break

        return removed

    async def restore_message(self, message: NotificationMessage) -> None:
        async with self._lock:
            self._messages.insert(0, message)


notification_hub = NotificationHub()
