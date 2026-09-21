# AgentVentas BOT

Bot de ventas para Bitrix24 que toma chats nuevos de la etapa `ASIGNACION`,
los fija al operador actual, mueve la negociacion a `ASIGNADO` y manda el
primer mensaje automatico.

## Estado

- Plataforma: FastAPI en Render.
- Fuente de datos: Bitrix24 REST API.
- Modo seguro: `dry_run`, solo detecta candidatos.
- Modo real: `live`, reclama/fija chat, actualiza CRM y envia mensaje.
- Dashboard: `/` protegido con `BITRIX_DASHBOARD_TOKEN`.

## Estructura

```text
AgentVentas BOT/
  apps/api/                  API FastAPI y logica Bitrix
  docs/                      Documentacion operativa
  scripts/subir_a_github.sh  Commit + push + autodeploy Render
  .env.example               Variables de entorno de referencia
```

La carpeta raiz del repo aun conserva `apps/api` como espejo de compatibilidad,
porque el servicio actual de Render fue creado con `Root Directory: apps/api`.
El script de subida sincroniza automaticamente `AgentVentas BOT/apps/api` hacia
ese espejo antes de subir a GitHub.

## Uso rapido

```bash
cd "AgentVentas BOT"
../subir-agentventas.sh "mensaje del cambio"
```

O directamente:

```bash
bash "AgentVentas BOT/scripts/subir_a_github.sh" "mensaje del cambio"
```

Al hacer push a `main`, Render redeploya automaticamente si el servicio tiene
Auto Deploy activo.

## Documentos

- [Funcionamiento](docs/FUNCIONAMIENTO.md)
- [Configuracion](docs/CONFIGURACION.md)
- [Operacion diaria](docs/OPERACION.md)
- [Despliegue en Render](docs/DESPLIEGUE_RENDER.md)
- [Como se hizo](docs/COMO_LO_HICIMOS.md)
- [Seguridad](docs/SEGURIDAD.md)
