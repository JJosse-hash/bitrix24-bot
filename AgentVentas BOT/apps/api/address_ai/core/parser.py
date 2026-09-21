from __future__ import annotations

import re

from .models import Evidence, EvidenceStatus, ParsedAddress
from .normalization import CANONICAL_NAMES, display_case, normalize_for_match


POI_KEYWORDS = {
    "panteon": "cementerio",
    "cementerio": "cementerio",
    "iglesia": "iglesia",
    "parroquia": "iglesia",
    "hospital": "hospital",
    "clinica": "hospital",
    "escuela": "escuela",
    "universidad": "universidad",
    "facultad": "universidad",
    "metro": "transporte",
    "estacion": "transporte",
    "oxxo": "tienda",
    "tienda": "tienda",
    "plaza": "plaza",
    "parque": "parque",
}

STREET_PREFIX = r"(?:calle|avenida|boulevard|blvd|av|ave|privada|cerrada|camino|carretera)"
REFERENCE_PREFIX = r"(?:frente a|frente al|enfrente de|atras de|atrás de|cerca de|cerca del|cerca de la|junto a|junto al|a un lado de)"


class MexicanAddressParser:
    def parse(self, text: str) -> ParsedAddress:
        normalized = normalize_for_match(text)
        parsed = ParsedAddress(raw_text=text, normalized_text=normalized)
        self._extract_admin(parsed, normalized)
        self._extract_numbers(parsed, normalized)
        self._extract_streets(parsed, normalized)
        self._extract_references(parsed, normalized)
        self._detect_ambiguity(parsed, normalized)
        return parsed

    def _extract_admin(self, parsed: ParsedAddress, normalized: str) -> None:
        for raw, canonical in CANONICAL_NAMES.items():
            if f" {raw} " in f" {normalized} ":
                evidence = Evidence(value=canonical, confidence=0.92, status=EvidenceStatus.detected)
                if canonical in {"Nuevo León", "Ciudad de México"}:
                    parsed.state = evidence
                else:
                    parsed.municipality = evidence
        if parsed.municipality and parsed.municipality.value == "San Nicolás de los Garza" and not parsed.state:
            parsed.state = Evidence(value="Nuevo León", confidence=0.72, status=EvidenceStatus.hypothesis)

    def _extract_numbers(self, parsed: ParsedAddress, normalized: str) -> None:
        cp = re.search(r"(?:codigo postal)\s*(\d{5})\b|\b(\d{5})\b", normalized)
        if cp:
            parsed.postal_code = Evidence(value=cp.group(1) or cp.group(2), confidence=0.9)
        house = re.search(
            r"(?:numero)\s*(\d+[a-z]?)\b|casa\s*(?:es\s*)?(?:la\s*)?(\d+[a-z]?)\b|(?:calle|avenida|boulevard)\s+[a-z ]+\s+(\d+[a-z]?)\b",
            normalized,
        )
        if house:
            parsed.house_number = Evidence(value=house.group(1) or house.group(2) or house.group(3), confidence=0.82)
        block = re.search(r"manzana\s*(\d+[a-z]?)\b", normalized)
        if block:
            parsed.block = Evidence(value=block.group(1), confidence=0.88)
        lot = re.search(r"lote\s*(\d+[a-z]?)\b", normalized)
        if lot:
            parsed.lot = Evidence(value=lot.group(1), confidence=0.88)
        interior = re.search(r"(?:interior|departamento|piso)\s*([a-z0-9-]+)\b", normalized)
        if interior:
            parsed.interior_number = Evidence(value=interior.group(1), confidence=0.75)

    def _extract_streets(self, parsed: ParsedAddress, normalized: str) -> None:
        between = re.search(r"entre\s+(.+?)\s+y\s+(.+?)(?:\s+(?:numero|casa|colonia|municipio|cerca|frente|atras|$)|$)", normalized)
        if between:
            for value in [between.group(1), between.group(2)]:
                clean = self._clean_entity(value)
                if clean:
                    parsed.intersections.append(Evidence(value=display_case(clean), confidence=0.72, status=EvidenceStatus.hypothesis))
        for match in re.finditer(fr"{STREET_PREFIX}\s+([a-z0-9 ]+?)(?=\s+(?:entre|numero|casa|colonia|municipio|cerca|frente|atras|y\s+otra|$))", normalized):
            clean = self._clean_entity(match.group(1))
            if clean and clean not in {"que", "creo"} and " y " not in f" {clean} ":
                parsed.streets.append(Evidence(value=display_case(clean), confidence=0.8))
        named = re.search(r"(?:se llama|llama)\s+([a-z0-9 ]+?)(?=\s+(?:entre|y|numero|casa|$))", normalized)
        if named:
            parsed.streets.append(Evidence(value=display_case(self._clean_entity(named.group(1))), confidence=0.68, status=EvidenceStatus.hypothesis))

    def _extract_references(self, parsed: ParsedAddress, normalized: str) -> None:
        for keyword, category in POI_KEYWORDS.items():
            if f" {keyword} " in f" {normalized} ":
                parsed.poi_categories.append(Evidence(value=category, confidence=0.84))
        for match in re.finditer(fr"{REFERENCE_PREFIX}\s+(?:una?|el|la|del|de)?\s*([a-z0-9 ]+?)(?=\s+(?:calle|avenida|entre|numero|casa|que|$))", normalized):
            clean = self._clean_entity(match.group(1))
            if clean:
                parsed.references.append(Evidence(value=display_case(clean), confidence=0.7, status=EvidenceStatus.hypothesis))

    def _detect_ambiguity(self, parsed: ParsedAddress, normalized: str) -> None:
        if "creo" in normalized or "otra calle" in normalized:
            parsed.ambiguities.append("El hablante expresó duda sobre una o más pistas.")
        if " no " in f" {normalized} " and ("creo" in normalized or "municipio" in normalized):
            parsed.contradictions.append("Hay una posible corrección o contradicción en la conversación.")
        if not parsed.streets and not parsed.intersections and not parsed.poi_categories:
            parsed.ambiguities.append("Faltan calles o referencias cercanas para ubicar con precisión.")

    def _clean_entity(self, value: str) -> str:
        value = re.sub(r"\b(una?|el|la|del|de|que|creo|se|llama|otra|calle)\b", " ", value)
        return re.sub(r"\s+", " ", value).strip()
