from __future__ import annotations

from address_ai.core.fuzzy import phonetic_similarity, similarity
from address_ai.core.models import Candidate, ParsedAddress, RankedCandidate, ScoreBreakdown


WEIGHTS = {
    "state": 12,
    "municipality": 24,
    "municipality_phonetic": 4,
    "postal_code": 16,
    "house_number": 8,
    "block": 8,
    "lot": 8,
    "street": 18,
    "street_phonetic": 3,
    "poi": 13,
    "semantic": 10,
}


def confidence_label(score: float) -> str:
    if score >= 90:
        return "muy alta"
    if score >= 75:
        return "alta"
    if score >= 55:
        return "media"
    if score >= 30:
        return "baja"
    return "muy baja"


class CandidateRanker:
    def rank(self, parsed: ParsedAddress, candidates: list[Candidate]) -> list[RankedCandidate]:
        ranked = [self._score_candidate(parsed, candidate) for candidate in candidates]
        ranked.sort(key=lambda item: item.score, reverse=True)
        return [item for item in ranked if item.score > 12][:8]

    def _score_candidate(self, parsed: ParsedAddress, candidate: Candidate) -> RankedCandidate:
        breakdown: list[ScoreBreakdown] = []

        def add(signal: str, points: float, reason: str) -> None:
            if points > 0:
                breakdown.append(ScoreBreakdown(signal=signal, points=round(points, 2), reason=reason))

        if parsed.state:
            add("state", WEIGHTS["state"] * similarity(parsed.state.value, candidate.state), f"Estado compatible: {candidate.state}")
        if parsed.municipality:
            sim = similarity(parsed.municipality.value, candidate.municipality)
            add("municipality", WEIGHTS["municipality"] * sim, f"Municipio candidato: {candidate.municipality}")
            add("municipality_phonetic", WEIGHTS["municipality_phonetic"] * phonetic_similarity(parsed.municipality.value, candidate.municipality), "Similitud fonética municipal")
        if parsed.postal_code and candidate.postal_code == parsed.postal_code.value:
            add("postal_code", WEIGHTS["postal_code"], "Código postal coincide")
        if parsed.house_number and candidate.house_number == parsed.house_number.value:
            add("house_number", WEIGHTS["house_number"], "Número exterior coincide")
        if parsed.block and candidate.tags.get("block") == parsed.block.value:
            add("block", WEIGHTS["block"], "Manzana coincide")
        if parsed.lot and candidate.tags.get("lot") == parsed.lot.value:
            add("lot", WEIGHTS["lot"], "Lote coincide")

        mentioned_streets = [item.value for item in parsed.streets + parsed.intersections]
        for street in mentioned_streets:
            best = max([similarity(street, candidate_street) for candidate_street in candidate.streets] or [0])
            add("street", WEIGHTS["street"] * best, f"Calle compatible con “{street}”")
            best_phonetic = max([phonetic_similarity(street, candidate_street) for candidate_street in candidate.streets] or [0])
            add("street_phonetic", WEIGHTS["street_phonetic"] * best_phonetic, f"Fonética compatible con “{street}”")

        for poi in parsed.poi_categories:
            if poi.value in candidate.poi_categories:
                add("poi", WEIGHTS["poi"] * poi.confidence, f"Referencia compatible: {poi.value}")

        words = set(parsed.normalized_text.split())
        semantic_hits = 0
        for value in candidate.tags.get("programs", []) + candidate.tags.get("nearby", []):
            semantic_hits += len(words.intersection(set(value.split())))
        add("semantic", min(WEIGHTS["semantic"], semantic_hits * 4), "Términos semánticos del candidato aparecen en la descripción")

        total = min(100, sum(item.points for item in breakdown))
        return RankedCandidate(candidate=candidate, score=round(total, 1), confidence_label=confidence_label(total), breakdown=breakdown)
