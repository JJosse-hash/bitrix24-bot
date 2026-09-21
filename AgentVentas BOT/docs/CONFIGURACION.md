# Configuracion

Estas son las variables que controlan el bot.

## Obligatoria

```bash
BITRIX_WEBHOOK_BASE_URL=https://tu-bitrix.bitrix24.mx/rest/USER_ID/WEBHOOK_KEY
BITRIX_ASSIGNMENT_STAGE_ID=C16:UC_GIKKS8
BITRIX_CATEGORY_ID=16
BITRIX_OPERATOR_USER_ID=2381716
BITRIX_TARGET_STAGE_ID=C16:UC_L8W7U1
BITRIX_DASHBOARD_TOKEN=elige-un-token-privado
```

## Modo

```bash
BITRIX_AUTOMATION_MODE=dry_run
```

Valores:

- `dry_run`: no toca chats; solo detecta candidatos.
- `live`: toma chats, fija operador, mueve etapa y manda mensaje.

## Mensaje automatico

```bash
BITRIX_GREETING_MESSAGE=Hola, buen dia soy Jose Pecina de Megacable...
```

En Render puedes escribir saltos de linea reales o usar `\n`.

Mensaje usado:

```text
Hola, buen día soy José Pecina de Megacable, para confirmar cobertura y promociones me puede brindar de su domicilio: Calle y número, Colonia, Código postal

¿es la primera vez que contrata Megacable en el domicilio?
```

## Scanner

```bash
BITRIX_SCAN_ENABLED=true
BITRIX_SCAN_INTERVAL_SECONDS=5
BITRIX_SCAN_LIMIT=8
```

## Opcionales

```bash
BITRIX_ALLOWED_CONNECTORS=
BITRIX_OUTBOUND_TOKEN=
```

`BITRIX_ALLOWED_CONNECTORS` permite limitar por conector. Si esta vacio acepta
todos los conectores.

`BITRIX_OUTBOUND_TOKEN` solo se usa si algun dia se activan webhooks salientes.
Actualmente el bot funciona por polling.

## Permisos del webhook entrante

El webhook entrante de Bitrix debe tener permisos:

- `CRM (crm)`
- `Canales Abiertos (imopenlines)`
- `Chat y Notificaciones (im)`
- `Usuarios (user)`

Con esos permisos puede leer chats, tomar/fijar conversaciones, actualizar CRM
y mandar mensajes.
