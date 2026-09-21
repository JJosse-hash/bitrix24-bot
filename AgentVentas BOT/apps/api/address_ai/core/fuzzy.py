from __future__ import annotations

from difflib import SequenceMatcher

from .normalization import normalize_for_match


def similarity(left: str, right: str) -> float:
    a = normalize_for_match(left)
    b = normalize_for_match(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return max(0.86, SequenceMatcher(None, a, b).ratio())
    return SequenceMatcher(None, a, b).ratio()


def soundex_es(value: str) -> str:
    text = normalize_for_match(value)
    text = text.replace("h", "").replace("v", "b").replace("z", "s").replace("ll", "y")
    text = text.replace("qu", "k").replace("ce", "se").replace("ci", "si")
    consonants = "".join(char for char in text if char.isalpha() and char not in "aeiou")
    return consonants[:8]


def phonetic_similarity(left: str, right: str) -> float:
    return similarity(soundex_es(left), soundex_es(right))


def best_match(query: str, choices: list[str], threshold: float = 0.62) -> tuple[str, float] | None:
    scored = [(choice, max(similarity(query, choice), phonetic_similarity(query, choice) * 0.92)) for choice in choices]
    scored.sort(key=lambda item: item[1], reverse=True)
    if scored and scored[0][1] >= threshold:
        return scored[0]
    return None
