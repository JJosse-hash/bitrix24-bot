from __future__ import annotations

import os
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
      --panel-2: #20252c;
      --panel-3: #12161b;
      --text: #e9edf2;
      --muted: #9aa4b2;
      --line: #2c333d;
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
      background: #0c0e11;
    }
    .bar, main {
      max-width: 1220px;
      margin: 0 auto;
      padding: 18px 22px;
    }
    .bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0; }
    .subtitle { margin-top: 4px; color: var(--muted); font-size: 13px; }
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
    .pill.ok { color: var(--green); border-color: rgba(54, 194, 122, 0.45); }
    .pill.live { color: var(--red); border-color: rgba(240, 106, 106, 0.5); }
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
    .panel.third { grid-column: span 4; }
    h2 { margin: 0 0 12px; font-size: 15px; font-weight: 650; }
    dl {
      display: grid;
      grid-template-columns: 170px minmax(0, 1fr);
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
    .toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
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
    button.secondary { background: #151a20; border-color: var(--line); color: var(--text); }
    button:disabled { opacity: 0.55; cursor: wait; }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 10px;
      background: var(--panel-3);
      min-height: 68px;
    }
    .metric span { display: block; color: var(--muted); font-size: 12px; }
    .metric strong { display: block; margin-top: 6px; font-size: 18px; overflow-wrap: anywhere; }
    form, .settings-grid {
      display: grid;
      grid-template-columns: 1fr 1fr auto;
      gap: 10px;
      align-items: end;
    }
    .settings-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
      align-items: start;
    }
    label { display: grid; gap: 6px; color: var(--muted); font-size: 13px; }
    input, select, textarea {
      width: 100%;
      min-height: 40px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #111418;
      color: var(--text);
      padding: 8px 10px;
      font-size: 14px;
    }
    textarea { min-height: 94px; resize: vertical; grid-column: span 2; }
    pre {
      min-height: 96px;
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
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
      text-align: left;
      vertical-align: top;
    }
    th { color: var(--muted); font-weight: 600; }
    td { overflow-wrap: anywhere; }
    .status-candidate, .status-claimed { color: var(--green); }
    .status-error, .status-race_lost, .status-race_lost_after_answer { color: var(--red); }
    .status-ignored { color: var(--muted); }
    @media (max-width: 760px) {
      .bar { align-items: flex-start; flex-direction: column; }
      .panel, .panel.wide { grid-column: span 12; }
      .metrics { grid-template-columns: 1fr 1fr; }
      form, dl, .settings-grid { grid-template-columns: 1fr; }
      textarea { grid-column: span 1; }
    }
  </style>
</head>
<body>
  <header>
    <div class="bar">
      <div>
        <h1>Bitrix24 Bot</h1>
        <div class="subtitle">Escaneo automatico de ASIGNACION, filtro de chats nuevos y operacion segura.</div>
      </div>
      <div id="mode" class="pill">Cargando</div>
    </div>
  </header>

  <main>
    <section class="grid">
      <div class="panel">
        <h2>Configuracion</h2>
        <dl id="status"></dl>
      </div>

      <div class="panel">
        <h2>Servicio</h2>
        <dl id="urls"></dl>
      </div>

      <div class="panel wide">
        <h2>Configuracion En Vivo</h2>
        <div class="settings-grid">
          <label>Modo
            <select id="setting-mode">
              <option value="dry_run">dry_run</option>
              <option value="live">live</option>
            </select>
          </label>
          <label>Etapa ASIGNACION
            <input id="setting-assignment-stage" placeholder="C16:UC_GIKKS8">
          </label>
          <label>Etapa ASIGNADO
            <input id="setting-target-stage" placeholder="C16:UC_L8W7U1">
          </label>
          <label>Categoria
            <input id="setting-category" inputmode="numeric" placeholder="16">
          </label>
          <label>Operador
            <input id="setting-operator" inputmode="numeric" placeholder="2381716">
          </label>
          <label>Intervalo scanner
            <input id="setting-interval" inputmode="decimal" placeholder="5">
          </label>
          <label>Limite por vuelta
            <input id="setting-limit" inputmode="numeric" placeholder="8">
          </label>
          <label>Scanner activo
            <select id="setting-scan-enabled">
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
          <label>Conectores permitidos
            <input id="setting-connectors" placeholder="opcional">
          </label>
          <label>Webhook Bitrix
            <input id="setting-webhook" placeholder="pega URL completa solo si quieres cambiarla">
          </label>
          <label>Mensaje automatico
            <textarea id="setting-message"></textarea>
          </label>
          <div style="align-self:end">
            <button id="save-settings" type="button">Guardar</button>
            <button id="clear-settings" class="secondary" type="button">Limpiar overrides</button>
          </div>
        </div>
        <pre id="settings-output">Los cambios aqui son inmediatos. Para hacerlos permanentes, copialos despues a Render.</pre>
      </div>

      <div class="panel wide">
        <h2>Scanner Automatico</h2>
        <div class="toolbar">
          <button id="scan-now" type="button">Escanear ahora</button>
          <button id="pause-scanner" class="secondary" type="button">Pausar</button>
          <button id="resume-scanner" class="secondary" type="button">Reanudar</button>
        </div>
        <div class="metrics">
          <div class="metric"><span>Worker</span><strong id="scanner-running">-</strong></div>
          <div class="metric"><span>Estado</span><strong id="scanner-state">-</strong></div>
          <div class="metric"><span>Intervalo</span><strong id="scanner-interval">-</strong></div>
          <div class="metric"><span>Candidatos</span><strong id="scanner-candidates">-</strong></div>
        </div>
        <pre id="scanner-error">Sin errores recientes.</pre>
      </div>

      <div class="panel wide">
        <h2>Candidatos Actuales</h2>
        <div style="overflow:auto">
          <table>
            <thead>
              <tr>
                <th>Detectado</th>
                <th>Deal</th>
                <th>Chat</th>
                <th>Motivo</th>
                <th>Acciones en live</th>
              </tr>
            </thead>
            <tbody id="current-candidates"></tbody>
          </table>
        </div>
      </div>

      <div class="panel wide">
        <h2>Historial Reciente</h2>
        <div style="overflow:auto">
          <table>
            <thead>
              <tr>
                <th>Hora</th>
                <th>Estado</th>
                <th>Deal</th>
                <th>Chat</th>
                <th>Motivo</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody id="recent-results"></tbody>
          </table>
        </div>
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
    </section>
  </main>

  <script>
    const params = new URLSearchParams(location.search);
    const token = params.get("token") || "";
    const headers = token ? {"x-dashboard-token": token} : {};

    function row(key, value) {
      return `<dt>${key}</dt><dd>${value || "<span style='color: var(--red)'>Falta</span>"}</dd>`;
    }

    function fmt(value) {
      return value === null || value === undefined || value === "" ? "-" : value;
    }

    function fmtTime(value) {
      if (!value) return "-";
      try { return new Date(value).toLocaleTimeString(); } catch { return value; }
    }

    async function loadStatus() {
      const response = await fetch("/api/bitrix/status", {headers});
      if (!response.ok) {
        document.querySelector("#mode").textContent = "Sin acceso";
        document.querySelector("#status").innerHTML = row("Error", await response.text());
        return;
      }
      const data = await response.json();
      const mode = document.querySelector("#mode");
      mode.textContent = data.is_live ? "LIVE" : "DRY RUN";
      mode.className = data.is_live ? "pill live" : "pill ok";

      document.querySelector("#status").innerHTML = [
        row("Modo", `<code>${data.mode}</code>`),
        row("Webhook Bitrix", data.webhook_configured ? `<code>${data.webhook_preview}</code>` : ""),
        row("ASIGNACION", data.assignment_stage_id ? `<code>${data.assignment_stage_id}</code>` : ""),
        row("Categoria", data.category_id ?? ""),
        row("Operador", data.operator_user_id ?? ""),
        row("Mover a ASIGNADO", data.target_stage_id ? `<code>${data.target_stage_id}</code>` : ""),
        row("Mensaje inicial", data.greeting_enabled ? "Configurado" : "Sin mensaje"),
        row("Scanner", data.scan_enabled ? `Cada ${data.scan_interval_seconds}s, limite ${data.scan_limit}` : "Desactivado"),
        row("Overrides", (data.runtime_overrides || []).join(", ") || "Ninguno"),
      ].join("");

      document.querySelector("#urls").innerHTML = [
        row("Health", `<code>${data.health_url}</code>`),
        row("Eventos", `<code>${data.event_url}</code>`),
        row("Dashboard token", data.dashboard_token_enabled ? "Activado" : "Sin proteger"),
      ].join("");
    }

    function renderScanner(data) {
      document.querySelector("#scanner-running").textContent = data.task_running ? "Activo" : "Detenido";
      document.querySelector("#scanner-state").textContent = data.paused ? "Pausado" : (data.enabled ? "Escaneando" : "Desactivado");
      document.querySelector("#scanner-interval").textContent = `${data.interval_seconds}s`;
      document.querySelector("#scanner-candidates").textContent = (data.current_candidates || []).length;
      document.querySelector("#scanner-error").textContent = data.last_error || "Sin errores recientes.";

      const currentRows = (data.current_candidates || []).map((item) => `
        <tr>
          <td>${fmtTime(item.timestamp)}</td>
          <td>${fmt(item.deal_id)}</td>
          <td>${fmt(item.chat_id)}</td>
          <td>${item.reason}</td>
          <td>${(item.actions || []).join(", ") || "-"}</td>
        </tr>
      `).join("");
      document.querySelector("#current-candidates").innerHTML = currentRows || "<tr><td colspan='5'>No hay candidatos actuales.</td></tr>";

      const rows = (data.recent || []).map((item) => `
        <tr>
          <td>${fmtTime(item.timestamp)}</td>
          <td class="status-${item.status}">${item.status}</td>
          <td>${fmt(item.deal_id)}</td>
          <td>${fmt(item.chat_id)}</td>
          <td>${item.reason}</td>
          <td>${(item.actions || []).join(", ") || "-"}</td>
        </tr>
      `).join("");
      document.querySelector("#recent-results").innerHTML = rows || "<tr><td colspan='6'>Sin resultados todavia.</td></tr>";
    }

    async function loadScanner() {
      const response = await fetch("/api/bitrix/scanner", {headers});
      if (response.ok) renderScanner(await response.json());
    }

    async function loadSettings() {
      const response = await fetch("/api/bitrix/settings", {headers});
      if (!response.ok) return;
      const data = await response.json();
      const values = data.values || {};
      document.querySelector("#setting-mode").value = values.BITRIX_AUTOMATION_MODE || "dry_run";
      document.querySelector("#setting-assignment-stage").value = values.BITRIX_ASSIGNMENT_STAGE_ID || "";
      document.querySelector("#setting-target-stage").value = values.BITRIX_TARGET_STAGE_ID || "";
      document.querySelector("#setting-category").value = values.BITRIX_CATEGORY_ID ?? "";
      document.querySelector("#setting-operator").value = values.BITRIX_OPERATOR_USER_ID ?? "";
      document.querySelector("#setting-interval").value = values.BITRIX_SCAN_INTERVAL_SECONDS ?? "";
      document.querySelector("#setting-limit").value = values.BITRIX_SCAN_LIMIT ?? "";
      document.querySelector("#setting-scan-enabled").value = String(values.BITRIX_SCAN_ENABLED ?? "true");
      document.querySelector("#setting-connectors").value = values.BITRIX_ALLOWED_CONNECTORS || "";
      document.querySelector("#setting-webhook").value = values.BITRIX_WEBHOOK_BASE_URL || "";
      document.querySelector("#setting-message").value = values.BITRIX_GREETING_MESSAGE || "";
    }

    async function saveSettings() {
      const button = document.querySelector("#save-settings");
      const output = document.querySelector("#settings-output");
      button.disabled = true;
      output.textContent = "Guardando...";
      const body = {
        BITRIX_AUTOMATION_MODE: document.querySelector("#setting-mode").value,
        BITRIX_ASSIGNMENT_STAGE_ID: document.querySelector("#setting-assignment-stage").value.trim(),
        BITRIX_TARGET_STAGE_ID: document.querySelector("#setting-target-stage").value.trim(),
        BITRIX_CATEGORY_ID: document.querySelector("#setting-category").value.trim(),
        BITRIX_OPERATOR_USER_ID: document.querySelector("#setting-operator").value.trim(),
        BITRIX_SCAN_INTERVAL_SECONDS: document.querySelector("#setting-interval").value.trim(),
        BITRIX_SCAN_LIMIT: document.querySelector("#setting-limit").value.trim(),
        BITRIX_SCAN_ENABLED: document.querySelector("#setting-scan-enabled").value,
        BITRIX_ALLOWED_CONNECTORS: document.querySelector("#setting-connectors").value.trim(),
        BITRIX_GREETING_MESSAGE: document.querySelector("#setting-message").value,
      };
      const webhookValue = document.querySelector("#setting-webhook").value.trim();
      if (webhookValue && !webhookValue.includes("...")) {
        body.BITRIX_WEBHOOK_BASE_URL = webhookValue;
      }
      try {
        const response = await fetch("/api/bitrix/settings", {
          method: "PUT",
          headers: {"content-type": "application/json", ...headers},
          body: JSON.stringify(body),
        });
        const data = await response.json();
        output.textContent = JSON.stringify(data, null, 2);
        await loadStatus();
        await loadScanner();
      } catch (error) {
        output.textContent = String(error);
      } finally {
        button.disabled = false;
      }
    }

    async function clearSettings() {
      const output = document.querySelector("#settings-output");
      output.textContent = "Limpiando overrides...";
      const response = await fetch("/api/bitrix/settings", {method: "DELETE", headers});
      const data = await response.json();
      output.textContent = JSON.stringify(data, null, 2);
      await loadSettings();
      await loadStatus();
      await loadScanner();
    }

    async function postScanner(path) {
      const response = await fetch(path, {method: "POST", headers});
      if (response.ok) {
        const data = await response.json();
        renderScanner(data.scanner || data);
      }
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
        output.textContent = JSON.stringify(await response.json(), null, 2);
      } catch (error) {
        output.textContent = String(error);
      } finally {
        button.disabled = false;
      }
    });

    document.querySelector("#scan-now").addEventListener("click", async () => postScanner("/api/bitrix/scan"));
    document.querySelector("#pause-scanner").addEventListener("click", async () => postScanner("/api/bitrix/scanner/pause"));
    document.querySelector("#resume-scanner").addEventListener("click", async () => postScanner("/api/bitrix/scanner/resume"));
    document.querySelector("#save-settings").addEventListener("click", saveSettings);
    document.querySelector("#clear-settings").addEventListener("click", clearSettings);

    loadStatus();
    loadScanner();
    loadSettings();
    setInterval(loadStatus, 15000);
    setInterval(loadScanner, 4000);
  </script>
</body>
</html>
"""
