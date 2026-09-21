# Seguridad

## Nunca subir secretos

No subas:

- Webhook real de Bitrix.
- Tokens de GitHub.
- Token del dashboard.
- Claves privadas.

Usa Environment Variables en Render.

## Tokens compartidos durante desarrollo

Si algun token fue pegado en un chat o usado para pruebas, revocalo cuando ya
no se necesite.

## GitHub

El script de subida soporta `GITHUB_TOKEN` como variable temporal:

```bash
GITHUB_TOKEN=ghp_xxx bash "AgentVentas BOT/scripts/subir_a_github.sh"
```

No guarda el token en archivos ni en git config.

## Bitrix

El webhook entrante de Bitrix permite ejecutar acciones. Guardalo como secreto.

Si sospechas que se filtro:

1. En Bitrix, genera uno nuevo.
2. Cambia `BITRIX_WEBHOOK_BASE_URL` en Render.
3. Redeploya o reinicia el servicio.
