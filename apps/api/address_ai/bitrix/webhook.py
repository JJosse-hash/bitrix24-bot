from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request

from address_ai.bitrix.automation import (
    AutomationResult,
    BitrixAutomationConfig,
    BitrixOpenLineAutomation,
    RecentEventCache,
)
from address_ai.bitrix.client import BitrixClient, BitrixError

logger = logging.getLogger("address-ai.bitrix")
router = APIRouter(prefix="/api/bitrix", tags=["bitrix"])
event_cache = RecentEventCache()


@router.get("/health")
def health() -> dict[str, str]:
    config = BitrixAutomationConfig.from_env()
    return {
        "status": "ok",
        "mode": config.mode,
        "assignment_stage_id": config.assignment_stage_id or "missing",
    }


@router.post("/events")
async def bitrix_event(request: Request) -> dict[str, Any]:
    config = BitrixAutomationConfig.from_env()
    if not config.webhook_base_url:
        raise HTTPException(status_code=500, detail="BITRIX_WEBHOOK_BASE_URL is not configured")
    if not config.assignment_stage_id:
        raise HTTPException(status_code=500, detail="BITRIX_ASSIGNMENT_STAGE_ID is not configured")

    payload = await parse_bitrix_payload(request)
    verify_outbound_token(payload, config)

    event_name = str(payload.get("event") or payload.get("EVENT") or "")
    deal_id = extract_first_int(
        payload,
        (
            "data[FIELDS][ID]",
            "data[fields][ID]",
            "FIELDS[ID]",
            "deal_id",
            "DEAL_ID",
            "CRM_ENTITY",
            "crm_entity",
        ),
    )
    chat_id = extract_first_int(
        payload,
        (
            "data[PARAMS][CHAT_ID]",
            "data[params][CHAT_ID]",
            "data[FIELDS][CHAT_ID]",
            "CHAT_ID",
            "chat_id",
        ),
    )

    cache_key = f"{event_name}:{deal_id or ''}:{chat_id or ''}:{payload.get('ts') or ''}"
    if event_cache.seen(cache_key):
        return {"status": "duplicate_ignored", "event": event_name, "dry_run": not config.live}

    automation = BitrixOpenLineAutomation(BitrixClient(config.webhook_base_url), config)
    try:
        if deal_id is not None:
            result = automation.handle_deal(deal_id)
        elif chat_id is not None:
            result = automation.handle_chat(chat_id)
        else:
            result = AutomationResult(
                status="ignored",
                reason="El evento no trajo deal_id ni chat_id",
                dry_run=not config.live,
            )
    except BitrixError as error:
        logger.exception("bitrix.event.failed")
        raise HTTPException(status_code=502, detail=str(error)) from error

    logger.info(
        {
            "event": "bitrix.event.processed",
            "bitrix_event": event_name,
            "status": result.status,
            "reason": result.reason,
            "deal_id": result.deal_id,
            "chat_id": result.chat_id,
            "dry_run": result.dry_run,
            "actions": result.actions,
        }
    )
    return {
        "status": result.status,
        "reason": result.reason,
        "event": event_name,
        "deal_id": result.deal_id,
        "chat_id": result.chat_id,
        "dry_run": result.dry_run,
        "actions": result.actions,
    }


async def parse_bitrix_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        return flatten_json(body)

    raw_body = (await request.body()).decode("utf-8")
    parsed = parse_qs(raw_body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def flatten_json(payload: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in payload.items():
        path = f"{prefix}[{key}]" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(flatten_json(value, path))
        else:
            flat[path] = value
            if not prefix:
                flat[str(key)] = value
    return flat


def verify_outbound_token(payload: dict[str, Any], config: BitrixAutomationConfig) -> None:
    if not config.outbound_token:
        return
    token = str(
        payload.get("auth[application_token]")
        or payload.get("AUTH[APPLICATION_TOKEN]")
        or payload.get("application_token")
        or ""
    )
    if token != config.outbound_token:
        raise HTTPException(status_code=403, detail="Invalid Bitrix outbound token")


def extract_first_int(payload: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = payload.get(key)
        if value in (None, ""):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None
