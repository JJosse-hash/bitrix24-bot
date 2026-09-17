# Despliegue

## Variables

Usar `.env.example` como base. Nunca exponer `LLM_API_KEY` o `SPEECH_API_KEY` al frontend.

## Producción

Requisitos mínimos:

- HTTPS detrás de proxy o plataforma administrada.
- Postgres con backups cifrados.
- Retención temporal de sesiones.
- Rate limiting por IP/usuario.
- Logs estructurados sin texto completo de direcciones.
- Separar datos raw de datos normalizados con licencias registradas.

## Docker

```bash
docker compose up --build
```

Para producción, construir imágenes inmutables, fijar versiones y configurar secretos con el gestor de la plataforma.
