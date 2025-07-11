"""
Analyze command for the Editorial Assistant CLI.

This module implements analysis functionality for extracted data.
"""

import click
from pathlib import Path
import json
from rich.table import Table


@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--conflicts', is_flag=True, help='Analyze potential conflicts of interest')
@click.option('--statistics', is_flag=True, help='Generate statistical analysis')
@click.option('--output', type=click.Path(), help='Output file for analysis results')
@click.pass_context
def analyze(ctx, input_file, conflicts, statistics, output):
    """
    Analyze extracted referee data.
    
    Examples:
        
        # Basic analysis
        editorial-assistant analyze results.json
        
        # Conflict of interest analysis
        editorial-assistant analyze results.json --conflicts
        
        # Statistical analysis with output
        editorial-assistant analyze results.json --statistics --output stats.json
    """
    console = ctx.obj['console']
    
    # Load data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    console.print(f"\n[bold]Analyzing: {Path(input_file).name}[/bold]")
    
    # Basic statistics
    if statistics or (not conflicts and not statistics):
        _show_statistics(console, data)
    
    # Conflict analysis
    if conflicts:
        _analyze_conflicts(console, data)
    
    # Save output if requested
    if output:
        # TODO: Implement output saving
        console.print(f"[yellow]Output saving not yet implemented[/yellow]")


def _show_statistics(console, data):
    """Show statistical analysis."""
    manuscripts = data.get('manuscripts', [])
    
    # Calculate statistics
    total_referees = sum(len(m.get('referees', [])) for m in manuscripts)
    
    # Status breakdown
    status_counts = {}
    for m in manuscripts:
        for r in m.get('referees', []):
            status = r.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
    
    # Display statistics
    table = Table(title="Referee Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Manuscripts", str(len(manuscripts)))
    table.add_row("Total Referees", str(total_referees))
    table.add_row("Average Referees per MS", f"{total_referees/len(manuscripts):.1f}" if manuscripts else "0")
    
    console.print(table)
    
    # Status breakdown
    if status_counts:
        status_table = Table(title="Referee Status Breakdown")
        status_table.add_column("Status", style="cyan")
        status_table.add_column("Count", style="green")
        status_table.add_column("Percentage")
        
        for status, count in sorted(status_counts.items()):
            percentage = (count / total_referees * 100) if total_referees > 0 else 0
            status_table.add_row(status, str(count), f"{percentage:.1f}%")
        
        console.print("\n")
        console.print(status_table)


def _analyze_conflicts(console, data):
    """Analyze potential conflicts of interest."""
    console.print("\n[bold]Conflict of Interest Analysis[/bold]")
    
    # Group referees by institution
    institution_referees = {}
    
    for m in data.get('manuscripts', []):
        for r in m.get('referees', []):
            institution = r.get('institution', 'Unknown')
            if institution:
                if institution not in institution_referees:
                    institution_referees[institution] = []
                institution_referees[institution].append({
                    'name': r.get('name'),
                    'manuscript': m.get('manuscript_id')
                })
    
    # Find institutions with multiple referees
    conflicts = []
    for institution, referees in institution_referees.items():
        if len(referees) > 1:
            conflicts.append((institution, referees))
    
    if conflicts:
        console.print(f"\n[yellow]Found {len(conflicts)} institutions with multiple referees:[/yellow]")
        
        for institution, referees in conflicts[:10]:  # Show first 10
            console.print(f"\n[cyan]{institution}[/cyan]")
            for ref in referees:
                console.print(f"  • {ref['name']} (MS: {ref['manuscript']})")
    else:
        console.print("\n[green]No potential conflicts found[/green]")