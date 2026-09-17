# Desarrollo

## Backend

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r apps/api/requirements-dev.txt
pytest apps/api/tests -q
uvicorn address_ai.api.main:app --app-dir apps/api --reload
```

## Frontend

```bash
npm install
npm --workspace apps/web run dev
```

## Añadir abreviaturas

Editar `ABBREVIATIONS` en `apps/api/address_ai/core/normalization.py`. En fases siguientes se moverá a un diccionario externo versionado.

## Añadir fixtures

Usar datos sintéticos en `apps/api/address_ai/data/fixtures.py`. No usar domicilios privados reales.

## Tests obligatorios

Agregar pruebas para cada regla nueva de parser o ranking. Los casos actuales cubren:

- normalización;
- abreviaturas;
- fuzzy/fonética;
- parser;
- manzana/lote;
- referencias;
- ranking;
- API.
