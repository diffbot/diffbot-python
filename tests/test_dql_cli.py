import json

import httpx
import pytest
from click.testing import CliRunner

from diffbot import Diffbot
from diffbot.cli import main
from diffbot.cli import dql as dql_mod
from diffbot.cli import ontology


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
def ontology_cache(tmp_path, monkeypatch):
    path = tmp_path / "ontology.json"
    path.write_text(json.dumps(FIXTURE_ONTOLOGY))
    monkeypatch.setattr(ontology, "ONTOLOGY_PATH", path)
    ontology._CACHE.clear()
    yield
    ontology._CACHE.clear()


def make_client(handler) -> Diffbot:
    return Diffbot(token="test-token", transport=httpx.MockTransport(handler))


def use_mock_client(monkeypatch, handler):
    monkeypatch.setattr(dql_mod, "get_client", lambda: make_client(handler))


def test_ontology_navigation_helpers(ontology_cache):
    assert ontology.list_types() == ["Organization", "Person"]
    assert ontology.list_composites() == ["Location"]
    assert ontology.list_enums() == ["Language"]
    assert ontology.enum_values("Language") == ["EN", "FR", "DE"]
    assert ontology.taxonomy_values("OrganizationCategory", "semi") == ["Semiconductor Companies"]
    assert ontology.find_named("compan") == ["Semiconductor Companies"]


def test_ontology_fields_filters_deprecated(ontology_cache):
    fields = ontology.fields_for("Organization")
    names = [n for n, _ in ontology.filter_fields(fields, None)]
    assert "oldField" not in names
    names_incl = [n for n, _ in ontology.filter_fields(fields, None, include_deprecated=True)]
    assert "oldField" in names_incl
    assert ontology.format_field("location", fields["location"]) == "location: [Location] [isComposite]"


def test_cli_ontology_types(ontology_cache):
    result = CliRunner().invoke(main, ["dql", "ontology", "types"])
    assert result.exit_code == 0
    assert result.output.split() == ["Organization", "Person"]


def test_cli_probe_table(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["size"] == "0"
        hits = 5 if "Diffbot" in request.url.params["query"] else 100
        return httpx.Response(200, json={"hits": hits, "results": 0})

    use_mock_client(monkeypatch, handler)
    result = CliRunner().invoke(
        main,
        ["dql", "probe", 'type:Organization name:"Diffbot"', "type:Organization"],
    )
    assert result.exit_code == 0
    lines = result.output.splitlines()
    assert lines[0] == '  5  type:Organization name:"Diffbot"'
    assert lines[1] == "100  type:Organization"


def test_cli_probe_json(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"hits": 7, "results": 0})

    use_mock_client(monkeypatch, handler)
    result = CliRunner().invoke(main, ["dql", "probe", "--json", "type:Person"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == [{"query": "type:Person", "hits": 7, "results": 0}]


def test_cli_export_writes_file(monkeypatch, tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["format"] == "csv"
        return httpx.Response(200, content=b"Name\nDiffbot\n")

    use_mock_client(monkeypatch, handler)
    out = tmp_path / "out.csv"
    result = CliRunner().invoke(main, ["dql", "export", "type:Organization", "--out", str(out)])
    assert result.exit_code == 0
    assert out.read_bytes() == b"Name\nDiffbot\n"
    assert "saved:" in result.output
