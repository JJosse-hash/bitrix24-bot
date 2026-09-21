import pytest

from address_ai.core.models import LLMAnalysisRequest, LLMTask
from address_ai.core.parser import MexicanAddressParser
from address_ai.llm import DevelopmentLLMProvider, select_llm_model


def test_model_router_prefers_flash_for_simple_extraction():
    assert select_llm_model(LLMTask.quick_extract, ambiguity_count=0, candidate_count=1) == "deepseek-v4-flash"


def test_model_router_prefers_pro_for_ambiguous_or_complex_cases():
    assert select_llm_model(LLMTask.complex_reasoning, ambiguity_count=0, candidate_count=1) == "deepseek-v4-pro"
    assert select_llm_model(LLMTask.quick_extract, ambiguity_count=2, candidate_count=1) == "deepseek-v4-pro"


@pytest.mark.anyio
async def test_development_llm_provider_proposes_geo_tools_without_coordinates():
    parsed = MexicanAddressParser().parse("casa 137 entre abedul y sauce cp 67286 frente al panteon")
    response = await DevelopmentLLMProvider().analyze(LLMAnalysisRequest(text=parsed.raw_text, parsed=parsed))
    names = [tool.name for tool in response.tool_calls]
    assert "search_postal_codes" in names
    assert "search_streets" in names
    assert "find_intersection" in names
    assert response.raw == {}
