from __future__ import annotations

from address_ai.core.fuzzy import similarity
from address_ai.core.models import Candidate, ParsedAddress
from address_ai.data.fixtures import FIXTURE_CANDIDATES


class FixtureGeoSearch:
    """Small fictitious search index used in development and tests."""

    def __init__(self, candidates: list[Candidate] | None = None):
        self.candidates = candidates or FIXTURE_CANDIDATES

    def search(self, parsed: ParsedAddress) -> list[Candidate]:
        pool = self.candidates
        if parsed.municipality:
            nearby = [candidate for candidate in pool if similarity(parsed.municipality.value, candidate.municipality) >= 0.62]
            pool = nearby or pool
        if parsed.poi_categories:
            wanted = {item.value for item in parsed.poi_categories}
            poi_hits = [candidate for candidate in pool if wanted.intersection(candidate.poi_categories)]
            pool = list({candidate.id: candidate for candidate in poi_hits + pool}.values())
        return pool


def recommended_question(parsed: ParsedAddress, candidate_count: int) -> str | None:
    if not parsed.municipality:
        return "¿En qué municipio o alcaldía se encuentra?"
    if not parsed.streets and not parsed.intersections and not parsed.poi_categories:
        return "¿Me puede decir alguna calle cercana, referencia o entre qué calles está?"
    if candidate_count > 2 and not parsed.house_number and not parsed.block and not parsed.lot:
        return "¿Tiene número exterior, manzana/lote o alguna referencia más cercana?"
    if parsed.ambiguities:
        return "¿Puede confirmar la calle o referencia que mencionó?"
    return None
