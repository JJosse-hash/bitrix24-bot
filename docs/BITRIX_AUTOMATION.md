# Bitrix24 Open Lines automation

This service scans Bitrix24 deals in the `ASIGNACION` stage, checks each linked
Open Lines chat history, and acts only when the chat is truly new.

Default mode is `dry_run`: it reports candidates without taking chats, moving
deals, or sending messages.

## Render settings

Create a Render **Web Service**.

```text
Root Directory: apps/api
Build Command: pip install -r requirements.txt
Start Command: uvicorn address_ai.api.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /api/health
```

## Environment

```bash
BITRIX_WEBHOOK_BASE_URL=https://your-domain.bitrix24.mx/rest/USER_ID/WEBHOOK_KEY
BITRIX_ASSIGNMENT_STAGE_ID=C16:UC_GIKKS8
BITRIX_CATEGORY_ID=16
BITRIX_AUTOMATION_MODE=dry_run
BITRIX_DASHBOARD_TOKEN=choose-a-private-token
BITRIX_OPERATOR_USER_ID=2381716
BITRIX_TARGET_STAGE_ID=C16:UC_L8W7U1
BITRIX_GREETING_MESSAGE=Hola, buen día soy José Pecina de Megacable, para confirmar cobertura y promociones me puede brindar de su domicilio: Calle y número, Colonia, Código postal\n\n¿es la primera vez que contrata Megacable en el domicilio?
BITRIX_SCAN_ENABLED=true
BITRIX_SCAN_INTERVAL_SECONDS=5
BITRIX_SCAN_LIMIT=8
```

Optional:

```bash
BITRIX_ALLOWED_CONNECTORS=
BITRIX_OUTBOUND_TOKEN=
```

## Dashboard

Open:

```text
https://your-render-service.onrender.com/?token=choose-a-private-token
```

The dashboard shows config, scanner health, recent results, manual checks, and
buttons to pause, resume, or trigger a scan.

## Modes

`BITRIX_AUTOMATION_MODE=dry_run`

- Scans `ASIGNACION`.
- Validates the “new real chat” condition.
- Shows `candidate` or `ignored` in the dashboard.
- Does not answer, move, assign, or message.

`BITRIX_AUTOMATION_MODE=live`

- Rechecks history before acting.
- Calls `imopenlines.operator.answer`.
- Tries `imopenlines.session.intercept` as a best-effort claim helper. If Bitrix
  rejects it because the dialog is already claimed, the bot continues.
- Updates the deal owner/stage.
- Sends `BITRIX_GREETING_MESSAGE`.

## Condition

The bot only acts when:

- The deal is in `ASIGNACION`.
- The deal belongs to the configured category.
- The linked chat has no internal human messages.
- The chat history has no handled markers such as conversation picked up,
  assigned to agent, transfer, or invitation.

## Optional outbound webhook

If Bitrix24 outbound webhooks become available later, `/api/bitrix/events` can
still receive them. The scanner is the main mechanism and does not require
outbound webhooks.

## Safety

- Keep `dry_run` until the dashboard shows the expected candidates.
- Keep the Bitrix incoming webhook secret.
- Revoke any GitHub or Bitrix token that was shared during setup.
