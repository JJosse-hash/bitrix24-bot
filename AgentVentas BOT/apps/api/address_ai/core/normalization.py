from __future__ import annotations

import re
import unicodedata


ABBREVIATIONS: dict[str, str] = {
    "cp": "codigo postal",
    "c p": "codigo postal",
    "mz": "manzana",
    "mza": "manzana",
    "lt": "lote",
    "lte": "lote",
    "num": "numero",
    "no": "numero",
    "n": "numero",
    "av": "avenida",
    "ave": "avenida",
    "blvd": "boulevard",
    "col": "colonia",
    "fracc": "fraccionamiento",
    "mpio": "municipio",
    "mun": "municipio",
    "edo": "estado",
    "int": "interior",
    "depto": "departamento",
    "km": "kilometro",
}

CANONICAL_NAMES: dict[str, str] = {
    "nuevo leon": "Nuevo León",
    "san nicolas": "San Nicolás de los Garza",
    "san nico": "San Nicolás de los Garza",
    "san nicolas de los garza": "San Nicolás de los Garza",
    "monterrey": "Monterrey",
    "guadalupe": "Guadalupe",
    "cdmx": "Ciudad de México",
    "ciudad de mexico": "Ciudad de México",
    "iztapalapa": "Iztapalapa",
    "istapalapa": "Iztapalapa",
    "ista palapa": "Iztapalapa",
}


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def compact_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_for_match(value: str) -> str:
    value = strip_accents(value.lower())
    value = re.sub(r"[#°º.,;:()\[\]{}]", " ", value)
    value = re.sub(r"\b(c\.?\s*p\.?)\b", " cp ", value)
    tokens = []
    for token in compact_spaces(value).split(" "):
        tokens.append(ABBREVIATIONS.get(token, token))
    return compact_spaces(" ".join(tokens))


def display_case(value: str) -> str:
    key = normalize_for_match(value)
    if key in CANONICAL_NAMES:
        return CANONICAL_NAMES[key]
    lowercase = {"de", "del", "la", "las", "los", "y", "el", "a"}
    parts = []
    for index, token in enumerate(compact_spaces(value).split(" ")):
        base = token.lower()
        parts.append(base if index and base in lowercase else base.capitalize())
    return " ".join(parts)


def contains_phrase(text: str, phrase: str) -> bool:
    return f" {normalize_for_match(phrase)} " in f" {normalize_for_match(text)} "
