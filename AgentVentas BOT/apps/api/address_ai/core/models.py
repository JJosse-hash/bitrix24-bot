from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceStatus(str, Enum):
    unknown = "unknown"
    detected = "detected"
    hypothesis = "hypothesis"
    confirmed = "confirmed"
    rejected = "rejected"


class Evidence(BaseModel):
    value: str
    source: str = "text"
    confidence: float = Field(ge=0, le=1)
    status: EvidenceStatus = EvidenceStatus.detected
    alternatives: list[str] = Field(default_factory=list)


class ParsedAddress(BaseModel):
    raw_text: str
    normalized_text: str
    state: Evidence | None = None
    municipality: Evidence | None = None
    locality: Evidence | None = None
    neighborhood: Evidence | None = None
    postal_code: Evidence | None = None
    streets: list[Evidence] = Field(default_factory=list)
    intersections: list[Evidence] = Field(default_factory=list)
    house_number: Evidence | None = None
    interior_number: Evidence | None = None
    block: Evidence | None = None
    lot: Evidence | None = None
    references: list[Evidence] = Field(default_factory=list)
    poi_categories: list[Evidence] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)


class GeoPoint(BaseModel):
    lat: float
    lon: float


class Candidate(BaseModel):
    id: str
    label: str
    normalized_address: str
    point: GeoPoint
    state: str
    municipality: str
    neighborhood: str | None = None
    postal_code: str | None = None
    streets: list[str] = Field(default_factory=list)
    house_number: str | None = None
    poi_categories: list[str] = Field(default_factory=list)
    tags: dict[str, Any] = Field(default_factory=dict)
    source: str = "fixture"


class ScoreBreakdown(BaseModel):
    signal: str
    points: float
    reason: str


class RankedCandidate(BaseModel):
    candidate: Candidate
    score: float = Field(ge=0, le=100)
    confidence_label: Literal["muy alta", "alta", "media", "baja", "muy baja"]
    breakdown: list[ScoreBreakdown]


class LLMTask(str, Enum):
    quick_extract = "quick_extract"
    complex_reasoning = "complex_reasoning"
    contradiction_review = "contradiction_review"
    question_selection = "question_selection"


class LLMToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class LLMAnalysisRequest(BaseModel):
    text: str
    parsed: ParsedAddress | None = None
    candidates: list[Candidate] = Field(default_factory=list)
    task: LLMTask = LLMTask.quick_extract


class LLMAnalysisResponse(BaseModel):
    model: str
    provider: str
    summary: str
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=80)
    confirmed: dict[str, str] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    parsed: ParsedAddress
    candidates: list[RankedCandidate]
    recommended_question: str | None
    warnings: list[str] = Field(default_factory=list)


class TranscriptionChunk(BaseModel):
    text: str
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: float | None = None
    is_final: bool = False
