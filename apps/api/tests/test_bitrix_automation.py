from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from address_ai.api.main import app
from address_ai.bitrix.automation import (
    BitrixAutomationConfig,
    BitrixOpenLineAutomation,
    evaluate_history,
)


def test_evaluate_history_accepts_customer_and_system_only():
    result = evaluate_history(
        {
            "sessionId": 123,
            "message": {
                "1": {"senderid": "0", "text": "Nuevo contacto creado"},
                "2": {"senderid": "99", "text": "Quiero internet"},
            },
            "users": {
                "99": {
                    "id": "99",
                    "name": "Cliente",
                    "type": "extranet",
                    "connector": True,
                    "bot": False,
                }
            },
        },
        chat_id=456,
    )

    assert result.eligible is True
    assert result.reason == "Solo se detectan cliente/sistema; candidato para tomar"


def test_evaluate_history_rejects_internal_agent_message():
    result = evaluate_history(
        {
            "message": {
                "1": {"senderid": "10", "text": "Hola, soy tu asesora"},
                "2": {"senderid": "99", "text": "Gracias"},
            },
            "users": {
                "10": {"id": "10", "name": "Asesora", "type": "user", "bot": False},
                "99": {
                    "id": "99",
                    "name": "Cliente",
                    "type": "extranet",
                    "connector": True,
                    "bot": False,
                },
            },
        },
        chat_id=456,
    )

    assert result.eligible is False
    assert result.reason == "Ya hay mensaje de empleado/agente humano"
    assert result.internal_senders == ("Asesora",)


def test_evaluate_history_rejects_handled_marker():
    result = evaluate_history(
        {
            "message": {
                "1": {"senderid": "0", "text": "La conversación se asignó al agente"},
                "2": {"senderid": "99", "text": "Quiero internet"},
            },
            "users": {
                "99": {
                    "id": "99",
                    "name": "Cliente",
                    "type": "extranet",
                    "connector": True,
                    "bot": False,
                }
            },
        },
        chat_id=456,
    )

    assert result.eligible is False
    assert result.reason == "El historial tiene señales de conversación ya atendida"


def test_handle_deal_dry_run_reports_candidate():
    client = FakeBitrixClient(
        {
            "crm.item.get": {"item": {"id": 2804388, "stageId": "C16:UC_GIKKS8", "categoryId": 16}},
            "imopenlines.crm.chat.get": [{"CHAT_ID": 2758584, "CONNECTOR_ID": "whatsapp"}],
            "imopenlines.session.history.get": {
                "message": {"1": {"senderid": "99", "text": "Quiero internet"}},
                "users": {
                    "99": {
                        "id": "99",
                        "name": "Cliente",
                        "type": "extranet",
                        "connector": True,
                        "bot": False,
                    }
                },
            },
        }
    )
    config = BitrixAutomationConfig(
        webhook_base_url="https://example.bitrix24.mx/rest/1/key",
        assignment_stage_id="C16:UC_GIKKS8",
        category_id=16,
        operator_user_id=2381716,
        target_stage_id="C16:UC_L8W7U1",
        greeting_message="Hola",
        mode="dry_run",
        outbound_token=None,
        allowed_connectors=set(),
        scan_enabled=True,
        scan_interval_seconds=5,
        scan_limit=8,
    )

    result = BitrixOpenLineAutomation(client, config).handle_deal(2804388)

    assert result.status == "candidate"
    assert result.actions == ("would_answer_dialog", "would_update_deal", "would_send_message")
    assert client.called_methods == [
        "crm.item.get",
        "imopenlines.crm.chat.get",
        "imopenlines.session.history.get",
    ]


def test_bitrix_event_endpoint_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("BITRIX_WEBHOOK_BASE_URL", "https://example.bitrix24.mx/rest/1/key")
    monkeypatch.setenv("BITRIX_ASSIGNMENT_STAGE_ID", "C16:UC_GIKKS8")
    monkeypatch.setenv("BITRIX_OUTBOUND_TOKEN", "secret")

    response = TestClient(app).post(
        "/api/bitrix/events",
        data={
            "event": "ONCRMDEALADD",
            "data[FIELDS][ID]": "2804388",
            "auth[application_token]": "wrong",
        },
    )

    assert response.status_code == 403


class FakeBitrixClient:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.called_methods: list[str] = []

    def call(self, method: str, params: dict[str, Any]) -> Any:
        self.called_methods.append(method)
        return self.responses[method]
