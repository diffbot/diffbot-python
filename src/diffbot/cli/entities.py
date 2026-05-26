"""CLI command: db entities — identify and resolve entities in text via the Diffbot NLP API."""

import json
import sys

import click
from rich.console import Console
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from diffbot import AuthError, APIError

from ._common import get_client

console = Console()

_PALETTE = [
    "cyan", "magenta", "yellow", "green", "blue", "red",
    "bright_cyan", "bright_magenta", "bright_yellow", "bright_green",
]


def _sentiment_label(score) -> str:
    if score is None:
        return ""
    if score > 0.1:
        return f"[green]+{score:.2f}[/green]"
    if score < -0.1:
        return f"[red]{score:.2f}[/red]"
    return f"[dim]{score:.2f}[/dim]"


def _highlight_mentions(text: str, ents: list, palette: list) -> str:
    spans = []
    for i, e in enumerate(ents):
        color = palette[i % len(palette)]
        for m in e.get("mentions", []):
            begin = m.get("beginOffset")
            end = m.get("endOffset")
            if begin is not None and end is not None:
                spans.append((begin, end, color))

    if not spans:
        return escape(text)

    spans.sort(key=lambda s: s[0])

    parts = []
    pos = 0
    for begin, end, color in spans:
        if begin < pos:
            continue  # skip overlapping spans
        parts.append(escape(text[pos:begin]))
        parts.append(f"[bold underline {color}]{escape(text[begin:end])}[/bold underline {color}]")
        pos = end
    parts.append(escape(text[pos:]))
    return "".join(parts)


@click.command(name="entities")
@click.argument("text", required=False)
@click.option("-f", "--format", "fmt", type=click.Choice(["table", "json", "dql"]), default="table",
              help="Output format: table (default), json (raw), dql (id:or(...) filter ready for db dql export)")
@click.option("--lang", default="auto", help="Language code (default: auto)")
def entities(text, fmt, lang):
    """Identify and resolve entities and sentiment in text using the Diffbot NLP API.

    TEXT can be passed as an argument or piped via stdin.

    Entity IDs returned can be used in DQL for fast lookups:

      db entities "..." -f dql | xargs db dql export
    """
    if text is None:
        if sys.stdin.isatty():
            raise click.UsageError("provide TEXT as an argument or pipe text via stdin")
        text = sys.stdin.read().strip()
        if not text:
            raise click.UsageError("no text provided")

    db = get_client()
    try:
        is_interactive = sys.stdout.isatty()
        if is_interactive:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                progress.add_task(description="Resolving entities...", total=None)
                result = db.entities(text, lang=lang)
        else:
            result = db.entities(text, lang=lang)

        if fmt == "json":
            sys.stdout.write(json.dumps(result, indent=2))
            sys.stdout.write("\n")
            return

        ents = result.get("entities", [])

        if fmt == "dql":
            ids = []
            for e in ents:
                raw = e.get("id") or e.get("diffbotUri") or ""
                eid = raw.rstrip("/").rsplit("/", 1)[-1] if raw else ""
                if eid:
                    ids.append(eid)
            if not ids:
                return
            sys.stdout.write('id:or(' + ",".join(f'"{i}"' for i in ids) + ')\n')
            return

        doc_sentiment = result.get("sentiment")
        if doc_sentiment is not None:
            console.print(f"Document sentiment: {_sentiment_label(doc_sentiment)}")
            console.print()

        if not ents:
            console.print("[dim]No entities found.[/dim]")
            return

        table = Table(show_header=True, header_style="bold", show_lines=False)
        table.add_column("Entity", overflow="fold")
        table.add_column("Type", no_wrap=True)
        table.add_column("Confidence", no_wrap=True, justify="right")
        table.add_column("Salience", no_wrap=True, justify="right")
        table.add_column("Sentiment", no_wrap=True, justify="right")
        table.add_column("Diffbot ID", overflow="fold", style="dim")

        for i, e in enumerate(ents):
            color = _PALETTE[i % len(_PALETTE)]
            name = e.get("name") or e.get("label") or ""
            all_types = e.get("allTypes") or []
            etype = all_types[0]["name"] if all_types else (e.get("type") or "")
            confidence = e.get("confidence")
            salience = e.get("salience")
            sentiment = e.get("sentiment")
            raw = e.get("id") or e.get("diffbotUri") or ""
            eid = raw.rstrip("/").rsplit("/", 1)[-1] if raw else ""
            conf_str = f"{confidence:.2f}" if confidence is not None else ""
            sal_str = f"{salience:.2f}" if salience is not None else ""
            table.add_row(
                f"[{color}]● {name}[/{color}]",
                etype, conf_str, sal_str, _sentiment_label(sentiment), eid,
            )

        console.print(_highlight_mentions(text, ents, _PALETTE))
        console.print()
        console.print(table)
        console.print(f"[dim]{len(ents)} entit{'y' if len(ents) == 1 else 'ies'} found[/dim]")

    except AuthError:
        click.echo("Error: Invalid or unauthorized API token.", err=True)
        raise click.Abort()
    except APIError as e:
        click.echo(f"API error {e.status_code}: {e.message or e.body}", err=True)
        raise click.Abort()
