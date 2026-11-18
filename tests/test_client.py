import pytest

from diffbot import Diffbot, DiffbotAsync


def test_defaults_every_endpoint_to_the_public_hosts():
    db = Diffbot(token="t")
    assert db.analyze_url == "https://api.diffbot.com/v3"
    assert db.crawler_url == "https://api.diffbot.com/v3/crawl"
    assert db.llm_url == "https://llm.diffbot.com/rag/v1/chat/completions"
    assert db.web_search_url == "https://llm.diffbot.com/api/v1/web_search"
    assert db.nlp_url == "https://nl.diffbot.com/v1/"
    assert db.dql_url == "https://kg.diffbot.com/kg/v3/dql"
    assert db.ontology_url == "https://kg.diffbot.com/kg/ontology"


def test_derives_every_api_diffbot_com_endpoint_from_a_single_api_base_override():
    db = Diffbot(token="t", api_base="https://staging.example.com")
    assert db.analyze_url == "https://staging.example.com/v3"
    assert db.crawler_url == "https://staging.example.com/v3/crawl"


def test_derives_every_kg_diffbot_com_endpoint_from_a_single_kg_base_override():
    db = Diffbot(token="t", kg_base="https://kg.staging.example.com")
    assert db.dql_url == "https://kg.staging.example.com/kg/v3/dql"
    assert db.ontology_url == "https://kg.staging.example.com/kg/ontology"


def test_derives_every_llm_diffbot_com_endpoint_from_a_single_llm_base_override():
    db = Diffbot(token="t", llm_base="https://llm.staging.example.com")
    assert db.llm_url == "https://llm.staging.example.com/rag/v1/chat/completions"
    assert db.web_search_url == "https://llm.staging.example.com/api/v1/web_search"


def test_derives_the_nl_endpoint_from_nlp_base():
    db = Diffbot(token="t", nlp_base="https://nl.staging.example.com")
    assert db.nlp_url == "https://nl.staging.example.com/v1/"


def test_legacy_per_endpoint_option_wins_over_a_host_base():
    db = Diffbot(
        token="t",
        api_base="https://staging.example.com",
        analyze_url="https://custom.example.com/v3",
    )
    assert db.analyze_url == "https://custom.example.com/v3"
    assert db.crawler_url == "https://staging.example.com/v3/crawl"


def test_async_client_resolves_bases_the_same_way():
    db = DiffbotAsync(token="t", api_base="https://staging.example.com")
    assert db.analyze_url == "https://staging.example.com/v3"
    assert db.crawler_url == "https://staging.example.com/v3/crawl"
    assert db.dql_url == "https://kg.diffbot.com/kg/v3/dql"


def test_token_required_async():
    from diffbot import ValidationError

    with pytest.raises(ValidationError):
        DiffbotAsync(token="")
