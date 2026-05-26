import csv
import io
import json
import pathlib
import re
import shutil
import time

import click
import sys
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from diffbot import DiffbotError

from . import ontology
from ._common import get_client, resolve_token


class _DqlGroup(click.Group):
    _SECTIONS = [
        (
            "Commands",
            ["export"],
        ),
        (
            "Advanced Commands",
            ["init", "ontology", "probe"],
        ),
    ]

    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except (FileNotFoundError, KeyError, DiffbotError) as e:
            raise click.ClickException(str(e))

    def format_commands(self, ctx, formatter):
        section_cmds = {label: [] for label, _ in self._SECTIONS}
        uncategorized = []

        for name in self.list_commands(ctx):
            cmd = self.commands.get(name)
            if cmd is None or cmd.hidden:
                continue
            placed = False
            for label, names in self._SECTIONS:
                if name in names:
                    section_cmds[label].append((name, cmd))
                    placed = True
                    break
            if not placed:
                uncategorized.append((name, cmd))

        for label, _ in self._SECTIONS:
            cmds = section_cmds[label]
            if not cmds:
                continue
            with formatter.section(f"{label}"):
                formatter.write_dl(
                    [(name, cmd.get_short_help_str(formatter.width)) for name, cmd in cmds]
                )

        if uncategorized:
            with formatter.section("Other"):
                formatter.write_dl(
                    [(name, cmd.get_short_help_str(formatter.width)) for name, cmd in uncategorized]
                )


@click.group("dql", cls=_DqlGroup)
def dql():
    """Construct and run Diffbot Query Language (DQL) queries against the Knowledge Graph."""


@dql.command("init")
@click.option("--max-age", type=int, default=0, help="Skip the ontology re-download if the local copy is younger than N seconds (default 0 = always refresh).")
@click.option("--keep-tmp", is_flag=True, help="Don't clear ~/.diffbot/tmp.")
def init(max_age: int, keep_tmp: bool):
    """Cache the Diffbot ontology and reset the tmp workspace."""
    base = pathlib.Path.home() / ".diffbot"
    base.mkdir(exist_ok=True)
    tmp = base / "tmp"
    if not keep_tmp:
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir()

    ont = ontology.ONTOLOGY_PATH
    fresh = ont.exists() and max_age > 0 and (time.time() - ont.stat().st_mtime) < max_age
    if fresh:
        click.echo(f"ontology: cached ({int(time.time() - ont.stat().st_mtime)}s old)")
    else:
        get_client().dql_refresh_ontology(ont)
        click.echo(f"ontology: refreshed -> {ont}")
    ontology._CACHE.pop("data", None)

    if resolve_token():
        click.echo("credentials: token found")
    else:
        click.echo(
            "credentials: MISSING -- no Diffbot API token found\n"
            "  Set the DIFFBOT_API_TOKEN environment variable, or\n"
            "  write 'DIFFBOT_API_TOKEN=YOUR_TOKEN' to ~/.diffbot/credentials",
            err=True,
        )
        raise SystemExit(2)


@dql.group("ontology")
def ontology_group():
    """Navigate the cached Diffbot ontology (types, fields, taxonomies, enums)."""


@ontology_group.command("types")
def ontology_types():
    """List all entity type names."""
    for n in ontology.list_types():
        click.echo(n)


@ontology_group.command("composites")
def ontology_composites():
    """List all composite type names."""
    for n in ontology.list_composites():
        click.echo(n)


@ontology_group.command("enums")
def ontology_enums():
    """List all enum type names."""
    for n in ontology.list_enums():
        click.echo(n)


@ontology_group.command("taxonomies")
def ontology_taxonomies():
    """List all taxonomy names."""
    for n in ontology.list_taxonomies():
        click.echo(n)


@ontology_group.command("fields")
@click.argument("type_name", metavar="TYPE")
@click.argument("search", required=False, default=None)
@click.option("--include-deprecated", is_flag=True)
def ontology_fields(type_name: str, search, include_deprecated: bool):
    """List fields of an entity type or composite (e.g. db dql ontology fields Organization)."""
    fields = ontology.fields_for(type_name)
    for name, meta in ontology.filter_fields(fields, search, include_deprecated=include_deprecated):
        click.echo(ontology.format_field(name, meta))


@ontology_group.command("taxonomy")
@click.argument("name")
@click.argument("search", required=False, default=None)
def ontology_taxonomy(name: str, search):
    """List values of a taxonomy."""
    for v in ontology.taxonomy_values(name, search):
        click.echo(v)


@ontology_group.command("enum")
@click.argument("name")
def ontology_enum(name: str):
    """List values of an enum."""
    for v in ontology.enum_values(name):
        click.echo(v)


@ontology_group.command("search")
@click.argument("term")
def ontology_search(term: str):
    """Generic fallback: search every 'name' field in the ontology by regex."""
    for n in ontology.find_named(term):
        click.echo(n)


@dql.command("probe")
@click.argument("queries", nargs=-1, required=True)
@click.option("--workers", type=int, default=8, help="Maximum concurrent requests (default 8).")
@click.option("--json", "as_json", is_flag=True, help="Emit results as a JSON array instead of a text table.")
def probe(queries, workers: int, as_json: bool):
    """Run multiple DQL queries in parallel and print hit counts (size=0) for each."""
    reqs = [{"query": q, "size": 0} for q in queries]
    results = get_client().dql_parallel(reqs, workers=workers)
    rows = [
        {"query": q, "hits": r.get("hits"), "results": r.get("results")}
        for q, r in zip(queries, results)
    ]
    if as_json:
        click.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    width = max(len(str(row["hits"])) for row in rows)
    for row in rows:
        click.echo(f"{str(row['hits']).rjust(width)}  {row['query']}")


_DEFAULT_SPECS: dict[str, str] = {
    "Organization": "name,Name;summary,Summary;nbEmployees,Employees;location.city.name,City;location.country.name,Country",
    "Person":       "name,Name;$.employments[0].employer.name,Organization;$.employments[0].title,Title;location.city.name,City;location.country.name,Country",
    "Article":      "date.str,Date;title,Title;author,Author;siteName,Site;language,Language",
    "Product":      "name,Name;brand,Brand;category,Category;offerPrice,Price;summary,Summary",
    "*":            "name,Name;description,Description",
}

# Extra fields appended to the stdout default spec for file exports (--out).
# Exports can carry more columns than the terminal table; fill these in per type.
# Format matches _DEFAULT_SPECS: "field.path,Display Name;..." (no leading ';').
_EXPORT_EXTRA_SPECS: dict[str, str] = {
    "Organization": "$.categories[*].name,Industries;revenue.value,Revenue;revenue.currency,Revenue Currency;foundingDate.str,Founding Date",
    "Person":       "allNames,All Names;homepageUri,Website;linkedInUri,LinkedIn;$.employments[1:].employer.name,Employment History;",
    "Article":      "authorUrl,Author URL;$.categories[*].name,Categories;tags.label,Tags;publisherCountry,Publisher Country;text,Text;html,HTML;",
    "Product":      "",
    "*":            "",
}

_TYPE_RE = re.compile(r"\btype:([A-Za-z]+)", re.IGNORECASE)


def _type_for_query(query: str) -> str:
    """Return the entity type named in the query, or '*' if none is found/known."""
    m = _TYPE_RE.search(query)
    if m and m.group(1) in _DEFAULT_SPECS:
        return m.group(1)
    return "*"


def _spec_for_query(query: str) -> str:
    """Return the default stdout exportspec for the entity type found in query."""
    return _DEFAULT_SPECS[_type_for_query(query)]


def _export_spec_for_query(query: str) -> str:
    """Return the default file-export spec: the stdout default plus any per-type extras."""
    t = _type_for_query(query)
    base = _DEFAULT_SPECS[t]
    extra = _EXPORT_EXTRA_SPECS.get(t, "").strip().strip(";")
    return f"{base};{extra}" if extra else base


@dql.command("export")
@click.argument("query")
@click.option("--out", default=None, help="Output file path. If omitted, results are printed to stdout as a table.")
@click.option("--format", "fmt", type=click.Choice(["csv", "xls", "xlsx", "json"]), default="csv", help="Response format for --out (default csv).")
@click.option("--spec", "exportspec", default=None, help="exportspec, e.g. 'name,Name;nbEmployees,Employees;location.city.name,City'")
@click.option("--size", type=int, default=10, help="Page size (default 10).")
@click.option("--from", "from_", type=int, default=0, help="Pagination offset.")
@click.option("--filter", "filter_", default=None, help="Response field filter.")
def export(query: str, out, fmt: str, exportspec, size: int, from_: int, filter_):
    """Execute a DQL query and print to stdout or save to a file."""
    if out is not None:
        resolved_spec = exportspec or _export_spec_for_query(query)
        body = get_client().dql(
            query,
            size=size,
            from_=from_,
            format=fmt,
            exportspec=resolved_spec or None,
            filter=filter_,
            raw=True,
        )
        dest = pathlib.Path(out).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        click.echo(f"saved: {dest} ({len(body)} bytes)")
        return

    client = get_client()
    resolved_spec = exportspec or _spec_for_query(query)

    if sys.stdout.isatty():
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description=f"[Querying...] {query}", total=None)
            hits = client.dql(query, size=0).get("hits", 0)
            csv_bytes = client.dql(query, size=size, from_=from_, format="csv", exportspec=resolved_spec or None, filter=filter_, raw=True)
    else:
        hits = client.dql(query, size=0).get("hits", 0)
        csv_bytes = client.dql(query, size=size, from_=from_, format="csv", exportspec=resolved_spec or None, filter=filter_, raw=True)

    click.echo("")
    click.echo(f"[Query] {query}")

    reader = csv.reader(io.StringIO(csv_bytes.decode("utf-8")))
    rows = list(reader)
    if len(rows) < 2:
        click.echo("(no results)")
        return

    headers, *data_rows = rows
    table = Table(show_header=True, header_style="bold", show_lines=True)
    for i, header in enumerate(headers):
        if i < 3:
            table.add_column(header, overflow="ellipsis", max_width=40, no_wrap=True)
        else:
            table.add_column(header, overflow="ellipsis", max_width=20, no_wrap=True)
    for row in data_rows:
        table.add_row(*row)

    Console().print(table)

    click.echo(f"{len(data_rows)} of {hits} records")
    click.echo("")
    click.echo("Options:")
    click.echo("  --size N     return N records (default 10; -1 for all)")
    click.echo("  --from N     skip the first N records (pagination offset)")
    click.echo("")
