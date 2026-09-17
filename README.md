# AddressAI México

MVP funcional para interpretar descripciones humanas imperfectas de ubicaciones mexicanas, generar candidatos y explicar el ranking.

## Estado actual

Fase 1 implementada con un núcleo ejecutable:

- Parser de direcciones mexicanas con abreviaturas, manzana/lote, referencias y cruces.
- Normalización y fuzzy/phonetic matching para español.
- Ranking explicable con múltiples señales.
- API FastAPI.
- UI Next.js con modo llamada/manual, candidatos, diagnóstico y mapa MapLibre.
- Abstracción `LLMProvider` con router `deepseek-v4-flash`/`deepseek-v4-pro` y proveedor local determinista.
- PostGIS listo vía Docker para Fase 2.
- Tests unitarios e integración con fixtures ficticios.

## Ejecutar local

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r apps/api/requirements-dev.txt
pytest apps/api/tests -q
uvicorn address_ai.api.main:app --app-dir apps/api --reload
```

En otra terminal:

```bash
npm install
npm --workspace apps/web run dev
```

Abre `http://localhost:3000`.

## Docker

```bash
docker compose up --build
```

Servicios:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- PostGIS: `localhost:5432`

## Ejemplo MVP

Entrada:

```text
universidad por san nicolas cerca del metro que tenga mecatronica
```

El sistema identifica municipio, referencia de transporte, intención de universidad y programa, devuelve candidatos y explica por qué rankea primero.

## LLM

La Fase 1 no inventa coordenadas con IA. El paquete `address_ai.llm` define un `LLMProvider` intercambiable y un router de modelo:

- `deepseek-v4-flash`: extracción rápida y casos simples.
- `deepseek-v4-pro`: razonamiento complejo, contradicciones o demasiados candidatos.

El proveedor actual (`DevelopmentLLMProvider`) solo propone herramientas geográficas como `search_postal_codes`, `search_streets` y `find_intersection`. La validación de ubicación sigue dependiendo del motor geográfico.

## Documentos

- [Arquitectura](docs/ARCHITECTURE.md)
- [Fuentes de datos](docs/DATA_SOURCES.md)
- [Base de datos](docs/DATABASE.md)
- [API](docs/API.md)
- [Desarrollo](docs/DEVELOPMENT.md)
- [Despliegue](docs/DEPLOYMENT.md)
- [Privacidad](docs/PRIVACY.md)
