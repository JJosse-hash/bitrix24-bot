# API

Base local: `http://localhost:8000`.

## GET /api/health

Devuelve estado básico.

## POST /api/parse

Request:

```json
{ "text": "MZ 4 LT 18 COL SAN JOSE atras de la iglesia" }
```

Response: `ParsedAddress`, con evidencias probabilísticas y estados `detected`, `hypothesis`, etc.

## POST /api/search

Request:

```json
{
  "text": "San Nicolás calle Abedul entre Sauce casa 137 frente al panteón",
  "session_id": "optional"
}
```

Response:

- `parsed`: interpretación estructurada.
- `candidates`: candidatos rankeados.
- `breakdown`: razones de scoring.
- `recommended_question`: siguiente pregunta útil.
- `warnings`: insuficiencia o ambigüedad.

## POST /api/questions

Devuelve solo la pregunta recomendada para reducir incertidumbre.

## LLMProvider interno

El MVP incluye una abstracción Python, no un endpoint público todavía:

- `LLMProvider.analyze(...)`
- `DevelopmentLLMProvider`
- `select_llm_model(...)`

El router selecciona `deepseek-v4-flash` para extracción sencilla y `deepseek-v4-pro` para razonamiento complejo, contradicciones o alta ambigüedad. El proveedor de desarrollo no llama a redes ni genera coordenadas; solo propone tool calls geoespaciales verificables.
