# Privacidad y Seguridad

Principio: mínima retención.

## Por defecto

- No almacenar audio permanentemente.
- No persistir transcripciones ni direcciones completas.
- No registrar texto completo del usuario.
- Mantener sesión en memoria durante el MVP.
- Usar fixtures sintéticos para desarrollo.

## Logs

La API registra metadatos operativos:

- duración;
- número de candidatos;
- presencia de municipio/calle/POI.

No registra dirección completa.

## Proveedores externos

Speech-to-Text y LLM están desacoplados. Antes de habilitar un proveedor:

- revisar residencia y retención de datos;
- firmar acuerdos necesarios;
- documentar qué campos se envían;
- permitir modo local/offline cuando sea requerido.
