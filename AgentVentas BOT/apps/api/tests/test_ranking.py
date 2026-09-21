from address_ai.core.parser import MexicanAddressParser
from address_ai.geo.search import FixtureGeoSearch, recommended_question
from address_ai.ranking.ranker import CandidateRanker


def search(text: str):
    parsed = MexicanAddressParser().parse(text)
    candidates = FixtureGeoSearch().search(parsed)
    return parsed, CandidateRanker().rank(parsed, candidates)


def test_university_mvp_ranks_mecatronica_near_metro_first():
    parsed, ranked = search("universidad por san nicolas cerca del metro que tenga mecatronica")
    assert ranked[0].candidate.id == "mx-nl-sng-u-uanl-fime"
    assert ranked[0].score >= 50
    assert any(item.signal == "semantic" for item in ranked[0].breakdown)


def test_call_example_ranks_address_candidate_first():
    parsed, ranked = search("San Nicolás calle Abedul entre Sauce y otra calle casa 137 frente al panteón")
    assert ranked[0].candidate.id == "mx-nl-sng-abedul-137"
    assert ranked[0].score >= 80
    assert any(item.signal == "poi" for item in ranked[0].breakdown)


def test_recommended_question_when_underspecified():
    parsed, ranked = search("estoy por san nicolas")
    assert recommended_question(parsed, len(ranked)).startswith("¿Me puede decir")
