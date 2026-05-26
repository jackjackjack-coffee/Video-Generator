"""creativeforge CLI — entrypoint commands.

Status: skeletal. `run` and `resume` print intended action; full pipeline orchestration
(stage iteration, approval gate wiring, adapter dispatch) is the next session's main task.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from creativeforge.adapters import base as _adapter_base  # ensures registry populated
import creativeforge.adapters  # noqa: F401 — populates registry
from creativeforge.config import ProjectConfig

app = typer.Typer(add_completion=False, help="creativeforge — multi-project AI video pipeline")
console = Console()


@app.command()
def list() -> None:
    """List available projects under projects/."""
    root = Path("projects")
    if not root.exists():
        console.print("[yellow]No projects/ directory found.[/yellow]")
        raise typer.Exit(0)
    table = Table(title="Projects")
    table.add_column("id")
    table.add_column("title")
    table.add_column("path")
    for p in sorted(root.iterdir()):
        if not (p / "project.yaml").exists():
            continue
        cfg = ProjectConfig.load(p)
        table.add_row(cfg.project.id, cfg.project.title, str(p))
    console.print(table)


@app.command()
def doctor() -> None:
    """Show registered adapters and basic env health."""
    table = Table(title="Registered adapters")
    table.add_column("name")
    for n in _adapter_base.list_adapters():
        table.add_row(n)
    console.print(table)


@app.command()
def run(
    project: str = typer.Argument(..., help="project id (folder name under projects/)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip adapter calls; print plan only."),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Skip approval gates."),
) -> None:
    """Run a project's pipeline end-to-end (stage by stage)."""
    project_dir = Path("projects") / project
    if not project_dir.exists():
        console.print(f"[red]Project not found: {project_dir}[/red]")
        raise typer.Exit(1)

    cfg = ProjectConfig.load(project_dir)
    run_id = datetime.now().strftime("%Y-%m-%d-") + project + "-" + datetime.now().strftime("%H%M%S")
    run_dir = Path("runs") / run_id

    console.print(f"[green]Project:[/green] {cfg.project.title} ({cfg.project.id})")
    console.print(f"[green]Run id:[/green] {run_id}")
    console.print(f"[green]Run dir:[/green] {run_dir}")
    console.print(f"[green]Dry run:[/green] {dry_run}")
    console.print(f"[green]Auto approve:[/green] {auto_approve}")

    table = Table(title="Stages")
    table.add_column("stage")
    table.add_column("adapter")
    table.add_column("model")
    table.add_column("enabled")
    for sid, spec in cfg.stages.items():
        table.add_row(sid, spec.adapter, spec.model or "-", "yes" if spec.enabled else "no")
    console.print(table)

    console.print(
        "\n[yellow]Pipeline orchestration is not yet wired. "
        "Next session: implement creativeforge.pipeline.run() that iterates stages, "
        "dispatches adapters, and calls creativeforge.ui.approve.approve_stage between them.[/yellow]"
    )


@app.command()
def resume(run_id: str) -> None:
    """Resume an existing run from its last incomplete stage."""
    run_dir = Path("runs") / run_id
    if not (run_dir / "state.json").exists():
        console.print(f"[red]No state.json at {run_dir}[/red]")
        raise typer.Exit(1)
    console.print(f"[yellow]resume not implemented yet — would pick up from state.json at {run_dir}[/yellow]")


if __name__ == "__main__":
    app()
