from __future__ import annotations

import os
from dataclasses import replace
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from address_ai.bitrix.automation import BitrixAutomationConfig, BitrixOpenLineAutomation
from address_ai.bitrix.client import BitrixClient, BitrixError


router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    verify_dashboard_access(request)
    return HTMLResponse(DASHBOARD_HTML)


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
        "outbound_token_enabled": bool(config.outbound_token),
        "allowed_connectors": sorted(config.allowed_connectors),
        "event_url": str(request.url_for("bitrix_event")),
        "health_url": str(request.url_for("api_health")),
        "dashboard_token_enabled": bool(os.getenv("BITRIX_DASHBOARD_TOKEN", "").strip()),
    }


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


DASHBOARD_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bitrix24 Bot</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101214;
      --panel: #171a1f;
      --panel-2: #1f232a;
      --text: #e9edf2;
      --muted: #9aa4b2;
      --line: #2b313a;
      --green: #36c27a;
      --yellow: #e0b84f;
      --red: #f06a6a;
      --blue: #5aa7ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      border-bottom: 1px solid var(--line);
      background: #0d0f12;
    }
    .bar, main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 18px 22px;
    }
    .bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .subtitle {
      margin-top: 4px;
      color: var(--muted);
      font-size: 13px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 10px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel);
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }
    .pill.ok { color: var(--green); border-color: rgba(54, 194, 122, 0.4); }
    .pill.warn { color: var(--yellow); border-color: rgba(224, 184, 79, 0.4); }
    .grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 14px;
      margin-top: 18px;
    }
    .panel {
      grid-column: span 6;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-width: 0;
    }
    .panel.wide { grid-column: span 12; }
    h2 {
      margin: 0 0 12px;
      font-size: 15px;
      font-weight: 650;
    }
    dl {
      display: grid;
      grid-template-columns: 180px minmax(0, 1fr);
      gap: 8px 12px;
      margin: 0;
      font-size: 13px;
    }
    dt { color: var(--muted); }
    dd { margin: 0; overflow-wrap: anywhere; }
    code {
      display: inline-block;
      max-width: 100%;
      padding: 2px 6px;
      border-radius: 6px;
      background: var(--panel-2);
      color: #d7e6ff;
      overflow-wrap: anywhere;
    }
    form {
      display: grid;
      grid-template-columns: 1fr 1fr auto;
      gap: 10px;
      align-items: end;
    }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
    }
    input {
      width: 100%;
      min-height: 40px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #111418;
      color: var(--text);
      padding: 8px 10px;
      font-size: 14px;
    }
    button {
      min-height: 40px;
      border: 1px solid rgba(90, 167, 255, 0.45);
      border-radius: 7px;
      background: #19324f;
      color: #edf6ff;
      padding: 8px 14px;
      font-weight: 650;
      cursor: pointer;
    }
    button:disabled { opacity: 0.55; cursor: wait; }
    pre {
      min-height: 120px;
      margin: 12px 0 0;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #0d0f12;
      color: #dfe7ef;
      overflow: auto;
      white-space: pre-wrap;
      font-size: 13px;
    }
    .steps {
      display: grid;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
      color: var(--muted);
      font-size: 13px;
    }
    .steps li {
      padding: 9px 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #12161b;
    }
    @media (max-width: 760px) {
      .bar { align-items: flex-start; flex-direction: column; }
      .panel, .panel.wide { grid-column: span 12; }
      form { grid-template-columns: 1fr; }
      dl { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div class="bar">
      <div>
        <h1>Bitrix24 Bot</h1>
        <div class="subtitle">Panel operativo para webhooks, pruebas y estado del servicio.</div>
      </div>
      <div id="mode" class="pill">Cargando</div>
    </div>
  </header>

  <main>
    <section class="grid">
      <div class="panel">
        <h2>Estado</h2>
        <dl id="status"></dl>
      </div>

      <div class="panel">
        <h2>URLs</h2>
        <dl id="urls"></dl>
      </div>

      <div class="panel wide">
        <h2>Prueba Manual</h2>
        <form id="check-form">
          <label>Deal ID
            <input id="deal-id" inputmode="numeric" placeholder="2804388">
          </label>
          <label>Chat ID
            <input id="chat-id" inputmode="numeric" placeholder="2758584">
          </label>
          <button id="check-button" type="submit">Probar</button>
        </form>
        <pre id="check-output">La prueba manual siempre corre en modo dry-run.</pre>
      </div>

      <div class="panel wide">
        <h2>Render</h2>
        <ul class="steps">
          <li>Tipo de servicio: Web Services.</li>
          <li>Root directory: apps/api.</li>
          <li>Build command: pip install -r requirements.txt.</li>
          <li>Start command: uvicorn address_ai.api.main:app --host 0.0.0.0 --port $PORT.</li>
          <li>Health check path: /api/health.</li>
        </ul>
      </div>
    </section>
  </main>

  <script>
    const params = new URLSearchParams(location.search);
    const token = params.get("token") || "";
    const headers = token ? {"x-dashboard-token": token} : {};

    function row(key, value) {
      return `<dt>${key}</dt><dd>${value || "<span style='color: var(--red)'>Falta</span>"}</dd>`;
    }

    async function loadStatus() {
      const response = await fetch("/api/bitrix/status", {headers});
      if (!response.ok) {
        document.querySelector("#mode").textContent = "Sin acceso";
        document.querySelector("#mode").className = "pill warn";
        document.querySelector("#status").innerHTML = row("Error", await response.text());
        return;
      }
      const data = await response.json();
      const mode = document.querySelector("#mode");
      mode.textContent = data.is_live ? "LIVE" : "DRY RUN";
      mode.className = data.is_live ? "pill warn" : "pill ok";

      document.querySelector("#status").innerHTML = [
        row("Modo", `<code>${data.mode}</code>`),
        row("Webhook Bitrix", data.webhook_configured ? `<code>${data.webhook_preview}</code>` : ""),
        row("Etapa ASIGNACION", data.assignment_stage_id ? `<code>${data.assignment_stage_id}</code>` : ""),
        row("Categoria", data.category_id ?? ""),
        row("Operador", data.operator_user_id ?? ""),
        row("Mover a etapa", data.target_stage_id ? `<code>${data.target_stage_id}</code>` : ""),
        row("Mensaje inicial", data.greeting_enabled ? "Configurado" : "Sin mensaje"),
        row("Token eventos", data.outbound_token_enabled ? "Configurado" : "Sin token"),
      ].join("");

      document.querySelector("#urls").innerHTML = [
        row("Eventos Bitrix", `<code>${data.event_url}</code>`),
        row("Health", `<code>${data.health_url}</code>`),
        row("Dashboard token", data.dashboard_token_enabled ? "Activado" : "Sin proteger"),
      ].join("");
    }

    document.querySelector("#check-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = document.querySelector("#check-button");
      const output = document.querySelector("#check-output");
      button.disabled = true;
      output.textContent = "Probando...";
      const body = {
        deal_id: document.querySelector("#deal-id").value.trim(),
        chat_id: document.querySelector("#chat-id").value.trim(),
      };
      try {
        const response = await fetch("/api/bitrix/check", {
          method: "POST",
          headers: {"content-type": "application/json", ...headers},
          body: JSON.stringify(body),
        });
        const data = await response.json();
        output.textContent = JSON.stringify(data, null, 2);
      } catch (error) {
        output.textContent = String(error);
      } finally {
        button.disabled = false;
      }
    });

    loadStatus();
  </script>
</body>
</html>
"""
