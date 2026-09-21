# Operacion diaria

## Abrir dashboard

```text
https://TU-SERVICIO.onrender.com/?token=TU_TOKEN
```

## Antes de trabajar

1. Verifica que el modo diga `live`.
2. Verifica que el scanner este activo.
3. Verifica que no haya `last_error`.
4. Confirma que el mensaje automatico este configurado.

## Si no toma chats

Revisa en este orden:

1. Modo: debe estar en `live`.
2. Scanner: debe estar activo y no pausado.
3. Mensaje: `greeting_enabled` debe ser `true`.
4. Permisos del webhook en Bitrix.
5. Que haya deals en etapa `ASIGNACION`.
6. Que los chats sean realmente nuevos.

## Si aparecen candidatos pero no hace nada

Eso casi siempre significa que esta en `dry_run`.

Solucion rapida desde dashboard:

1. En Configuracion cambia `Modo` a `live`.
2. Pega el mensaje automatico si esta vacio.
3. Guarda.

Solucion permanente:

En Render agrega:

```bash
BITRIX_AUTOMATION_MODE=live
BITRIX_GREETING_MESSAGE=Hola, buen día soy José Pecina de Megacable...
```

## Si Render se reinicia

Los cambios hechos desde dashboard son temporales. Si Render se reinicia, vuelve
a tomar las variables permanentes del panel de Render.

Por eso lo importante debe estar en Environment Variables.

## Apagar rapido

Desde dashboard:

- Cambia `Modo` a `dry_run`, o
- Pausa el scanner.

Desde Render:

```bash
BITRIX_SCAN_ENABLED=false
```
