import json

import httpx
import pytest

from diffbot import Diffbot, DiffbotAsync, Ontology

FIXTURE_ONTOLOGY = {
    "types": {
        "Organization": {
            "fields": {
                "name": {"type": "String"},
                "location": {"type": "Location", "isComposite": True},
                "oldField": {"type": "String", "isDeprecated": True},
            }
        },
        "Person": {"fields": {"name": {"type": "String"}}},
    },
    "composites": {
        "Location": {"fields": {"city": {"type": "City", "isComposite": True}}},
    },
    "enums": {"Language": {"values": ["EN", "FR", "DE"]}},
    "taxonomies": {
        "OrganizationCategory": {
            "categories": [
                {"name": "Technology", "children": [{"name": "Semiconductor Companies"}]},
            ]
        }
    },
}


@pytest.fixture
def ont() -> Ontology:
    return Ontology(FIXTURE_ONTOLOGY)


def test_navigation_helpers(ont):
    assert ont.types() == ["Organization", "Person"]
    assert ont.composites() == ["Location"]
    assert ont.enums() == ["Language"]
    assert ont.taxonomies() == ["OrganizationCategory"]
    assert ont.enum_values("Language") == ["EN", "FR", "DE"]
    assert ont.taxonomy_values("OrganizationCategory", "semi") == ["Semiconductor Companies"]
    assert ont.find_named("compan") == ["Semiconductor Companies"]


def test_fields_for_routes_types_and_composites(ont):
    assert "name" in ont.fields_for("Organization")
    assert "city" in ont.fields_for("Location")
    with pytest.raises(KeyError):
        ont.fields_for("NopeType")


def test_filter_fields_drops_deprecated_by_default(ont):
    fields = ont.fields_for("Organization")
    names = [n for n, _ in Ontology.filter_fields(fields, None)]
    assert "oldField" not in names
    names_incl = [n for n, _ in Ontology.filter_fields(fields, None, include_deprecated=True)]
    assert "oldField" in names_incl


def test_format_field(ont):
    fields = ont.fields_for("Organization")
    assert Ontology.format_field("location", fields["location"]) == "location: [Location] [isComposite]"


def test_from_json_and_from_path(tmp_path):
    raw = json.dumps(FIXTURE_ONTOLOGY)
    assert Ontology.from_json(raw).types() == ["Organization", "Person"]
    path = tmp_path / "ontology.json"
    path.write_text(raw)
    assert Ontology.from_path(path).enums() == ["Language"]


def test_unknown_taxonomy_and_enum_raise(ont):
    with pytest.raises(KeyError):
        ont.taxonomy_values("Nope")
    with pytest.raises(KeyError):
        ont.enum_values("Nope")


def test_dql_fetch_ontology_returns_ontology():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/ontology")
        return httpx.Response(200, json=FIXTURE_ONTOLOGY)

    db = Diffbot(token="test-token", transport=httpx.MockTransport(handler))
    ont = db.dql_fetch_ontology()
    assert isinstance(ont, Ontology)
    assert ont.types() == ["Organization", "Person"]


@pytest.mark.anyio
async def test_async_dql_fetch_ontology_returns_ontology():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=FIXTURE_ONTOLOGY)

    db = DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler))
    ont = await db.dql_fetch_ontology()
    assert isinstance(ont, Ontology)
    assert ont.composites() == ["Location"]


@pytest.mark.anyio
async def test_async_dql_parallel_runs_all_queries():
    def handler(request: httpx.Request) -> httpx.Response:
        q = request.url.params["query"]
        hits = 5 if "Diffbot" in q else 100
        return httpx.Response(200, json={"hits": hits, "results": 0})

    db = DiffbotAsync(token="test-token", transport=httpx.MockTransport(handler))
    results = await db.dql_parallel(
        [
            {"query": 'type:Organization name:"Diffbot"', "size": 0},
            {"query": "type:Organization", "size": 0},
        ]
    )
    assert [r["hits"] for r in results] == [5, 100]
