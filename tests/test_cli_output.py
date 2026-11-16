import json

from click.testing import CliRunner

import diffbot.cli as cli


class StubClient:
    def extract(self, url, api, fmt):
        return {"objects": [{"title": "T"}]}

    def crawl(self, site, **kwargs):
        return iter(())


def test_extract_output_creates_missing_folders(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "get_client", StubClient)
    out = tmp_path / "a" / "b" / "extracted.json"
    result = CliRunner().invoke(
        cli.main, ["extract", "https://example.com", "-f", "json", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(out.read_text()) == {"objects": [{"title": "T"}]}


def test_crawl_output_creates_missing_folders(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "get_client", StubClient)
    out = tmp_path / "a" / "b" / "crawl.json"
    result = CliRunner().invoke(
        cli.main, ["crawl", "https://example.com", "-f", "json", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
