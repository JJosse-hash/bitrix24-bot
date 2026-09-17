from __future__ import annotations

import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from address_ai.bitrix.dashboard import router as bitrix_dashboard_router
from address_ai.bitrix.webhook import router as bitrix_router
from address_ai.core.models import ParsedAddress, SearchRequest, SearchResponse
from address_ai.core.parser import MexicanAddressParser
from address_ai.geo.search import FixtureGeoSearch, recommended_question
from address_ai.ranking.ranker import CandidateRanker

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("address-ai")

app = FastAPI(title="AddressAI México API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

parser = MexicanAddressParser()
geo_search = FixtureGeoSearch()
ranker = CandidateRanker()

app.include_router(bitrix_dashboard_router)
app.include_router(bitrix_router)


@app.get("/api/health")
def api_health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/parse", response_model=ParsedAddress)
def parse_address(request: SearchRequest) -> ParsedAddress:
    return parser.parse(request.text)


@app.post("/api/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    start = time.perf_counter()
    parsed = parser.parse(request.text)
    candidates = ranker.rank(parsed, geo_search.search(parsed))
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        {
            "event": "search.completed",
            "elapsed_ms": elapsed_ms,
            "candidate_count": len(candidates),
            "has_municipality": bool(parsed.municipality),
            "has_street": bool(parsed.streets or parsed.intersections),
            "has_poi": bool(parsed.poi_categories),
        }
    )
    warnings = []
    if not candidates or candidates[0].score < 45:
        warnings.append("No hay información suficiente para determinar una ubicación exacta.")
    if parsed.postal_code and candidates and candidates[0].candidate.postal_code and parsed.postal_code.value != candidates[0].candidate.postal_code:
        warnings.append(
            f"El código postal indicado ({parsed.postal_code.value}) no coincide con el candidato principal ({candidates[0].candidate.postal_code})."
        )
    return SearchResponse(
        parsed=parsed,
        candidates=candidates,
        recommended_question=recommended_question(parsed, len(candidates)),
        warnings=warnings,
    )


@app.post("/api/questions")
def question(request: SearchRequest) -> dict[str, str | None]:
    parsed = parser.parse(request.text)
    ranked = ranker.rank(parsed, geo_search.search(parsed))
    return {"question": recommended_question(parsed, len(ranked))}
