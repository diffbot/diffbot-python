import json
import re
import sys
import textwrap
from email.utils import parsedate_to_datetime

import click
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime

from diffbot import CrawlEventType, AuthError, ExtractionError, APIError

from ._common import get_client

console = Console()
is_interactive = sys.stdout.isatty()


def print_markdown(text):
    if is_interactive:
        console.print(Markdown(text))
    else:
        sys.stdout.write(text)
        sys.stdout.write("\n")


@click.group()
def main():
    """
    Diffbot 🤖 Structure the world's knowledge.
    """
    pass


@main.command(name="extract")
@click.argument("url")
@click.option("-o", "--output", type=click.Path(), help="Write output to file instead of stdout")
@click.option("-f", "--format", "fmt", type=click.Choice(["markdown", "json"]), default="markdown", help="Output format")
@click.option("-a", "--api", type=str, default="analyze", help="Diffbot API to use")
def extract(url, output, fmt, api):
    """Get structured content from a URL."""
    db = get_client()
    try:
        if is_interactive and not output:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                progress.add_task(description="Extracting content...", total=None)
                data = db.extract(url, api=api, fmt=fmt)
        else:
            data = db.extract(url, api=api, fmt=fmt)

        if fmt == "json":
            output_str = json.dumps(data, indent=2)
        else:
            objects = data.get("objects", [])
            if not objects:
                output_str = json.dumps(data, indent=2)
            else:
                obj = objects[0]
                title = obj.get("title", "")
                url = obj.get("pageUrl", "")
                content = obj.get("content", "")
                output_str = f"Title: {title}\n\nURL: {url}\n\nContent: {content}"

        if output:
            with open(output, "w") as f:
                f.write(output_str)
            click.echo(f"Output written to {output}")
        else:
            print_markdown(output_str)
    except ExtractionError as e:
        click.echo(f"Extraction error {e.error_code}: {e.error}", err=True)
        raise click.Abort()
    except AuthError:
        click.echo("Error: Invalid or unauthorized API token.", err=True)
        raise click.Abort()
    except APIError as e:
        click.echo(f"API error {e.status_code}: {e.message or e.body}", err=True)
        raise click.Abort()


@main.command()
@click.argument("prompt")
@click.option("-o", "--output", type=click.Path(), help="Write output to file instead of stdout")
@click.option("--json", "as_json", is_flag=True, help="Output from LLM as JSON")
def ask(prompt: str, output: str = None, as_json: bool = False):
    """Ask a question to the Diffbot LLM"""
    db = get_client()
    stdin_content = sys.stdin.read() if not sys.stdin.isatty() else None
    interactive_mode = is_interactive and not output and not as_json

    messages = [
        {
            "role": "system",
            "content": f"Current local time: {datetime.now().strftime('%A, %B %d, %Y, %I:%M:%S %p %Z')}",
        },
        {"role": "user", "content": prompt},
    ]

    if as_json:
        messages[1]["content"] += "\nReturn the output as a JSON object. Do not include any other text outside of the JSON object."

    if stdin_content:
        messages[1]["content"] = f"<input>{stdin_content}</input>\n" + messages[1]["content"]

    try:
        if interactive_mode:
            response_text = ""
            with Live("", auto_refresh=False, console=console) as live:
                for chunk in db.ask(messages):
                    response_text += chunk
                    live.update(Markdown(response_text))
                    live.refresh()

            messages.append({"role": "assistant", "content": response_text})

            while True:
                try:
                    sys.stdout.write("\n> ")
                    sys.stdout.flush()
                    user_input = input()
                    messages.append({"role": "user", "content": user_input})
                except (KeyboardInterrupt, EOFError):
                    console.print("\nExiting chat...")
                    return

                response_text = ""
                with Live("", auto_refresh=False, console=console) as live:
                    for chunk in db.ask(messages):
                        response_text += chunk
                        live.update(Markdown(response_text))
                        live.refresh()
                messages.append({"role": "assistant", "content": response_text})
        else:
            response = ""
            if output:
                for chunk in db.ask(messages):
                    response += chunk
                with open(output, "w") as f:
                    f.write(response)
                click.echo(f"Output written to {output}")
            elif as_json:
                buffer = ""
                for chunk in db.ask(messages):
                    buffer += chunk
                buffer = buffer[buffer.find("{") : buffer.rfind("}") + 1]
                sys.stdout.write(buffer)
            else:
                for chunk in db.ask(messages):
                    sys.stdout.write(chunk)
    except (KeyboardInterrupt, EOFError):
        console.print("\nExiting chat...")
    except AuthError:
        click.echo("Error: Invalid or unauthorized API token.", err=True)
        raise click.Abort()
    except APIError as e:
        click.echo(f"API error {e.status_code}: {e.message or e.body}", err=True)
        raise click.Abort()


@main.command()
@click.argument("site")
@click.option("--hops", type=int, default=2, help="Maximum link depth from seed URLs")
@click.option("--job-name", type=str, help="Name for the crawler job (generated if not provided)")
@click.option("--max-to-crawl", type=int, default=100, help="Maximum number of pages to crawl")
@click.option("--max-to-process", type=int, default=100, help="Maximum number of pages to process")
@click.option("--restrict-domain", is_flag=True, default=True, help="Restrict crawling to the same domain as seeds")
@click.option("--api-url", type=str, default="", help="Diffbot API endpoint to use for processing")
@click.option("--crawl-delay", type=float, default=-1, help="Delay between requests to the same domain in seconds")
@click.option("--url-crawl-pattern", type=str, help="Only crawl URLs matching this pattern")
@click.option("--url-process-pattern", type=str, help="Only process URLs matching this pattern")
@click.option("--obey-robots", is_flag=True, help="Obey robots.txt rules")
@click.option("--use-proxies", is_flag=True, help="Use proxies for crawling")
@click.option("--custom-headers", type=str, help="Custom HTTP headers to send with requests (newline separated)")
@click.option("-o", "--output", type=click.Path(), help="Write output to file instead of stdout")
@click.option("-f", "--format", "fmt", type=click.Choice(["markdown", "json"]), default="markdown", help="Output format")
def crawl(site, hops, job_name, max_to_crawl, max_to_process, restrict_domain,
          api_url, crawl_delay, url_crawl_pattern, url_process_pattern, obey_robots,
          use_proxies, custom_headers, output, fmt):
    """Crawl a website using the Diffbot Crawler API."""
    db = get_client()
    events = []
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description=f"Crawling {site}...", total=None)

            for event in db.crawl(
                site,
                hops=hops,
                job_name=job_name,
                max_to_crawl=max_to_crawl,
                max_to_process=max_to_process,
                restrict_domain=restrict_domain,
                api_url=api_url,
                crawl_delay=crawl_delay,
                url_crawl_pattern=url_crawl_pattern,
                url_process_pattern=url_process_pattern,
                obey_robots=obey_robots,
                use_proxies=use_proxies,
                custom_headers=custom_headers,
                watch=True,
            ):
                events.append(event)
                if event.event_type == CrawlEventType.JOB_CREATED:
                    progress.console.print(f"Job created: {event.details['job_name']}")
                elif event.event_type == CrawlEventType.URL_PROCESSED:
                    status = event.details.get("status", "")
                    icon = "✓" if status == "Success" else "!"
                    progress.console.print(f"  [{icon}] {event.details['url']}")

        if fmt == "json":
            output_str = json.dumps(
                [{"event_type": e.event_type.value, "timestamp": e.timestamp, "details": e.details} for e in events],
                indent=2,
            )
        else:
            lines = []
            for event in events:
                if event.event_type == CrawlEventType.JOB_CREATED:
                    lines.append(f"# Job: {event.details['job_name']}\n")
                elif event.event_type == CrawlEventType.URL_PROCESSED:
                    lines.append(f"- [{event.details.get('status', 'unknown')}] {event.details['url']}")
            output_str = "\n".join(lines)

        if output:
            with open(output, "w") as f:
                f.write(output_str)
            click.echo(f"Output written to {output}")
        else:
            print_markdown(output_str)
    except AuthError:
        click.echo("Error: Invalid or unauthorized API token.", err=True)
        raise click.Abort()
    except APIError as e:
        click.echo(f"API error {e.status_code}: {e.message or e.body}", err=True)
        raise click.Abort()


@main.command()
@click.argument("job_name", required=False)
def crawl_list_jobs(job_name):
    """List Diffbot crawler jobs or get details for a specific job."""
    db = get_client()
    try:
        if job_name:
            job = db.crawl_get_job(job_name)
            print_markdown(f"# Job: {job_name}\n\n```json\n{json.dumps(job, indent=2)}\n```")
        else:
            jobs = db.crawl_list_jobs()
            if not jobs:
                print_markdown("No crawler jobs found.")
                return
            lines = ["# Diffbot Crawler Jobs\n"]
            for job in jobs:
                name = job.get("name", "Unknown")
                job_type = job.get("type", "Unknown")
                status = job.get("jobStatus", {}).get("message", "Unknown")
                lines.append(f"## {name}")
                lines.append(f"Type: {job_type}")
                lines.append(f"Status: {status}")
                if "pageCrawlSuccesses" in job:
                    lines.append(f"Pages Crawled: {job['pageCrawlSuccesses']}")
                if "pageProcessSuccesses" in job:
                    lines.append(f"Pages Processed: {job['pageProcessSuccesses']}")
                lines.append("\n---\n")
            print_markdown("\n".join(lines))
    except AuthError:
        click.echo("Error: Invalid or unauthorized API token.", err=True)
        raise click.Abort()
    except APIError as e:
        click.echo(f"API error {e.status_code}: {e.message or e.body}", err=True)
        raise click.Abort()


@main.command()
@click.argument("job_name")
def crawl_delete_job(job_name):
    """Delete a Diffbot crawler job."""
    db = get_client()
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description=f"Deleting job {job_name}...", total=None)
            db.crawl_delete_job(job_name)
            progress.console.print(f"Job {job_name} deleted.")
    except AuthError:
        click.echo("Error: Invalid or unauthorized API token.", err=True)
        raise click.Abort()
    except APIError as e:
        click.echo(f"API error {e.status_code}: {e.message or e.body}", err=True)
        raise click.Abort()


def _format_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt = parsedate_to_datetime(date_str)
        return f"{dt.strftime('%b')} {dt.day}, {dt.year}"
    except Exception:
        return date_str[:12].strip()


def _score_color(score: float) -> str:
    if score > 0.85:
        return "bright_green"
    elif score >= 0.7:
        return "green"
    elif score >= 0.5:
        return "yellow"
    return "red"


def _strip_markdown(text: str) -> str:
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)          # images
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text) # links → label
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # headings
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE) # bullets
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE) # numbered lists
    text = re.sub(r'[`*_~]{1,3}', '', text)              # inline code/bold/italic
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


@main.command(name="web-search")
@click.argument("query")
@click.option("-n", "--num-results", type=int, default=None, help="Number of results to return")
@click.option("-m", "--max-tokens", type=int, default=None, help="Limit total response tokens (for agentic use cases)")
@click.option("-f", "--format", "fmt", type=click.Choice(["list", "json", "text"]), default="list", help="Output format (text is plain/agent-friendly)")
def web_search(query: str, num_results, max_tokens, fmt: str):
    """Search the web using the Diffbot LLM web search API."""
    db = get_client()
    try:
        if is_interactive:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                progress.add_task(description="Searching...", total=None)
                data = db.web_search(query, num_results=num_results, max_tokens=max_tokens)
        else:
            data = db.web_search(query, num_results=num_results, max_tokens=max_tokens)

        if fmt == "json":
            sys.stdout.write(json.dumps(data, indent=2))
            sys.stdout.write("\n")
            return

        results = data.get("search_results", [])

        if fmt == "text":
            for i, r in enumerate(results, 1):
                date_fmt = _format_date(r.get("date", ""))
                content = " ".join(r.get("content", "").split())
                lines = [
                    f"[{i}] {r.get('title', '')} (score: {r.get('score', 0):.3f})",
                    f"URL: {r.get('pageUrl', '')}",
                ]
                if date_fmt:
                    lines.append(f"Date: {date_fmt}")
                lines += [f"Content: {content}", "---"]
                sys.stdout.write("\n".join(lines) + "\n")
            return

        time_ms = data.get("timeMs", 0)

        for i, r in enumerate(results, 1):
            score = r.get("score", 0)
            title = r.get("title", "")
            url = r.get("pageUrl", "")
            date = r.get("date", "")
            content = _strip_markdown(r.get("content", ""))

            date_fmt = _format_date(date)
            color = _score_color(score)
            prefix_len = len(date_fmt) + 3 if date_fmt else 0  # " — "
            snippet_width = max(80, console.width * 2 - prefix_len)
            snippet = textwrap.shorten(content, width=snippet_width, placeholder="...")

            console.print(f"[bold]#{i}: {title}[/bold] [[{color}]{score:.3f}[/{color}]]")
            console.print(f"[dim blue]{url}[/dim blue]")
            if date_fmt:
                console.print(f"[dim]{date_fmt}[/dim] — {snippet}")
            else:
                console.print(snippet)
            console.print()

        console.print(f"[dim]{len(results)} result(s) in {time_ms}ms[/dim]")
    except AuthError:
        click.echo("Error: Invalid or unauthorized API token.", err=True)
        raise click.Abort()
    except APIError as e:
        click.echo(f"API error {e.status_code}: {e.message or e.body}", err=True)
        raise click.Abort()


from .dql import dql as _dql_group  # noqa: E402
from .entities import entities as _entities_cmd  # noqa: E402

main.add_command(_dql_group)
main.add_command(_entities_cmd)
