"""
Compute Orchestrator — CLI
Manage your live job queue from the terminal.

Usage:
    python cli.py metrics --env prod
    python cli.py jobs list --env prod
    python cli.py jobs list --env prod --status running
    python cli.py jobs history 1 --env prod
"""

import typer
import httpx
from enum import Enum
from typing import Optional


# Environment URLs — switch between local Docker and live Railway
ENVIRONMENTS = {
    "local": "http://localhost:8000",
    "prod":  "https://compute-orchestrator-production.up.railway.app",
}

# Main app and jobs subcommand group
app = typer.Typer(help="Compute Orchestrator CLI", no_args_is_help=True)
jobs_app = typer.Typer(help="Job commands", no_args_is_help=True)
app.add_typer(jobs_app, name="jobs")


# Enum so Typer validates --env values automatically
class EnvOption(str, Enum):
    local = "local"
    prod  = "prod"


def get_base_url(env: str) -> str:
    return ENVIRONMENTS[env]


# Color per job status for terminal output
STATUS_COLORS = {
    "queued":    typer.colors.YELLOW,
    "running":   typer.colors.CYAN,
    "succeeded": typer.colors.GREEN,
    "failed":    typer.colors.RED,
    "exhausted": typer.colors.MAGENTA,
}


# Prints a bold section header with a divider line
def header(text: str):
    typer.echo("")
    typer.echo(typer.style(f"  {text}", fg=typer.colors.BRIGHT_WHITE, bold=True))
    typer.echo(typer.style("  " + "─" * 40, fg=typer.colors.BRIGHT_BLACK))


# Prints a single label/value row with optional color on the value
def row(label: str, value, color=None):
    label_str = typer.style(f"  {label:<20}", fg=typer.colors.BRIGHT_BLACK)
    value_str = typer.style(str(value), fg=color) if color else str(value)
    typer.echo(f"{label_str}{value_str}")


# Formats a datetime string from the API into a readable format
def fmt_dt(dt_str: str | None) -> str:
    if not dt_str:
        return "—"
    return dt_str[:19].replace("T", " ")


@app.command()
def metrics(
    env: EnvOption = typer.Option(EnvOption.local, "--env", "-e", help="local or prod"),
):
    """Live system snapshot — queue depth and status breakdown."""
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
    row("Total", data.get("total", 0))

    avg = data.get("avg_processing_time_seconds")
    if avg is not None:
        row("Avg Time", f"{avg:.2f}s")

    typer.echo("")


@jobs_app.command("list")
def jobs_list(
    env:    EnvOption     = typer.Option(EnvOption.local, "--env", "-e", help="local or prod"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="queued, running, succeeded, failed, exhausted"),
    page:   int           = typer.Option(1,  "--page",  "-p", help="Page number"),
    limit:  int           = typer.Option(10, "--limit", "-l", help="Jobs per page"),
):
    """List jobs with optional filters."""
    base_url = get_base_url(env.value)

    # Build query params — only include status if provided
    params = {"page": page, "limit": limit}
    if status:
        params["status"] = status

    try:
        r = httpx.get(f"{base_url}/jobs", params=params, timeout=10)
        r.raise_for_status()
        jobs = r.json()
    except httpx.ConnectError:
        typer.echo(typer.style(f"\n  ✗  Cannot connect to {base_url}\n", fg=typer.colors.RED))
        raise typer.Exit(1)

    title = f"Jobs  [{env.value.upper()}]"
    if status:
        title += f"  —  {status}"
    header(title)

    if not jobs:
        typer.echo(typer.style("  No jobs found\n", fg=typer.colors.BRIGHT_BLACK))
        return

    # Column headers
    typer.echo(typer.style(f"  {'ID':<6} {'STATUS':<14} {'PRIORITY':<10} {'RETRIES':<10} NAME", fg=typer.colors.BRIGHT_BLACK))

    for job in jobs:
        job_id   = typer.style(f"#{job['id']:<5}", fg=typer.colors.BRIGHT_BLACK)
        status_s = typer.style(job.get("status", "").upper(), fg=STATUS_COLORS.get(job.get("status", ""), typer.colors.WHITE), bold=True)
        priority = typer.style(f"p{job.get('priority', 1):<9}", fg=typer.colors.BRIGHT_BLACK)
        retries  = typer.style(f"{job.get('retry_count', 0)}/{job.get('max_retries', 3):<9}", fg=typer.colors.BRIGHT_BLACK)
        name     = typer.style(job.get("name", ""), fg=typer.colors.BRIGHT_WHITE)
        typer.echo(f"  {job_id} {status_s:<14} {priority} {retries} {name}")

    typer.echo(typer.style(f"\n  page {page}  —  {len(jobs)} jobs shown\n", fg=typer.colors.BRIGHT_BLACK))


@jobs_app.command("history")
def jobs_history(
    job_id: int       = typer.Argument(..., help="Job ID to inspect"),
    env:    EnvOption = typer.Option(EnvOption.local, "--env", "-e", help="local or prod"),
):
    """Full audit trail for a specific job."""
    base_url = get_base_url(env.value)

    try:
        # Fetch job details and event history in two separate calls
        job_r = httpx.get(f"{base_url}/jobs/{job_id}", timeout=10)
        if job_r.status_code == 404:
            typer.echo(typer.style(f"\n  ✗  Job #{job_id} not found\n", fg=typer.colors.RED))
            raise typer.Exit(1)
        job = job_r.json()

        hist_r = httpx.get(f"{base_url}/jobs/{job_id}/history", timeout=10)
        hist_r.raise_for_status()
        events = hist_r.json()
    except httpx.ConnectError:
        typer.echo(typer.style(f"\n  ✗  Cannot connect to {base_url}\n", fg=typer.colors.RED))
        raise typer.Exit(1)

    header(f"Job #{job_id}  [{env.value.upper()}]")
    row("Name",     job.get("name", ""))
    row("Status",   typer.style(job.get("status", "").upper(), fg=STATUS_COLORS.get(job.get("status", ""), typer.colors.WHITE), bold=True))
    row("Priority", f"p{job.get('priority', 1)}")
    row("Retries",  f"{job.get('retry_count', 0)} / {job.get('max_retries', 3)}")
    row("Created",  fmt_dt(job.get("created_at")))
    if job.get("locked_by"):
        row("Locked By", job.get("locked_by"), typer.colors.CYAN)

    typer.echo("")
    typer.echo(typer.style("  Timeline", fg=typer.colors.BRIGHT_WHITE, bold=True))
    typer.echo(typer.style("  " + "─" * 40, fg=typer.colors.BRIGHT_BLACK))

    if not events:
        typer.echo(typer.style("  No events recorded\n", fg=typer.colors.BRIGHT_BLACK))
        return

    # Print each state transition with timestamp and actor
    for event in events:
        from_s  = event.get("from_status") or "none"
        to_s    = event.get("to_status", "")
        actor   = event.get("actor") or "—"
        ts      = fmt_dt(event.get("created_at"))

        ts_str    = typer.style(ts, fg=typer.colors.BRIGHT_BLACK)
        from_str  = typer.style(from_s, fg=typer.colors.BRIGHT_BLACK)
        arrow     = typer.style(" → ", fg=typer.colors.BRIGHT_BLACK)
        to_str    = typer.style(to_s.upper(), fg=STATUS_COLORS.get(to_s, typer.colors.WHITE), bold=True)
        actor_str = typer.style(f"  ← {actor}", fg=typer.colors.BRIGHT_BLACK)

        typer.echo(f"  {ts_str}  {from_str}{arrow}{to_str}{actor_str}")

    typer.echo("")


if __name__ == "__main__":
    app()