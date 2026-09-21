# Como lo hicimos

## 1. Prueba segura

Primero se probo en modo `dry_run`. El bot revisaba chats y solo avisaba si un
chat cumplia la condicion, sin reclamarlo ni mandar mensajes.

## 2. Condicion de chat nuevo

Se definio que un chat era valido solo si:

- Venia de `ASIGNACION`.
- No tenia mensajes de empleados.
- No tenia senales de conversacion recogida/asignada/transferida.

Esto evita tomar chats reabiertos donde ya hablo otro asesor.

## 3. Primer modo live

Despues se activo `live`:

- Tomaba el dialogo.
- Movia la negociacion a `ASIGNADO`.
- Mandaba mensaje automatico.

## 4. Problema de asignacion real

Bitrix mostraba el chat como tomado, pero no como `Asignarlo a mi`.

Se probaron metodos aislados con chats reales:

- `imopenlines.operator.answer`
- `imopenlines.session.intercept`
- `imopenlines.operator.transfer`
- `imopenlines.session.mode.pin`

El metodo que resolvio el problema fue:

```text
imopenlines.session.mode.pin
```

Ese metodo fija el chat al operador actual y equivale al boton de Bitrix.

## 5. Dashboard

Se agrego dashboard para:

- Ver estado del scanner.
- Cambiar `dry_run/live`.
- Configurar mensaje.
- Ver candidatos.
- Probar Deal ID o Chat ID manualmente.

## 6. Reestructura

Finalmente se creo `AgentVentas BOT` como carpeta principal del proyecto y se
dejo un espejo en raiz para que Render no se rompa.
