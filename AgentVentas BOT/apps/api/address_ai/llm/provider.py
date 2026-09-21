from __future__ import annotations

import os
from abc import ABC, abstractmethod

from address_ai.core.models import LLMAnalysisRequest, LLMAnalysisResponse, LLMTask, LLMToolCall


DEEPSEEK_FLASH_MODEL = "deepseek-v4-flash"
DEEPSEEK_PRO_MODEL = "deepseek-v4-pro"


GEO_TOOL_NAMES = [
    "search_streets",
    "search_colonies",
    "search_postal_codes",
    "search_municipalities",
    "search_localities",
    "search_pois",
    "search_cemeteries",
    "search_schools",
    "search_universities",
    "find_intersection",
    "find_nearby",
    "find_between",
    "find_front_of",
    "find_behind",
    "find_distance",
    "search_candidates",
    "validate_candidate",
]


def select_llm_model(task: LLMTask, *, ambiguity_count: int = 0, candidate_count: int = 0) -> str:
    if task in {LLMTask.complex_reasoning, LLMTask.contradiction_review}:
        return DEEPSEEK_PRO_MODEL
    if ambiguity_count >= 2 or candidate_count >= 4:
        return DEEPSEEK_PRO_MODEL
    return DEEPSEEK_FLASH_MODEL


class LLMProvider(ABC):
    @abstractmethod
    async def analyze(self, request: LLMAnalysisRequest) -> LLMAnalysisResponse:
        raise NotImplementedError


class DevelopmentLLMProvider(LLMProvider):
    """Local deterministic provider used until a networked DeepSeek adapter is configured."""

    async def analyze(self, request: LLMAnalysisRequest) -> LLMAnalysisResponse:
        ambiguity_count = len(request.parsed.ambiguities) if request.parsed else 0
        model = select_llm_model(request.task, ambiguity_count=ambiguity_count, candidate_count=len(request.candidates))
        tool_calls: list[LLMToolCall] = []
        if request.parsed:
            if request.parsed.postal_code:
                tool_calls.append(LLMToolCall(name="search_postal_codes", arguments={"postal_code": request.parsed.postal_code.value}))
            for street in request.parsed.streets + request.parsed.intersections:
                tool_calls.append(LLMToolCall(name="search_streets", arguments={"name": street.value}))
            for poi in request.parsed.poi_categories:
                tool_calls.append(LLMToolCall(name="search_pois", arguments={"category": poi.value}))
            if len(request.parsed.intersections) >= 2:
                tool_calls.append(
                    LLMToolCall(
                        name="find_intersection",
                        arguments={"street_a": request.parsed.intersections[0].value, "street_b": request.parsed.intersections[1].value},
                    )
                )
        return LLMAnalysisResponse(
            model=model,
            provider=os.getenv("LLM_PROVIDER", "development"),
            summary="El proveedor local solo propone herramientas; no genera coordenadas ni reemplaza la validación geográfica.",
            tool_calls=tool_calls,
            uncertainties=request.parsed.ambiguities if request.parsed else [],
        )
