from address_ai.core.fuzzy import best_match, phonetic_similarity, similarity
from address_ai.core.normalization import normalize_for_match


def test_abbreviations_are_expanded():
    assert normalize_for_match("MZ 4 LT 18 COL SAN JOSE") == "manzana 4 lote 18 colonia san jose"
    assert normalize_for_match("C.P. 64000") == "codigo postal 64000"


def test_fuzzy_and_phonetic_matching():
    assert similarity("San Nicolas de los garza", "San Nicolás de los Garza") > 0.95
    assert phonetic_similarity("istapalapa", "Iztapalapa") > 0.75
    assert best_match("ista palapa", ["Monterrey", "Iztapalapa"])[0] == "Iztapalapa"
