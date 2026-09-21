# AgentVentas BOT

Proyecto principal en:

```text
AgentVentas BOT/
```

Este repo contiene el bot de ventas para Bitrix24. El bot revisa chats nuevos
en `ASIGNACION`, los toma cuando cumplen condiciones, los fija al operador,
mueve la negociacion a `ASIGNADO` y manda el mensaje automatico.

## Importante Sobre Render

El servicio actual de Render fue creado con:

```text
Root Directory: apps/api
```

Por eso se conserva `apps/api` en la raiz como espejo de compatibilidad.
Trabaja normalmente en `AgentVentas BOT/apps/api`; el script de subida sincroniza
ese contenido hacia `apps/api` antes de hacer commit/push.

## Subir Cambios

```bash
bash subir-agentventas.sh "mensaje del cambio"
```

Si GitHub pide token:

```bash
GITHUB_TOKEN=ghp_xxx bash subir-agentventas.sh "mensaje del cambio"
```

No guardes tokens en archivos.

## Documentacion

- [README del bot](AgentVentas%20BOT/README.md)
- [Funcionamiento](AgentVentas%20BOT/docs/FUNCIONAMIENTO.md)
- [Configuracion](AgentVentas%20BOT/docs/CONFIGURACION.md)
- [Operacion diaria](AgentVentas%20BOT/docs/OPERACION.md)
- [Despliegue Render](AgentVentas%20BOT/docs/DESPLIEGUE_RENDER.md)
- [Como se hizo](AgentVentas%20BOT/docs/COMO_LO_HICIMOS.md)
- [Seguridad](AgentVentas%20BOT/docs/SEGURIDAD.md)
