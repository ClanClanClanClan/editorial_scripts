"""
Report command for the Editorial Assistant CLI.

This module implements report generation functionality.
"""

import click
from pathlib import Path
import json
from datetime import datetime


@click.command()
@click.argument('journal', required=False)
@click.option('--all', 'report_all', is_flag=True, help='Generate report for all journals')
@click.option('--format', 'output_format', type=click.Choice(['md', 'html', 'pdf', 'excel']), 
              default='md', help='Output format')
@click.option('--output', type=click.Path(), help='Output file path')
@click.option('--email/--no-email', default=False, help='Email the report')
@click.pass_context
def report(ctx, journal, report_all, output_format, output, email):
    """
    Generate reports from extracted data.
    
    Examples:
        
        # Generate markdown report for MF
        editorial-assistant report MF
        
        # Generate Excel report for all journals
        editorial-assistant report --all --format excel
        
        # Generate and email report
        editorial-assistant report MOR --email
    """
    console = ctx.obj['console']
    config_loader = ctx.obj['config_loader']
    
    # Determine which journals to report on
    if report_all:
        journal_codes = config_loader.get_all_journal_codes()
    elif journal:
        journal_codes = [journal.upper()]
    else:
        console.print("[red]Error: Specify a journal or use --all[/red]")
        ctx.abort()
    
    # Generate reports
    for journal_code in journal_codes:
        console.print(f"\n[bold]Generating {output_format.upper()} report for {journal_code}...[/bold]")
        
        try:
            if output_format == 'md':
                content = _generate_markdown_report(journal_code, config_loader)
            elif output_format == 'excel':
                console.print("[yellow]Excel format not yet implemented[/yellow]")
                continue
            elif output_format == 'html':
                console.print("[yellow]HTML format not yet implemented[/yellow]")
                continue
            elif output_format == 'pdf':
                console.print("[yellow]PDF format not yet implemented[/yellow]")
                continue
            
            # Save report
            if output:
                output_path = Path(output)
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = Path(f"{journal_code}_report_{timestamp}.{output_format}")
            
            output_path.write_text(content)
            console.print(f"[green]✅ Report saved to: {output_path}[/green]")
            
            # Email if requested
            if email:
                console.print("[yellow]Email functionality not yet implemented[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error generating report: {e}[/red]")


def _generate_markdown_report(journal_code, config_loader):
    """Generate markdown format report."""
    # Find latest results file
    results_pattern = f"data/exports/{journal_code.lower()}/results_*.json"
    results_files = list(Path().glob(results_pattern))
    
    if not results_files:
        raise ValueError(f"No results found for {journal_code}")
    
    # Load latest results
    latest_file = max(results_files, key=lambda p: p.stat().st_mtime)
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    # Generate markdown
    lines = [
        f"# {journal_code} Extraction Report",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        "## Summary",
        "",
        f"- **Journal**: {data.get('journal', {}).get('name', journal_code)}",
        f"- **Extraction Date**: {data.get('extraction_date', 'Unknown')}",
        f"- **Total Manuscripts**: {len(data.get('manuscripts', []))}",
        f"- **Total Referees**: {data.get('stats', {}).get('total_referees', 0)}",
        f"- **PDFs Downloaded**: {data.get('stats', {}).get('total_pdfs', 0)}",
        "",
        "## Manuscripts",
        ""
    ]
    
    # Add manuscript details
    for manuscript in data.get('manuscripts', []):
        lines.extend([
            f"### {manuscript.get('manuscript_id')}",
            f"**Title**: {manuscript.get('title', 'Unknown')}",
            f"**Status**: {manuscript.get('status', 'Unknown')}",
            "",
            "**Referees**:",
            ""
        ])
        
        referees = manuscript.get('referees', [])
        if referees:
            lines.append("| Name | Institution | Status | Due Date |")
            lines.append("|------|------------|--------|----------|")
            
            for referee in referees:
                name = referee.get('name', 'Unknown')
                institution = referee.get('institution', '-')
                status = referee.get('status', 'Unknown')
                due_date = referee.get('dates', {}).get('due', '-')
                
                lines.append(f"| {name} | {institution} | {status} | {due_date} |")
        else:
            lines.append("*No referees assigned*")
        
        lines.append("")
    
    return "\n".join(lines)