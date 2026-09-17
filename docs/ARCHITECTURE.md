# Arquitectura

## Riesgos técnicos principales

1. Las transcripciones pueden distorsionar nombres propios mexicanos. Mitigación: normalización, fonética, fuzzy matching, contexto geográfico y candidatos alternativos.
2. OSM no tiene cobertura homogénea por colonia, número exterior o POI. Mitigación: arquitectura de fuentes reemplazables y scoring por evidencia, no por certeza falsa.
3. Direcciones no convencionales no siempre tienen calle y número. Mitigación: parser con manzana/lote, carretera/km, referencias e intersecciones.
4. Privacidad: una llamada puede contener datos personales. Mitigación: retención temporal, logs sin direcciones completas y proveedores configurables.
5. Latencia: el operador necesita respuestas preliminares. Mitigación: procesamiento incremental, debounce, índices trigram/spatial y ranking local sobre pool reducido.

## Componentes

```text
Browser
  -> Next.js UI
  -> FastAPI Search API
       -> Parser determinista
       -> Fuzzy/phonetic matcher
       -> Geo search
       -> Ranking explicable
       -> Question recommender
       -> Optional LLMProvider
  -> PostgreSQL + PostGIS
```

## Fases

- Fase 1: parser, normalización, búsqueda fixture y ranking explicable. Implementada.
- Fase 2: ingestión de OSM/INEGI/SEPOMEX en PostGIS.
- Fase 3: fuzzy search en Postgres con `pg_trgm` y catálogos.
- Fase 4: consultas geoespaciales reales con `ST_DWithin`, `ST_Intersects`, `ST_Distance`.
- Fase 5: ranking calibrable por YAML/DB.
- Fase 6: SpeechProvider realtime/file.
- Fase 7: LLMProvider para corrección contextual opcional. Interfaz y router base implementados; falta adaptador DeepSeek de red.
- Fase 8: preguntas interactivas por reducción de incertidumbre.

## STT

La API define `SpeechProvider.transcribe_audio(...)` y `transcribe_stream(...)`. La implementación actual es `DevelopmentSpeechProvider`, que permite probar sin enviar audio a terceros.

Alternativas comparadas:

- OpenAI realtime transcription: buena opción para deltas de micrófono y latencia baja.
- OpenAI file transcription: útil para fragmentos grabados y reprocesamiento.
- Whisper local: mejor privacidad, mayor costo operativo y latencia según hardware.
- Azure Speech / Google Speech: fuertes en telefonía empresarial, requieren revisar residencia de datos y costos.

## LLM

El MVP no depende de LLM. Un LLM debe ser fallback opcional para corregir contexto, extraer entidades difíciles y sugerir preguntas, nunca autoridad única. Proveedores deben conectarse por variable `LLM_PROVIDER`.

La interfaz `LLMProvider` ya existe en `address_ai.llm`. El router escoge `deepseek-v4-flash` para extracción rápida y `deepseek-v4-pro` para razonamiento complejo, contradicciones o alta ambigüedad. El proveedor de desarrollo es determinista: su salida son tool calls geoespaciales sugeridos, no coordenadas.
