"""
Compute Orchestrator — CLI
Usage:
    python cli.py --env local metrics
    python cli.py --env prod metrics
"""

import typer
import httpx
from enum import Enum

# ── config ────────────────────────────────────────────────────────────────────

ENVIRONMENTS = {
    "local": "http://localhost:8000",
    "prod":  "https://compute-orchestrator-production.up.railway.app",
}

app = typer.Typer(help="Compute Orchestrator CLI", no_args_is_help=True)


class EnvOption(str, Enum):
    local = "local"
    prod  = "prod"


def get_base_url(env: str) -> str:
    return ENVIRONMENTS[env]

# ── formatting ────────────────────────────────────────────────────────────────

def header(text: str):
    typer.echo("")
    typer.echo(typer.style(f"  {text}", fg=typer.colors.BRIGHT_WHITE, bold=True))
    typer.echo(typer.style("  " + "─" * 40, fg=typer.colors.BRIGHT_BLACK))

def row(label: str, value, color=None):
    label_str = typer.style(f"  {label:<20}", fg=typer.colors.BRIGHT_BLACK)
    value_str = typer.style(str(value), fg=color) if color else str(value)
    typer.echo(f"{label_str}{value_str}")

# ── metrics ───────────────────────────────────────────────────────────────────

@app.command()
def metrics(
    env: EnvOption = typer.Option(EnvOption.local, "--env", "-e", help="local or prod"),
):
    """Live system snapshot."""
    base_url = get_base_url(env.value)

    try:
        r = httpx.get(f"{base_url}/jobs/metrics", timeout=10)
        r.raise_for_status()
        data = r.json()
    except httpx.ConnectError:
        typer.echo(typer.style(f"\n  ✗  Cannot connect to {base_url}\n", fg=typer.colors.RED))
        raise typer.Exit(1)

    header(f"Metrics  [{env.value.upper()}]")
    row("Queued",    data.get("queued", 0),    typer.colors.YELLOW)
    row("Running",   data.get("running", 0),   typer.colors.CYAN)
    row("Succeeded", data.get("succeeded", 0), typer.colors.GREEN)
    row("Failed",    data.get("failed", 0),    typer.colors.RED)
    row("Exhausted", data.get("exhausted", 0), typer.colors.MAGENTA)
    typer.echo(typer.style("  " + "─" * 40, fg=typer.colors.BRIGHT_BLACK))
    row("Total",     data.get("total", 0))

    avg = data.get("avg_processing_time_seconds")
    if avg is not None:
        row("Avg Time", f"{avg:.2f}s")

    typer.echo("")


if __name__ == "__main__":
    app()