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
      --bg: #0f1115;
      --surface: #151922;
      --surface-2: #1b212b;
      --surface-3: #10141b;
      --line: #2b3441;
      --line-soft: #202833;
      --text: #eef3f8;
      --muted: #94a3b8;
      --blue: #60a5fa;
      --cyan: #2dd4bf;
      --green: #35c981;
      --amber: #f2b84b;
      --red: #fb7185;
      --violet: #a78bfa;
      --shadow: 0 20px 60px rgba(0, 0, 0, 0.28);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      min-width: 320px;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }
    button, input, select, textarea { font: inherit; }
    header {
      position: sticky;
      top: 0;
      z-index: 10;
      border-bottom: 1px solid var(--line);
      background: rgba(15, 17, 21, 0.96);
      backdrop-filter: blur(14px);
    }
    .wrap {
      width: min(1440px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      display: grid;
      grid-template-columns: minmax(260px, 1fr) auto;
      gap: 18px;
      align-items: center;
      padding: 18px 0;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
      min-width: 0;
    }
    .mark {
      display: grid;
      place-items: center;
      width: 40px;
      height: 40px;
      border: 1px solid rgba(96, 165, 250, 0.5);
      border-radius: 8px;
      background: #142033;
      color: var(--blue);
      font-weight: 800;
      letter-spacing: 0;
    }
    h1 { margin: 0; font-size: 19px; line-height: 1.2; }
    .subtitle {
      margin-top: 3px;
      color: var(--muted);
      font-size: 13px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .header-actions {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
    }
    main { padding: 22px 0 36px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 14px;
      align-items: start;
    }
    .panel {
      grid-column: span 6;
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }
    .panel.full { grid-column: span 12; }
    .panel.third { grid-column: span 4; }
    .panel-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line-soft);
    }
    h2 {
      margin: 0;
      font-size: 14px;
      font-weight: 750;
      letter-spacing: 0;
    }
    .panel-body { padding: 16px; }
    .kpis {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .kpi {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 14px;
      min-height: 96px;
    }
    .kpi small {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }
    .kpi strong {
      display: block;
      margin-top: 10px;
      font-size: clamp(21px, 2.1vw, 28px);
      line-height: 1.1;
      overflow-wrap: anywhere;
    }
    .kpi span {
      display: block;
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 26px;
      max-width: 100%;
      padding: 3px 9px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: var(--surface-2);
      color: var(--muted);
      font-size: 12px;
      font-weight: 750;
      line-height: 1.2;
      white-space: nowrap;
    }
    .badge.live, .badge.error { color: var(--red); border-color: rgba(251, 113, 133, 0.45); background: rgba(251, 113, 133, 0.08); }
    .badge.ok, .badge.claimed, .badge.candidate { color: var(--green); border-color: rgba(53, 201, 129, 0.45); background: rgba(53, 201, 129, 0.08); }
    .badge.warn { color: var(--amber); border-color: rgba(242, 184, 75, 0.5); background: rgba(242, 184, 75, 0.08); }
    .badge.info { color: var(--blue); border-color: rgba(96, 165, 250, 0.45); background: rgba(96, 165, 250, 0.08); }
    .badge.violet { color: var(--violet); border-color: rgba(167, 139, 250, 0.45); background: rgba(167, 139, 250, 0.08); }
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    button {
      min-height: 38px;
      border: 1px solid rgba(96, 165, 250, 0.55);
      border-radius: 7px;
      background: #173256;
      color: #f3f8ff;
      padding: 8px 13px;
      font-size: 13px;
      font-weight: 750;
      cursor: pointer;
    }
    button.secondary {
      background: var(--surface-3);
      border-color: var(--line);
      color: var(--text);
    }
    button.danger {
      background: rgba(251, 113, 133, 0.12);
      border-color: rgba(251, 113, 133, 0.45);
      color: #ffdbe1;
    }
    button:disabled { opacity: 0.55; cursor: wait; }
    dl {
      display: grid;
      grid-template-columns: 150px minmax(0, 1fr);
      gap: 9px 12px;
      margin: 0;
      font-size: 13px;
    }
    dt { color: var(--muted); }
    dd { margin: 0; overflow-wrap: anywhere; }
    code {
      display: inline-block;
      max-width: 100%;
      padding: 2px 7px;
      border-radius: 6px;
      background: var(--surface-3);
      color: #d8eaff;
      overflow-wrap: anywhere;
    }
    .settings-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .field-wide { grid-column: span 2; }
    .field-full { grid-column: span 3; }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    input, select, textarea {
      width: 100%;
      min-height: 40px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #0f1319;
      color: var(--text);
      padding: 8px 10px;
      font-size: 14px;
      letter-spacing: 0;
    }
    textarea { min-height: 106px; resize: vertical; line-height: 1.45; }
    .section-title {
      grid-column: span 3;
      margin-top: 2px;
      padding-top: 12px;
      border-top: 1px solid var(--line-soft);
      color: var(--text);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }
    .settings-actions {
      grid-column: span 3;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding-top: 4px;
    }
    .muted { color: var(--muted); font-size: 12px; }
    pre, .console {
      min-height: 84px;
      margin: 0;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #0b0e13;
      color: #dfe7ef;
      overflow: auto;
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.5;
    }
    .console.empty { color: var(--muted); }
    .table-tools {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
    }
    .filter {
      max-width: 320px;
      min-height: 36px;
      font-size: 13px;
    }
    .table-wrap {
      overflow: auto;
      border: 1px solid var(--line-soft);
      border-radius: 8px;
    }
    table {
      width: 100%;
      min-width: 840px;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      border-bottom: 1px solid var(--line-soft);
      padding: 10px 10px;
      text-align: left;
      vertical-align: top;
    }
    tr:last-child td { border-bottom: 0; }
    th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: #141922;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }
    tbody tr { cursor: default; }
    tbody tr:hover { background: rgba(96, 165, 250, 0.06); }
    td { overflow-wrap: anywhere; }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      min-width: 220px;
    }
    .action-chip {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 3px 7px;
      border-radius: 6px;
      background: #111827;
      border: 1px solid var(--line);
      color: #cbd5e1;
      font-size: 11px;
      font-weight: 700;
      white-space: nowrap;
    }
    .action-chip.good { color: var(--green); border-color: rgba(53, 201, 129, 0.35); }
    .action-chip.skip { color: var(--amber); border-color: rgba(242, 184, 75, 0.35); }
    .action-chip.danger { color: var(--red); border-color: rgba(251, 113, 133, 0.35); }
    .manual-grid {
      display: grid;
      grid-template-columns: 1fr 1fr auto;
      gap: 10px;
      align-items: end;
    }
    .split {
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 14px;
    }
    .status-line {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .linklike {
      color: #cfe4ff;
      text-decoration: none;
    }
    .empty-row td {
      color: var(--muted);
      text-align: center;
      padding: 22px;
    }
    @media (max-width: 1100px) {
      .kpis { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .panel, .panel.third { grid-column: span 12; }
      .split { grid-template-columns: 1fr; }
    }
    @media (max-width: 760px) {
      .wrap { width: min(100% - 20px, 1440px); }
      .topbar { grid-template-columns: 1fr; }
      .header-actions { justify-content: flex-start; }
      .subtitle { white-space: normal; }
      .kpis { grid-template-columns: 1fr 1fr; }
      .settings-grid, dl, .manual-grid { grid-template-columns: 1fr; }
      .field-wide, .field-full, .section-title, .settings-actions { grid-column: span 1; }
      .panel-head { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div class="brand">
        <div class="mark">B24</div>
        <div>
          <h1>Bitrix24 Bot</h1>
          <div class="subtitle">ASIGNACION -> reclamar, fijar, mover etapa y mandar mensaje</div>
        </div>
      </div>
      <div class="header-actions">
        <span id="mode" class="badge">Cargando</span>
        <span id="worker-pill" class="badge">Worker</span>
        <button id="scan-now-top" type="button">Escanear</button>
        <button id="pause-scanner-top" class="secondary" type="button">Pausar</button>
      </div>
    </div>
  </header>

  <main class="wrap">
    <section class="kpis">
      <div class="kpi"><small>Modo</small><strong id="kpi-mode">-</strong><span id="kpi-mode-detail">-</span></div>
      <div class="kpi"><small>Scanner</small><strong id="kpi-scanner">-</strong><span id="kpi-scanner-detail">-</span></div>
      <div class="kpi"><small>Candidatos</small><strong id="kpi-candidates">-</strong><span>visibles en esta vuelta</span></div>
      <div class="kpi"><small>Escaneos</small><strong id="kpi-scans">-</strong><span id="kpi-last-run">-</span></div>
      <div class="kpi"><small>Ultimo claim</small><strong id="kpi-claimed">-</strong><span id="kpi-claimed-detail">-</span></div>
    </section>

    <section class="grid">
      <div class="panel full" id="error-panel" hidden>
        <div class="panel-head">
          <h2>Atencion</h2>
          <span class="badge error">Error</span>
        </div>
        <div class="panel-body">
          <pre id="scanner-error" class="console"></pre>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>Operacion</h2>
          <div class="toolbar">
            <button id="scan-now" type="button">Escanear ahora</button>
            <button id="pause-scanner" class="secondary" type="button">Pausar</button>
            <button id="resume-scanner" class="secondary" type="button">Reanudar</button>
          </div>
        </div>
        <div class="panel-body">
          <dl id="status"></dl>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>Servicio</h2>
          <span id="token-pill" class="badge">Token</span>
        </div>
        <div class="panel-body">
          <dl id="urls"></dl>
        </div>
      </div>

      <div class="panel full">
        <div class="panel-head">
          <h2>Configuracion</h2>
          <span id="override-pill" class="badge">Overrides</span>
        </div>
        <div class="panel-body">
          <div class="settings-grid">
            <div class="section-title">Operacion</div>
            <label>Modo
              <select id="setting-mode">
                <option value="dry_run">dry_run</option>
                <option value="live">live</option>
              </select>
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

            <div class="section-title">CRM</div>
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

            <div class="section-title">Bitrix</div>
            <label class="field-full">Webhook Bitrix
              <input id="setting-webhook" placeholder="pega URL completa solo si quieres cambiarla">
            </label>
            <label class="field-full">Mensaje automatico
              <textarea id="setting-message"></textarea>
            </label>

            <div class="settings-actions">
              <div class="muted" id="settings-note">Cambios en vivo; Render los borra al redeploy si no los copias a variables.</div>
              <div class="toolbar">
                <button id="save-settings" type="button">Guardar cambios</button>
                <button id="clear-settings" class="secondary" type="button">Limpiar overrides</button>
              </div>
            </div>
          </div>
          <pre id="settings-output" class="console empty">Sin cambios pendientes.</pre>
        </div>
      </div>

      <div class="panel full">
        <div class="panel-head">
          <h2>Candidatos Actuales</h2>
          <span id="candidate-count" class="badge info">0</span>
        </div>
        <div class="panel-body">
          <div class="table-tools">
            <div class="muted">Click en una fila carga Deal/Chat en prueba manual.</div>
            <input id="candidate-filter" class="filter" placeholder="Filtrar candidatos">
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Hora</th>
                  <th>Deal</th>
                  <th>Chat</th>
                  <th>Motivo</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody id="current-candidates"></tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="panel full">
        <div class="panel-head">
          <h2>Historial Reciente</h2>
          <div class="status-line">
            <span id="history-count" class="badge">0</span>
            <input id="history-filter" class="filter" placeholder="Filtrar historial">
          </div>
        </div>
        <div class="panel-body">
          <div class="table-wrap">
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
      </div>

      <div class="panel full">
        <div class="panel-head">
          <h2>Prueba Manual</h2>
          <span class="badge violet">dry_run</span>
        </div>
        <div class="panel-body split">
          <form id="check-form" class="manual-grid">
            <label>Deal ID
              <input id="deal-id" inputmode="numeric" placeholder="2804388">
            </label>
            <label>Chat ID
              <input id="chat-id" inputmode="numeric" placeholder="2758584">
            </label>
            <button id="check-button" type="submit">Probar</button>
          </form>
          <pre id="check-output" class="console empty">Sin prueba ejecutada.</pre>
        </div>
      </div>
    </section>
  </main>

  <script>
    const params = new URLSearchParams(location.search);
    const token = params.get("token") || "";
    const headers = token ? {"x-dashboard-token": token} : {};
    let scannerCache = {current_candidates: [], recent: []};

    function esc(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;",
      }[char]));
    }

    function fmt(value) {
      return value === null || value === undefined || value === "" ? "-" : value;
    }

    function fmtTime(value) {
      if (!value) return "-";
      try { return new Date(value).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"}); }
      catch { return value; }
    }

    function compactTime(value) {
      if (!value) return "-";
      try { return new Date(value).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"}); }
      catch { return value; }
    }

    function row(key, value) {
      const rendered = value || "<span class='badge error'>Falta</span>";
      return `<dt>${esc(key)}</dt><dd>${rendered}</dd>`;
    }

    function statusBadge(status) {
      const safe = esc(status || "-");
      const cls = ["claimed", "candidate"].includes(status) ? "ok"
        : ["error", "race_lost", "race_lost_after_answer"].includes(status) ? "error"
        : status === "ignored" ? "" : "info";
      return `<span class="badge ${cls}">${safe}</span>`;
    }

    function actionChips(actions) {
      const list = actions || [];
      if (!list.length) return "<span class='muted'>-</span>";
      return `<div class="actions">${list.map((action) => {
        const text = esc(action);
        const cls = action.includes("skipped") ? "skip" : action.includes("error") ? "danger" : "good";
        return `<span class="action-chip ${cls}">${text}</span>`;
      }).join("")}</div>`;
    }

    function fillManual(dealId, chatId) {
      if (dealId) document.querySelector("#deal-id").value = dealId;
      if (chatId) document.querySelector("#chat-id").value = chatId;
      document.querySelector("#check-output").textContent = `Cargado Deal ${dealId || "-"} / Chat ${chatId || "-"}`;
      document.querySelector("#check-output").classList.remove("empty");
    }

    async function loadStatus() {
      const response = await fetch("/api/bitrix/status", {headers});
      if (!response.ok) {
        document.querySelector("#mode").textContent = "Sin acceso";
        document.querySelector("#status").innerHTML = row("Error", esc(await response.text()));
        return;
      }
      const data = await response.json();
      const mode = document.querySelector("#mode");
      mode.textContent = data.is_live ? "LIVE" : "DRY RUN";
      mode.className = data.is_live ? "badge live" : "badge ok";
      document.querySelector("#kpi-mode").textContent = data.is_live ? "LIVE" : "DRY";
      document.querySelector("#kpi-mode-detail").textContent = data.is_live ? "acciones reales activas" : "solo simulacion";
      document.querySelector("#token-pill").textContent = data.dashboard_token_enabled ? "Protegido" : "Abierto";
      document.querySelector("#token-pill").className = data.dashboard_token_enabled ? "badge ok" : "badge warn";
      const overrides = data.runtime_overrides || [];
      document.querySelector("#override-pill").textContent = overrides.length ? `${overrides.length} activos` : "Sin overrides";
      document.querySelector("#override-pill").className = overrides.length ? "badge warn" : "badge";

      document.querySelector("#status").innerHTML = [
        row("Webhook", data.webhook_configured ? `<code>${esc(data.webhook_preview)}</code>` : ""),
        row("ASIGNACION", data.assignment_stage_id ? `<code>${esc(data.assignment_stage_id)}</code>` : ""),
        row("ASIGNADO", data.target_stage_id ? `<code>${esc(data.target_stage_id)}</code>` : ""),
        row("Categoria", esc(data.category_id ?? "")),
        row("Operador", esc(data.operator_user_id ?? "")),
        row("Mensaje", data.greeting_enabled ? "<span class='badge ok'>Configurado</span>" : ""),
        row("Scanner", data.scan_enabled ? `<span class='badge ok'>${esc(data.scan_interval_seconds)}s / ${esc(data.scan_limit)}</span>` : "<span class='badge warn'>Desactivado</span>"),
        row("Overrides", overrides.length ? overrides.map(esc).join(", ") : "Ninguno"),
      ].join("");

      document.querySelector("#urls").innerHTML = [
        row("Health", `<code>${esc(data.health_url)}</code>`),
        row("Eventos", `<code>${esc(data.event_url)}</code>`),
        row("Conectores", (data.allowed_connectors || []).length ? data.allowed_connectors.map(esc).join(", ") : "Todos"),
      ].join("");
    }

    function renderScanner(data) {
      scannerCache = data;
      const candidates = data.current_candidates || [];
      const recent = data.recent || [];
      const claimed = recent.find((item) => item.status === "claimed");
      const state = data.paused ? "Pausado" : (data.enabled ? "Escaneando" : "Desactivado");
      const running = data.task_running ? "Activo" : "Detenido";
      document.querySelector("#worker-pill").textContent = running;
      document.querySelector("#worker-pill").className = data.task_running ? "badge ok" : "badge warn";
      document.querySelector("#kpi-scanner").textContent = state;
      document.querySelector("#kpi-scanner-detail").textContent = `${running} / cada ${data.interval_seconds}s / limite ${data.limit}`;
      document.querySelector("#kpi-candidates").textContent = candidates.length;
      document.querySelector("#kpi-scans").textContent = data.scan_count ?? "-";
      document.querySelector("#kpi-last-run").textContent = data.last_finished_at ? `ultimo ${compactTime(data.last_finished_at)}` : "sin cierre aun";
      document.querySelector("#kpi-claimed").textContent = claimed ? compactTime(claimed.timestamp) : "-";
      document.querySelector("#kpi-claimed-detail").textContent = claimed ? `deal ${claimed.deal_id || "-"} / chat ${claimed.chat_id || "-"}` : "sin claims recientes";
      document.querySelector("#candidate-count").textContent = String(candidates.length);
      document.querySelector("#history-count").textContent = `${recent.length} filas`;
      const errorPanel = document.querySelector("#error-panel");
      const errorBox = document.querySelector("#scanner-error");
      errorPanel.hidden = !data.last_error;
      errorBox.textContent = data.last_error || "";
      renderCandidates();
      renderHistory();
    }

    function rowMatches(item, query) {
      if (!query) return true;
      return JSON.stringify(item).toLowerCase().includes(query.toLowerCase());
    }

    function renderCandidates() {
      const query = document.querySelector("#candidate-filter").value.trim();
      const rows = (scannerCache.current_candidates || []).filter((item) => rowMatches(item, query)).map((item) => `
        <tr data-deal="${esc(item.deal_id || "")}" data-chat="${esc(item.chat_id || "")}">
          <td>${fmtTime(item.timestamp)}</td>
          <td><code>${esc(fmt(item.deal_id))}</code></td>
          <td><code>${esc(fmt(item.chat_id))}</code></td>
          <td>${esc(item.reason)}</td>
          <td>${actionChips(item.actions)}</td>
        </tr>
      `).join("");
      document.querySelector("#current-candidates").innerHTML = rows || "<tr class='empty-row'><td colspan='5'>Sin candidatos activos.</td></tr>";
      bindTableClicks("#current-candidates");
    }

    function renderHistory() {
      const query = document.querySelector("#history-filter").value.trim();
      const rows = (scannerCache.recent || []).filter((item) => rowMatches(item, query)).map((item) => `
        <tr data-deal="${esc(item.deal_id || "")}" data-chat="${esc(item.chat_id || "")}">
          <td>${fmtTime(item.timestamp)}</td>
          <td>${statusBadge(item.status)}</td>
          <td><code>${esc(fmt(item.deal_id))}</code></td>
          <td><code>${esc(fmt(item.chat_id))}</code></td>
          <td>${esc(item.reason)}</td>
          <td>${actionChips(item.actions)}</td>
        </tr>
      `).join("");
      document.querySelector("#recent-results").innerHTML = rows || "<tr class='empty-row'><td colspan='6'>Sin historial.</td></tr>";
      bindTableClicks("#recent-results");
    }

    function bindTableClicks(selector) {
      document.querySelectorAll(`${selector} tr[data-deal]`).forEach((row) => {
        row.addEventListener("click", () => fillManual(row.dataset.deal, row.dataset.chat));
      });
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
      output.classList.remove("empty");
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
      if (webhookValue && !webhookValue.includes("...")) body.BITRIX_WEBHOOK_BASE_URL = webhookValue;
      try {
        const response = await fetch("/api/bitrix/settings", {
          method: "PUT",
          headers: {"content-type": "application/json", ...headers},
          body: JSON.stringify(body),
        });
        const data = await response.json();
        output.textContent = JSON.stringify(data, null, 2);
        await Promise.all([loadSettings(), loadStatus(), loadScanner()]);
      } catch (error) {
        output.textContent = String(error);
      } finally {
        button.disabled = false;
      }
    }

    async function clearSettings() {
      const output = document.querySelector("#settings-output");
      output.classList.remove("empty");
      output.textContent = "Limpiando overrides...";
      const response = await fetch("/api/bitrix/settings", {method: "DELETE", headers});
      const data = await response.json();
      output.textContent = JSON.stringify(data, null, 2);
      await Promise.all([loadSettings(), loadStatus(), loadScanner()]);
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
      output.classList.remove("empty");
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
    document.querySelector("#scan-now-top").addEventListener("click", async () => postScanner("/api/bitrix/scan"));
    document.querySelector("#pause-scanner").addEventListener("click", async () => postScanner("/api/bitrix/scanner/pause"));
    document.querySelector("#pause-scanner-top").addEventListener("click", async () => postScanner("/api/bitrix/scanner/pause"));
    document.querySelector("#resume-scanner").addEventListener("click", async () => postScanner("/api/bitrix/scanner/resume"));
    document.querySelector("#save-settings").addEventListener("click", saveSettings);
    document.querySelector("#clear-settings").addEventListener("click", clearSettings);
    document.querySelector("#candidate-filter").addEventListener("input", renderCandidates);
    document.querySelector("#history-filter").addEventListener("input", renderHistory);

    loadStatus();
    loadScanner();
    loadSettings();
    setInterval(loadStatus, 15000);
    setInterval(loadScanner, 4000);
  </script>
</body>
</html>
"""
