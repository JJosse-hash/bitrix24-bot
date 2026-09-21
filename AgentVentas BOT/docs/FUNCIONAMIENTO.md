# Funcionamiento de AgentVentas BOT

AgentVentas BOT revisa Bitrix24 cada pocos segundos buscando negociaciones en
la etapa `ASIGNACION`. Por cada negociacion encuentra el chat de Canal Abierto
relacionado y decide si puede tomarlo.

## Flujo general

1. Lee negociaciones de CRM con `crm.item.list`.
2. Filtra solo las que estan en la etapa configurada como `ASIGNACION`.
3. Busca el chat relacionado con `imopenlines.crm.chat.get`.
4. Lee historial del chat con `imopenlines.session.history.get`.
5. Valida si el chat esta realmente nuevo.
6. Si esta en `dry_run`, solo lo muestra como candidato.
7. Si esta en `live`, ejecuta acciones reales:
   - `imopenlines.operator.answer`
   - `imopenlines.session.intercept`
   - `imopenlines.session.mode.pin`
   - `crm.item.update`
   - `crm.deal.update`
   - `imopenlines.crm.message.add`

## Condicion para tomar chat

El bot solo actua cuando:

- La negociacion esta en `BITRIX_ASSIGNMENT_STAGE_ID`.
- La negociacion pertenece a `BITRIX_CATEGORY_ID`.
- El chat no tiene mensajes de empleados.
- El historial no tiene senales de atencion previa.
- No hay indicadores como conversacion recogida, asignada, transferida o
  invitacion de otro asesor.

Si detecta mensajes internos o marcadores de atencion, lo ignora.

## Acciones en modo live

Cuando se cumplen las condiciones:

1. Responde el dialogo para tomarlo.
2. Intenta interceptarlo como operador actual.
3. Lo fija con `imopenlines.session.mode.pin`.
   Este fue el metodo que funciono como el boton de Bitrix `Asignarlo a mi`.
4. Cambia el responsable de la negociacion a `BITRIX_OPERATOR_USER_ID`.
5. Mueve la etapa a `BITRIX_TARGET_STAGE_ID`.
6. Manda `BITRIX_GREETING_MESSAGE`.

## Scanner

El scanner vive en memoria dentro del proceso de FastAPI. Corre en background
desde el arranque de la app.

Variables principales:

```text
BITRIX_SCAN_ENABLED=true
BITRIX_SCAN_INTERVAL_SECONDS=5
BITRIX_SCAN_LIMIT=8
```

`BITRIX_SCAN_LIMIT` significa cuantos deals revisa por vuelta. No es un limite
diario; solo controla que cada escaneo sea rapido.

## Dashboard

El dashboard permite:

- Ver modo actual (`dry_run` o `live`).
- Ver candidatos actuales.
- Ver historial reciente.
- Pausar/reanudar scanner.
- Ejecutar escaneo manual.
- Hacer prueba manual por Deal ID o Chat ID.
- Cambiar configuracion en vivo con overrides temporales.

Los overrides se pierden al reiniciar/redeployar Render. Para cambios
permanentes hay que ponerlos en Environment Variables de Render.
