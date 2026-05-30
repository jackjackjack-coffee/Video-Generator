"""creativeforge CLI — entrypoint commands."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from creativeforge.adapters import base as _adapter_base  # ensures registry populated
import creativeforge.adapters  # noqa: F401 — populates registry
from creativeforge.config import ProjectConfig
from creativeforge.pipeline import Pipeline, run_pipeline


def _force_utf8_stdio() -> None:
    """Make console output encoding-safe on non-UTF-8 locales (e.g. Korean cp949).

    rich renders through ``sys.stdout``; on a cp949 console that stream can't
    encode the UI's bullets/em-dashes (``•`` ``—``) or Korean text, so a render
    crashes with ``UnicodeEncodeError`` mid-run. Reconfiguring stdio to UTF-8
    makes modern terminals (Windows Terminal, codepage 65001) render correctly;
    ``errors="replace"`` keeps legacy consoles from crashing (worst case: a few
    replacement chars). Mutates the existing streams in place, so Console
    instances created elsewhere pick it up regardless of import order.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


_force_utf8_stdio()

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
    """Show registered adapters and environment health pre-flight."""
    adapter_table = Table(title="Registered adapters")
    adapter_table.add_column("name")
    for n in _adapter_base.list_adapters():
        adapter_table.add_row(n)
    console.print(adapter_table)

    health_table = Table(title="Environment health")
    health_table.add_column("check")
    health_table.add_column("status")
    health_table.add_column("detail")

    def _row(label: str, ok: bool, detail: str = "") -> None:
        status = "[green]OK[/green]" if ok else "[yellow]WARN[/yellow]"
        health_table.add_row(label, status, detail)

    _row("PIXABAY_API_KEY", bool(os.environ.get("PIXABAY_API_KEY")), "required for s04_audio")

    try:
        import edge_tts  # noqa: F401
        _row("edge_tts", True, "voice synthesis ready")
    except ImportError:
        _row("edge_tts", False, "pip install edge-tts")

    voicebox_url = os.environ.get("VOICEBOX_URL", "http://127.0.0.1:17493")
    try:
        import httpx as _httpx
        _httpx.get(voicebox_url, timeout=0.5)
        _row("voicebox", True, f"{voicebox_url} reachable")
    except Exception:
        _row("voicebox", False, f"start the Voicebox app — {voicebox_url} (needed for commercial dub)")

    npm = shutil.which("npm")
    npx = shutil.which("npx")
    _row("npm", bool(npm), npm or "not found — needed for s05_compose")
    _row("npx", bool(npx), npx or "not found — needed for s05_compose")

    auth_json = Path(".auth/google.json")
    auth_profile = Path(".auth/chrome-profile")
    _row(".auth/google.json", auth_json.exists(), "login state for Google Flow (run scripts/login_google_flow.py)")
    _row(".auth/chrome-profile/", auth_profile.is_dir(), "browser profile for Google Flow")

    console.print(health_table)


@app.command()
def run(
    project: str = typer.Argument(..., help="project id (folder name under projects/)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip adapter calls; print plan only."),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Skip approval gates."),
    only: str = typer.Option(None, "--only", help="Run only this stage id."),
    from_stage: str = typer.Option(None, "--from", help="Start from this stage id."),
) -> None:
    """Run a project's pipeline end-to-end (stage by stage)."""
    project_dir = Path("projects") / project
    if not project_dir.exists():
        console.print(f"[red]Project not found: {project_dir}[/red]")
        raise typer.Exit(1)

    cfg = ProjectConfig.load(project_dir)
    now = datetime.now()
    run_id = now.strftime("%Y-%m-%d-") + project + "-" + now.strftime("%H%M%S")
    run_dir = Path("runs") / run_id

    console.print(f"[green]Project:[/green] {cfg.project.title} ({cfg.project.id})")
    console.print(f"[green]Run id:[/green] {run_id}")
    console.print(f"[green]Run dir:[/green] {run_dir}")
    console.print(f"[green]Dry run:[/green] {dry_run}  [green]Auto approve:[/green] {auto_approve}")

    table = Table(title="Stages")
    table.add_column("stage")
    table.add_column("adapter")
    table.add_column("model")
    table.add_column("enabled")
    for sid, spec in cfg.stages.items():
        table.add_row(sid, spec.adapter, spec.model or "-", "yes" if spec.enabled else "no")
    console.print(table)

    asyncio.run(
        run_pipeline(
            cfg=cfg,
            project_dir=project_dir,
            run_dir=run_dir,
            dry_run=dry_run,
            auto_approve=auto_approve,
            only=only,
            from_stage=from_stage,
        )
    )


@app.command()
def resume(run_id: str) -> None:
    """Resume an existing run from its last incomplete stage."""
    run_dir = Path("runs") / run_id
    if not (run_dir / "state.json").exists():
        console.print(f"[red]No state.json at {run_dir}[/red]")
        raise typer.Exit(1)

    from creativeforge.state import RunState

    state = RunState.load(run_dir)
    data = state.data

    project_id = data.get("project")
    if not project_id:
        console.print("[red]state.json missing 'project' field[/red]")
        raise typer.Exit(1)

    project_dir = Path("projects") / project_id
    if not project_dir.exists():
        console.print(f"[red]Project directory not found: {project_dir}[/red]")
        raise typer.Exit(1)

    cfg = ProjectConfig.load(project_dir)

    tmp = Pipeline(cfg=cfg, project_dir=project_dir, run_dir=run_dir)
    order = tmp._topo_order()
    stages_state = data.get("stages") or {}

    from_stage: str | None = None
    for sid in order:
        stage_status = (stages_state.get(sid) or {}).get("status", "pending")
        if stage_status != "approved":
            from_stage = sid
            break

    if from_stage is None:
        console.print(f"[green]Run {run_id} is already fully approved — nothing to resume.[/green]")
        raise typer.Exit(0)

    console.print(f"[green]Resuming run:[/green] {run_id}")
    console.print(f"[green]From stage:[/green] {from_stage}")

    asyncio.run(
        run_pipeline(
            cfg=cfg,
            project_dir=project_dir,
            run_dir=run_dir,
            from_stage=from_stage,
            resume_mode=True,
        )
    )


@app.command()
def credits(project: str) -> None:
    """Show the video-generation credit budget breakdown for a project."""
    project_dir = Path("projects") / project
    if not project_dir.exists():
        console.print(f"[red]Project not found: {project_dir}[/red]")
        raise typer.Exit(1)

    from creativeforge.pipeline import plan_video_credits

    cfg = ProjectConfig.load(project_dir)
    plan = plan_video_credits(project_dir, cfg)
    if plan is None:
        console.print("[yellow]No video stage / prompts file found.[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f"Video credit estimate — {project}")
    table.add_column("cut")
    table.add_column("model")
    table.add_column("variants", justify="right")
    table.add_column("dur(s)", justify="right")
    table.add_column("source")
    table.add_column("credits", justify="right")
    for row in plan["rows"]:
        table.add_row(
            row["id"],
            str(row["model"]),
            str(row["variants"]),
            str(row["duration_s"] or "-"),
            row["source"],
            str(row["credits"]),
        )
    console.print(table)

    budget = cfg.credits.monthly_budget
    flow = plan["totals"].get("flow", 0)
    gemini = plan["totals"].get("gemini", 0)
    console.print(f"[bold]Flow credits:[/bold] {flow} / {budget}  (remaining {budget - flow})")
    if gemini:
        console.print(f"[bold]Gemini (separate pool):[/bold] {gemini}")
    if flow > budget:
        console.print(
            f"[bold red]⚠ Over budget by {flow - budget} credits.[/bold red] "
            "Switch hero cuts to fewer variants, or move some cuts to "
            "veo-3.1-fast / omni-flash / source: gemini."
        )
    else:
        console.print(f"[green]✓ Within budget — {budget - flow} credits free for regenerations.[/green]")


@app.command()
def process_doc(
    run_id: str,
    pdf: bool = typer.Option(False, "--pdf", help="Compile screenshots into a PDF (requires fpdf2)."),
    html: bool = typer.Option(False, "--html", help="Compile screenshots into an HTML gallery."),
) -> None:
    """List (or compile to PDF/HTML) process screenshots captured during a run."""
    run_dir = Path("runs") / run_id
    doc_dir = run_dir / "process-doc"
    if not doc_dir.exists():
        console.print(f"[yellow]No process-doc directory at {doc_dir}[/yellow]")
        raise typer.Exit(0)

    shots = sorted(doc_dir.rglob("*.png"))
    if not shots:
        console.print(f"[yellow]No screenshots found under {doc_dir}[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f"Process screenshots — {run_id}")
    table.add_column("stage")
    table.add_column("item")
    table.add_column("step")
    for s in shots:
        # filename: "{item_id}-{step}.png"  e.g. "cut01-2-prompt-entered.png"
        # Split on first "-" that is followed by a digit (start of step number)
        import re
        m = re.match(r"^(.+?)-(\d-.+)$", s.stem)
        if m:
            item, step = m.group(1), m.group(2)
        else:
            item, step = s.stem, "?"
        table.add_row(s.parent.name, item, step)
    console.print(table)
    console.print(f"[dim]Total: {len(shots)} screenshot(s)[/dim]")

    if pdf:
        _compile_pdf(shots, run_dir / "process-doc.pdf")
    elif html:
        out = _compile_html(shots, run_dir / "process-doc.html")
        console.print(f"[green]HTML gallery:[/green] {out}")


def _compile_pdf(shots: list[Path], out_path: Path) -> None:
    try:
        from fpdf import FPDF
    except ImportError:
        console.print("[red]fpdf2 not installed. Run: pip install fpdf2[/red]")
        return
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    for s in shots:
        pdf.add_page()
        pdf.image(str(s), x=10, y=10, w=190)
        pdf.set_font("Helvetica", size=8)
        pdf.set_y(260)
        pdf.cell(0, 5, f"{s.parent.name}/{s.name}")
    pdf.output(str(out_path))
    console.print(f"[green]PDF compiled:[/green] {out_path}")


def _compile_html(shots: list[Path], out_path: Path) -> Path:
    imgs = "\n".join(
        f'<figure style="margin:0 0 2em"><img src="{s.resolve()}" style="max-width:100%">'
        f'<figcaption style="font-size:12px;color:#666">{s.parent.name}/{s.name}</figcaption></figure>'
        for s in shots
    )
    html = (
        "<!DOCTYPE html><html><head><meta charset=utf-8>"
        "<title>Process screenshots</title></head>"
        f"<body style='font-family:sans-serif;max-width:900px;margin:auto'>"
        f"<h1>Process screenshots</h1>{imgs}</body></html>"
    )
    out_path.write_text(html, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    app()
