"""
Extract command for the Editorial Assistant CLI.

This module implements the extraction functionality.
"""

from pathlib import Path

import click
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ...core.exceptions import EditorialAssistantError
from ...extractors.implementations import MFExtractor, MORExtractor


@click.command()
@click.argument("journal", required=False)
@click.option("--all", "extract_all", is_flag=True, help="Extract all configured journals")
@click.option("--headless/--visible", default=True, help="Run browser in headless mode")
@click.option("--parallel", is_flag=True, help="Extract multiple journals in parallel")
@click.option("--checkpoint-dir", type=click.Path(), help="Directory for checkpoints")
@click.option("--output-dir", type=click.Path(), help="Output directory for results")
@click.pass_context
def extract(ctx, journal, extract_all, headless, parallel, checkpoint_dir, output_dir):
    """
    Extract referee data from journal submission systems.

    Examples:

        # Extract single journal
        editorial-assistant extract MF

        # Extract all journals
        editorial-assistant extract --all

        # Extract with visible browser
        editorial-assistant extract MOR --visible
    """
    console = ctx.obj["console"]
    config_loader = ctx.obj["config_loader"]

    # Determine which journals to extract
    if extract_all:
        journal_codes = config_loader.get_all_journal_codes()
    elif journal:
        journal_codes = [journal.upper()]
    else:
        console.print("[red]Error: Specify a journal or use --all[/red]")
        ctx.abort()

    # Validate journals have credentials
    valid_journals = []
    for code in journal_codes:
        try:
            journal_obj = config_loader.get_journal(code)
            if not journal_obj.credentials:
                console.print(f"[yellow]⚠️  No credentials for {code}, skipping[/yellow]")
            else:
                valid_journals.append(code)
        except Exception as e:
            console.print(f"[red]Error loading {code}: {e}[/red]")

    if not valid_journals:
        console.print("[red]No journals with valid credentials found[/red]")
        ctx.abort()

    # Extract journals
    if parallel and len(valid_journals) > 1:
        _extract_parallel(valid_journals, config_loader, console, headless, checkpoint_dir)
    else:
        _extract_sequential(valid_journals, config_loader, console, headless, checkpoint_dir)


def _extract_sequential(journal_codes, config_loader, console, headless, checkpoint_dir):
    """Extract journals sequentially."""
    results = []

    for journal_code in journal_codes:
        console.print(f"\n[bold blue]Extracting {journal_code}...[/bold blue]")

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task(f"Extracting {journal_code}", total=None)

            try:
                # Get appropriate extractor
                extractor = _get_extractor(journal_code, headless, checkpoint_dir)

                # Perform extraction
                result = extractor.extract()
                results.append(result)

                # Show results
                _display_extraction_result(console, result)

            except EditorialAssistantError as e:
                console.print(f"[red]❌ Extraction failed: {e}[/red]")
            except Exception as e:
                console.print(f"[red]❌ Unexpected error: {e}[/red]")
                console.print_exception()

    # Summary
    _display_summary(console, results)


def _extract_parallel(journal_codes, config_loader, console, headless, checkpoint_dir):
    """Extract journals in parallel."""
    # TODO: Implement parallel extraction using multiprocessing
    console.print(
        "[yellow]Parallel extraction not yet implemented, falling back to sequential[/yellow]"
    )
    _extract_sequential(journal_codes, config_loader, console, headless, checkpoint_dir)


def _get_extractor(journal_code, headless, checkpoint_dir):
    """Get the appropriate extractor for a journal."""
    extractors = {
        "MF": MFExtractor,
        "MOR": MORExtractor,
    }

    extractor_class = extractors.get(journal_code)
    if not extractor_class:
        # Fall back to generic ScholarOne extractor
        from ...extractors.scholarone import ScholarOneExtractor

        return ScholarOneExtractor(
            journal_code,
            headless=headless,
            checkpoint_dir=Path(checkpoint_dir) if checkpoint_dir else None,
        )

    return extractor_class(
        headless=headless, checkpoint_dir=Path(checkpoint_dir) if checkpoint_dir else None
    )


def _display_extraction_result(console, result):
    """Display extraction result in a nice table."""
    table = Table(title=f"{result.journal.name} Extraction Results")

    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Manuscripts", str(len(result.manuscripts)))
    table.add_row("Total Referees", str(result.total_referees))
    table.add_row("PDFs Downloaded", str(result.total_pdfs))
    table.add_row("Errors", str(len(result.errors)))
    table.add_row("Duration", f"{result.duration_seconds:.1f}s")

    console.print(table)

    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for error in result.errors[:5]:  # Show first 5 errors
            console.print(f"  • {error}")
        if len(result.errors) > 5:
            console.print(f"  ... and {len(result.errors) - 5} more")


def _display_summary(console, results):
    """Display summary of all extractions."""
    if not results:
        return

    console.print("\n[bold]Extraction Summary[/bold]")

    total_manuscripts = sum(len(r.manuscripts) for r in results)
    total_referees = sum(r.total_referees for r in results)
    total_pdfs = sum(r.total_pdfs for r in results)
    total_errors = sum(len(r.errors) for r in results)

    table = Table()
    table.add_column("Journal", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Manuscripts")
    table.add_column("Referees")
    table.add_column("PDFs")

    for result in results:
        status = "✅" if result.success else "❌"
        table.add_row(
            result.journal.code,
            status,
            str(len(result.manuscripts)),
            str(result.total_referees),
            str(result.total_pdfs),
        )

    table.add_row(
        "[bold]Total[/bold]",
        "",
        f"[bold]{total_manuscripts}[/bold]",
        f"[bold]{total_referees}[/bold]",
        f"[bold]{total_pdfs}[/bold]",
    )

    console.print(table)

    if total_errors > 0:
        console.print(f"\n[yellow]⚠️  Total errors: {total_errors}[/yellow]")
