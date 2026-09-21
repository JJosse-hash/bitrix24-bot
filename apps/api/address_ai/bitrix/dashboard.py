from __future__ import annotations

import os
import pathlib
from dataclasses import replace
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from address_ai.bitrix.automation import (
    BitrixAutomationConfig,
    BitrixOpenLineAutomation,
    clear_runtime_config_overrides,
    get_runtime_config_overrides,
    update_runtime_config_overrides,
)
from address_ai.bitrix.client import BitrixClient, BitrixError
from address_ai.bitrix.scanner import scanner


router = APIRouter(tags=["dashboard"])

DASHBOARD_HTML_PATH = pathlib.Path(__file__).parent / "dashboard.html"


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    verify_dashboard_access(request)
    return HTMLResponse(
        content=DASHBOARD_HTML_PATH.read_text(),
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/api/bitrix/status")
def bitrix_status(request: Request) -> dict[str, Any]:
    verify_dashboard_access(request)
    config = BitrixAutomationConfig.from_env()
    return {
        "status": "ok",
        "mode": config.mode,
        "is_live": config.live,
        "webhook_configured": bool(config.webhook_base_url),
        "webhook_preview": mask_secret(config.webhook_base_url),
        "assignment_stage_id": config.assignment_stage_id or None,
        "category_id": config.category_id,
        "operator_user_id": config.operator_user_id,
        "target_stage_id": config.target_stage_id,
        "greeting_enabled": bool(config.greeting_message),
        "allowed_connectors": sorted(config.allowed_connectors),
        "scan_enabled": config.scan_enabled,
        "scan_interval_seconds": config.scan_interval_seconds,
        "scan_limit": config.scan_limit,
        "runtime_overrides": sorted(get_runtime_config_overrides().keys()),
        "event_url": str(request.url_for("bitrix_event")),
        "health_url": str(request.url_for("api_health")),
        "dashboard_token_enabled": bool(os.getenv("BITRIX_DASHBOARD_TOKEN", "").strip()),
    }


@router.get("/api/bitrix/settings")
def bitrix_settings(request: Request) -> dict[str, Any]:
    verify_dashboard_access(request)
    config = BitrixAutomationConfig.from_env()
    overrides = get_runtime_config_overrides()
    return {
        "values": {
            "BITRIX_WEBHOOK_BASE_URL": mask_secret(config.webhook_base_url) or "",
            "BITRIX_ASSIGNMENT_STAGE_ID": config.assignment_stage_id,
            "BITRIX_CATEGORY_ID": config.category_id,
            "BITRIX_AUTOMATION_MODE": config.mode,
            "BITRIX_OPERATOR_USER_ID": config.operator_user_id,
            "BITRIX_TARGET_STAGE_ID": config.target_stage_id or "",
            "BITRIX_GREETING_MESSAGE": (config.greeting_message or "").replace("\n", "\\n"),
            "BITRIX_ALLOWED_CONNECTORS": ",".join(sorted(config.allowed_connectors)),
            "BITRIX_SCAN_ENABLED": str(config.scan_enabled).lower(),
            "BITRIX_SCAN_INTERVAL_SECONDS": config.scan_interval_seconds,
            "BITRIX_SCAN_LIMIT": config.scan_limit,
        },
        "runtime_overrides": overrides,
        "note": "Los cambios del dashboard son en vivo. Para hacerlos permanentes tras redeploy, copialos a Environment Variables de Render.",
    }


@router.put("/api/bitrix/settings")
async def bitrix_settings_update(request: Request) -> dict[str, Any]:
    verify_dashboard_access(request)
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")
    update_runtime_config_overrides(body)
    return bitrix_settings(request)


@router.delete("/api/bitrix/settings")
def bitrix_settings_clear(request: Request) -> dict[str, Any]:
    verify_dashboard_access(request)
    clear_runtime_config_overrides()
    return bitrix_settings(request)


@router.get("/api/bitrix/scanner")
def bitrix_scanner_status(request: Request) -> dict[str, Any]:
    verify_dashboard_access(request)
    return scanner.snapshot()


@router.post("/api/bitrix/scan")
async def bitrix_scan_now(request: Request) -> dict[str, Any]:
    verify_dashboard_access(request)
    records = await scanner.run_once(source="manual")
    return {"records": [record.__dict__ for record in records], "scanner": scanner.snapshot()}


@router.post("/api/bitrix/scanner/pause")
def bitrix_scanner_pause(request: Request) -> dict[str, Any]:
    verify_dashboard_access(request)
    scanner.pause()
    return scanner.snapshot()


@router.post("/api/bitrix/scanner/resume")
def bitrix_scanner_resume(request: Request) -> dict[str, Any]:
    verify_dashboard_access(request)
    scanner.resume()
    return scanner.snapshot()


@router.post("/api/bitrix/check")
async def bitrix_check(request: Request) -> dict[str, Any]:
    verify_dashboard_access(request)
    body = await request.json()
    deal_id = parse_optional_int(body.get("deal_id"))
    chat_id = parse_optional_int(body.get("chat_id"))
    if deal_id is None and chat_id is None:
        raise HTTPException(status_code=400, detail="Send deal_id or chat_id")

    config = BitrixAutomationConfig.from_env()
    if not config.webhook_base_url:
        raise HTTPException(status_code=500, detail="BITRIX_WEBHOOK_BASE_URL is not configured")

    dry_config = replace(config, mode="dry_run")
    automation = BitrixOpenLineAutomation(BitrixClient(dry_config.webhook_base_url), dry_config)
    try:
        result = automation.handle_deal(deal_id) if deal_id is not None else automation.handle_chat(chat_id)  # type: ignore[arg-type]
    except BitrixError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return {
        "status": result.status,
        "reason": result.reason,
        "deal_id": result.deal_id,
        "chat_id": result.chat_id,
        "dry_run": True,
        "actions": result.actions,
    }


def verify_dashboard_access(request: Request) -> None:
    expected = os.getenv("BITRIX_DASHBOARD_TOKEN", "").strip()
    if not expected:
        return

    received = (
        request.headers.get("x-dashboard-token")
        or request.query_params.get("token")
        or request.cookies.get("bitrix_dashboard_token")
        or ""
    )
    if received != expected:
        raise HTTPException(status_code=401, detail="Dashboard token required")


def parse_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def mask_secret(value: str) -> str | None:
    if not value:
        return None
    if len(value) <= 18:
        return "***"
    return f"{value[:16]}...{value[-6:]}"
