from __future__ import annotations

import os
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Protocol


SYSTEM_SENDER_IDS = {"0", 0, None, ""}
HANDLED_SYSTEM_PHRASES = (
    "conversacion recogida",
    "conversación recogida",
    "conversacion se asigno",
    "conversación se asignó",
    "se asigno al agente",
    "se asignó al agente",
    "invito a",
    "invitó a",
    "transferido",
    "transferida",
    "recogida",
    "recogido",
    "respondio",
    "respondió",
)

RUNTIME_CONFIG_LOCK = Lock()
RUNTIME_CONFIG_OVERRIDES: dict[str, str] = {}
EDITABLE_CONFIG_KEYS = {
    "BITRIX_ASSIGNMENT_STAGE_ID",
    "BITRIX_CATEGORY_ID",
    "BITRIX_AUTOMATION_MODE",
    "BITRIX_OPERATOR_USER_ID",
    "BITRIX_TARGET_STAGE_ID",
    "BITRIX_GREETING_MESSAGE",
    "BITRIX_ALLOWED_CONNECTORS",
    "BITRIX_SCAN_ENABLED",
    "BITRIX_SCAN_INTERVAL_SECONDS",
    "BITRIX_SCAN_LIMIT",
}
EDITABLE_SECRET_KEYS = {"BITRIX_WEBHOOK_BASE_URL"}


class BitrixApi(Protocol):
    def call(self, method: str, params: dict[str, Any]) -> Any:
        ...


@dataclass(frozen=True)
class BitrixAutomationConfig:
    webhook_base_url: str
    assignment_stage_id: str
    category_id: int | None
    operator_user_id: int | None
    target_stage_id: str | None
    greeting_message: str | None
    mode: str
    outbound_token: str | None
    allowed_connectors: set[str]
    scan_enabled: bool
    scan_interval_seconds: float
    scan_limit: int

    @classmethod
    def from_env(cls) -> "BitrixAutomationConfig":
        category_id = _optional_int(get_config_value("BITRIX_CATEGORY_ID"))
        operator_user_id = _optional_int(get_config_value("BITRIX_OPERATOR_USER_ID"))
        allowed_connectors = {
            value.strip()
            for value in get_config_value("BITRIX_ALLOWED_CONNECTORS", "").split(",")
            if value.strip()
        }
        return cls(
            webhook_base_url=get_config_value("BITRIX_WEBHOOK_BASE_URL", "").strip(),
            assignment_stage_id=get_config_value("BITRIX_ASSIGNMENT_STAGE_ID", "").strip(),
            category_id=category_id,
            operator_user_id=operator_user_id,
            target_stage_id=get_config_value("BITRIX_TARGET_STAGE_ID", "").strip() or None,
            greeting_message=(get_config_value("BITRIX_GREETING_MESSAGE", "").strip().replace("\\n", "\n") or None),
            mode=get_config_value("BITRIX_AUTOMATION_MODE", "dry_run").strip().lower(),
            outbound_token=get_config_value("BITRIX_OUTBOUND_TOKEN", "").strip() or None,
            allowed_connectors=allowed_connectors,
            scan_enabled=_optional_bool(get_config_value("BITRIX_SCAN_ENABLED"), default=True),
            scan_interval_seconds=_optional_float(get_config_value("BITRIX_SCAN_INTERVAL_SECONDS"), default=5.0),
            scan_limit=_optional_int(get_config_value("BITRIX_SCAN_LIMIT")) or 8,
        )

    @property
    def live(self) -> bool:
        return self.mode == "live"


@dataclass(frozen=True)
class ChatEligibility:
    eligible: bool
    reason: str
    chat_id: int
    session_id: str | None
    message_count: int
    internal_senders: tuple[str, ...] = ()


@dataclass(frozen=True)
class AutomationResult:
    status: str
    reason: str
    deal_id: int | None = None
    chat_id: int | None = None
    dry_run: bool = True
    actions: tuple[str, ...] = ()


class RecentEventCache:
    def __init__(self, ttl_seconds: int = 90) -> None:
        self.ttl_seconds = ttl_seconds
        self._seen: dict[str, float] = {}

    def seen(self, key: str) -> bool:
        now = time.monotonic()
        self._seen = {
            item_key: expires_at
            for item_key, expires_at in self._seen.items()
            if expires_at > now
        }
        if key in self._seen:
            return True
        self._seen[key] = now + self.ttl_seconds
        return False


def get_config_value(key: str, default: str = "") -> str:
    with RUNTIME_CONFIG_LOCK:
        if key in RUNTIME_CONFIG_OVERRIDES:
            return RUNTIME_CONFIG_OVERRIDES[key]
    return os.getenv(key, default)


def get_runtime_config_overrides() -> dict[str, str]:
    with RUNTIME_CONFIG_LOCK:
        return dict(RUNTIME_CONFIG_OVERRIDES)


def update_runtime_config_overrides(values: dict[str, Any]) -> dict[str, str]:
    allowed_keys = EDITABLE_CONFIG_KEYS | EDITABLE_SECRET_KEYS
    with RUNTIME_CONFIG_LOCK:
        for key, value in values.items():
            if key not in allowed_keys:
                continue
            text = "" if value is None else str(value)
            if key in EDITABLE_SECRET_KEYS and (not text or text.startswith("***") or "..." in text):
                continue
            RUNTIME_CONFIG_OVERRIDES[key] = text
        return dict(RUNTIME_CONFIG_OVERRIDES)


def clear_runtime_config_overrides() -> None:
    with RUNTIME_CONFIG_LOCK:
        RUNTIME_CONFIG_OVERRIDES.clear()


class BitrixOpenLineAutomation:
    def __init__(self, client: BitrixApi, config: BitrixAutomationConfig) -> None:
        self.client = client
        self.config = config

    def handle_deal(self, deal_id: int) -> AutomationResult:
        deal = self.get_deal(deal_id)
        if not self.deal_is_in_assignment(deal):
            return AutomationResult(
                status="ignored",
                reason="La negociacion no esta en ASIGNACION",
                deal_id=deal_id,
                dry_run=not self.config.live,
            )

        chats = self.get_deal_chats(deal_id)
        if not chats:
            return AutomationResult(
                status="ignored",
                reason="La negociacion no tiene chats vinculados",
                deal_id=deal_id,
                dry_run=not self.config.live,
            )

        rejected_reasons: list[str] = []
        for chat in chats:
            connector_id = str(chat.get("CONNECTOR_ID") or "")
            if self.config.allowed_connectors and connector_id not in self.config.allowed_connectors:
                rejected_reasons.append(f"Conector no permitido: {connector_id}")
                continue

            chat_id = int(chat["CHAT_ID"])
            eligibility = self.evaluate_chat(chat_id)
            if not eligibility.eligible:
                rejected_reasons.append(eligibility.reason)
                continue

            if not self.config.live:
                return AutomationResult(
                    status="candidate",
                    reason=eligibility.reason,
                    deal_id=deal_id,
                    chat_id=chat_id,
                    dry_run=True,
                    actions=("would_answer_dialog", "would_update_deal", "would_send_message"),
                )

            return self.take_chat(deal_id, chat_id)

        return AutomationResult(
            status="ignored",
            reason=rejected_reasons[0] if rejected_reasons else "Ningun chat vinculado cumple la condicion de nuevo real",
            deal_id=deal_id,
            dry_run=not self.config.live,
        )

    def scan_assignment(self, limit: int | None = None) -> list[AutomationResult]:
        deals = self.list_assignment_deals(limit or self.config.scan_limit)
        results: list[AutomationResult] = []
        for deal in deals:
            result = self.handle_deal(int(deal["id"]))
            results.append(result)
            if self.config.live and result.status == "claimed":
                break
        return results

    def list_assignment_deals(self, limit: int) -> list[dict[str, Any]]:
        filter_params: dict[str, Any] = {"=stageId": self.config.assignment_stage_id}
        if self.config.category_id is not None:
            filter_params["=categoryId"] = self.config.category_id

        result = self.client.call(
            "crm.item.list",
            {
                "entityTypeId": 2,
                "filter": filter_params,
                "select": ["id", "title", "stageId", "categoryId", "assignedById", "updatedTime"],
                "order": {"updatedTime": "DESC"},
            },
        )
        items = result.get("items", []) if isinstance(result, dict) else []
        return items[:limit]

    def handle_chat(self, chat_id: int, deal_id: int | None = None) -> AutomationResult:
        if deal_id is not None:
            return self.handle_deal(deal_id)

        eligibility = self.evaluate_chat(chat_id)
        if not eligibility.eligible:
            return AutomationResult(
                status="ignored",
                reason=eligibility.reason,
                chat_id=chat_id,
                dry_run=not self.config.live,
            )

        return AutomationResult(
            status="candidate",
            reason="Chat limpio, pero el evento no trajo deal_id para mover/asignar CRM",
            chat_id=chat_id,
            dry_run=True,
            actions=("needs_deal_id",),
        )

    def take_chat(self, deal_id: int, chat_id: int) -> AutomationResult:
        first_check = self.evaluate_chat(chat_id)
        if not first_check.eligible:
            return AutomationResult(
                status="race_lost",
                reason=first_check.reason,
                deal_id=deal_id,
                chat_id=chat_id,
                dry_run=False,
            )

        actions: list[str] = []
        self.client.call("imopenlines.operator.answer", {"CHAT_ID": chat_id})
        actions.append("answered_dialog")

        fields: dict[str, Any] = {}
        if self.config.operator_user_id is not None:
            fields["assignedById"] = self.config.operator_user_id
        if self.config.target_stage_id:
            fields["stageId"] = self.config.target_stage_id
        if fields:
            self.update_deal(deal_id, fields)
            actions.append("updated_deal")

        if self.config.greeting_message and self.config.operator_user_id is not None:
            self.send_openline_message(deal_id, chat_id)
            actions.append("sent_message")

        return AutomationResult(
            status="claimed",
            reason="Chat tomado correctamente",
            deal_id=deal_id,
            chat_id=chat_id,
            dry_run=False,
            actions=tuple(actions),
        )

    def get_deal(self, deal_id: int) -> dict[str, Any]:
        result = self.client.call("crm.item.get", {"entityTypeId": 2, "id": deal_id})
        if isinstance(result, dict) and "item" in result:
            return result["item"]
        return result or {}

    def update_deal(self, deal_id: int, fields: dict[str, Any]) -> None:
        self.client.call(
            "crm.item.update",
            {"entityTypeId": 2, "id": deal_id, "fields": fields},
        )

    def send_openline_message(self, deal_id: int, chat_id: int) -> None:
        message = self.config.greeting_message or ""
        user_id = self.config.operator_user_id
        if user_id is None or not message:
            return

        try:
            self.client.call(
                "imopenlines.crm.message.add",
                {
                    "CRM_ENTITY_TYPE": "deal",
                    "CRM_ENTITY": deal_id,
                    "USER_ID": user_id,
                    "CHAT_ID": chat_id,
                    "MESSAGE": message,
                },
            )
        except Exception:
            self.client.call(
                "im.message.add",
                {
                    "DIALOG_ID": f"chat{chat_id}",
                    "MESSAGE": message,
                },
            )

    def deal_is_in_assignment(self, deal: dict[str, Any]) -> bool:
        if str(deal.get("stageId") or "") != self.config.assignment_stage_id:
            return False
        if self.config.category_id is None:
            return True
        return int(deal.get("categoryId") or -1) == self.config.category_id

    def get_deal_chats(self, deal_id: int) -> list[dict[str, Any]]:
        result = self.client.call(
            "imopenlines.crm.chat.get",
            {
                "CRM_ENTITY_TYPE": "deal",
                "CRM_ENTITY": deal_id,
                "ACTIVE_ONLY": "N",
            },
        )
        return result or []

    def evaluate_chat(self, chat_id: int) -> ChatEligibility:
        history = self.client.call("imopenlines.session.history.get", {"CHAT_ID": chat_id})
        return evaluate_history(history or {}, chat_id)


def evaluate_history(history: dict[str, Any], chat_id: int) -> ChatEligibility:
    messages = history.get("message") or {}
    users = history.get("users") or {}
    chat = history.get("chat") or {}
    session_id = str(history.get("sessionId")) if history.get("sessionId") is not None else None
    internal_senders: set[str] = set()
    handled_marker_found = False

    active_internal_users = internal_chat_participants(history, users)
    if active_internal_users:
        return ChatEligibility(
            eligible=False,
            reason="Ya hay empleado/agente dentro del chat",
            chat_id=chat_id,
            session_id=session_id,
            message_count=len(messages),
            internal_senders=tuple(sorted(active_internal_users)),
        )

    for chat_info in chat.values():
        manager_list = chat_info.get("managerList") or []
        for manager_id in manager_list:
            user = users.get(str(manager_id))
            if user_is_internal_human(user):
                internal_senders.add(str(user.get("name") or manager_id))

    for message in messages.values():
        sender_id = message.get("senderid")
        text = normalize_text(message.get("textlegacy") or message.get("text"))

        if any(phrase in text for phrase in HANDLED_SYSTEM_PHRASES):
            handled_marker_found = True

        if sender_id in SYSTEM_SENDER_IDS:
            continue

        sender_key = str(sender_id)
        user = users.get(sender_key)
        if user_is_internal_human(user) and not message_is_hidden_system(message):
            internal_senders.add(str(user.get("name") or sender_key))

    if internal_senders:
        return ChatEligibility(
            eligible=False,
            reason="Ya hay mensaje de empleado/agente humano",
            chat_id=chat_id,
            session_id=session_id,
            message_count=len(messages),
            internal_senders=tuple(sorted(internal_senders)),
        )

    if handled_marker_found:
        return ChatEligibility(
            eligible=False,
            reason="El historial tiene señales de conversación ya atendida",
            chat_id=chat_id,
            session_id=session_id,
            message_count=len(messages),
        )

    return ChatEligibility(
        eligible=True,
        reason="Solo se detectan cliente/sistema; candidato para tomar",
        chat_id=chat_id,
        session_id=session_id,
        message_count=len(messages),
    )


def normalize_text(value: Any) -> str:
    return str(value or "").lower()


def user_is_internal_human(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    if user.get("bot") is True:
        return False
    if user.get("connector") is True:
        return False
    if str(user.get("type") or "").lower() in {"bot", "extranet"}:
        return False
    return bool(user.get("id"))


def message_is_hidden_system(message: dict[str, Any]) -> bool:
    params = message.get("params") or {}
    return params.get("class") == "bx-messenger-content-item-system"


def internal_chat_participants(history: dict[str, Any], users: dict[str, Any]) -> set[str]:
    internal_users: set[str] = set()
    user_in_chat = history.get("userInChat") or {}
    for chat_users in user_in_chat.values():
        if isinstance(chat_users, dict):
            iterable = chat_users.keys()
        else:
            iterable = chat_users or []
        for user_id in iterable:
            user = users.get(str(user_id))
            if user_is_internal_human(user):
                internal_users.add(str(user.get("name") or user_id))
    return internal_users


def _optional_int(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    return int(value)


def _optional_float(value: str | None, default: float) -> float:
    if not value or not value.strip():
        return default
    return float(value)


def _optional_bool(value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
