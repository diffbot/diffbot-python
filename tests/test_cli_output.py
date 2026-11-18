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


def _crawl_kwargs(monkeypatch, *args):
    captured = {}

    class Capture(StubClient):
        def crawl(self, site, **kwargs):
            captured.update(kwargs)
            return iter(())

    monkeypatch.setattr(cli, "get_client", Capture)
    result = CliRunner().invoke(cli.main, ["crawl", "https://example.com", *args])
    assert result.exit_code == 0, result.output
    return captured


def test_crawl_cli_bool_flags_default_to_api_defaults(monkeypatch):
    kw = _crawl_kwargs(monkeypatch)
    assert kw["obey_robots"] is None
    assert kw["use_proxies"] is None
    assert kw["restrict_domain"] is True


def test_crawl_cli_bool_flags_can_be_turned_off(monkeypatch):
    kw = _crawl_kwargs(monkeypatch, "--no-obey-robots", "--no-use-proxies", "--no-restrict-domain")
    assert kw["obey_robots"] is False
    assert kw["use_proxies"] is False
    assert kw["restrict_domain"] is False


def test_crawl_cli_bool_flags_can_be_turned_on(monkeypatch):
    kw = _crawl_kwargs(monkeypatch, "--obey-robots", "--use-proxies")
    assert kw["obey_robots"] is True
    assert kw["use_proxies"] is True
