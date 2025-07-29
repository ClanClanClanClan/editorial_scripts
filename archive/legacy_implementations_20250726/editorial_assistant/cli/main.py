"""
Editorial Assistant CLI - Main entry point.

This module provides the command-line interface for the Editorial Assistant system.
"""

import click
import logging
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

from ..utils.config_loader import ConfigLoader
from .commands import extract, analyze, report


# Setup rich console for beautiful output
console = Console()


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config-dir', type=click.Path(exists=True), help='Configuration directory')
@click.pass_context
def cli(ctx, debug, config_dir):
    """
    Editorial Assistant - Professional Journal Referee Management System
    
    Extract and analyze referee data from academic journal submission systems.
    """
    # Setup logging
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True)
        ]
    )
    
    # Load configuration
    config_loader = ConfigLoader(config_dir=Path(config_dir) if config_dir else None)
    
    # Validate configuration
    validation = config_loader.validate_configuration()
    if validation['errors']:
        console.print("[red]Configuration errors found:[/red]")
        for error in validation['errors']:
            console.print(f"  ❌ {error}")
        ctx.abort()
    
    if validation['warnings']:
        console.print("[yellow]Configuration warnings:[/yellow]")
        for warning in validation['warnings']:
            console.print(f"  ⚠️  {warning}")
    
    # Store config loader in context
    ctx.obj = {
        'config_loader': config_loader,
        'console': console
    }


# Add commands
cli.add_command(extract.extract)
cli.add_command(analyze.analyze)
cli.add_command(report.report)


# Version command
@cli.command()
def version():
    """Show version information."""
    from .. import __version__
    console.print(f"Editorial Assistant v{__version__}")


# Config command
@cli.command()
@click.pass_context
def config(ctx):
    """Show current configuration."""
    config_loader = ctx.obj['config_loader']
    
    console.print("\n[bold]Configured Journals:[/bold]")
    for journal_code in config_loader.get_all_journal_codes():
        journal = config_loader.get_journal(journal_code)
        status = "✅" if journal.credentials else "❌"
        console.print(f"  {status} {journal_code}: {journal.name}")
    
    console.print("\n[bold]System Settings:[/bold]")
    console.print(f"  Headless mode: {config_loader.get_setting('browser.headless_mode', True)}")
    console.print(f"  Log level: {config_loader.get_setting('logging.level', 'INFO')}")
    console.print(f"  Max retries: {config_loader.get_setting('extraction.max_retries', 3)}")


# Init command
@cli.command()
@click.option('--force', is_flag=True, help='Overwrite existing configuration')
def init(force):
    """Initialize configuration files."""
    from shutil import copyfile
    
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # Files to create
    files = {
        'journals.yaml': 'config/journals.yaml',
        'settings.yaml': 'config/settings.yaml',
        'credentials.yaml': 'config/credentials.yaml.example'
    }
    
    for filename, source in files.items():
        target = config_dir / filename
        
        if target.exists() and not force:
            console.print(f"[yellow]⚠️  {filename} already exists (use --force to overwrite)[/yellow]")
            continue
        
        # For credentials, copy from example
        if filename == 'credentials.yaml':
            source_path = Path(source)
            if source_path.exists():
                copyfile(source_path, target)
                console.print(f"[green]✅ Created {filename} from template[/green]")
            else:
                # Create basic template
                target.write_text("""# Editorial Assistant Credentials
# Add your journal credentials here

journals:
  MF:
    username: "your.email@example.com"
    password: "your_password"
  MOR:
    username: "your.email@example.com" 
    password: "your_password"
""")
                console.print(f"[green]✅ Created {filename} template[/green]")
        else:
            console.print(f"[yellow]⚠️  Please manually create {filename}[/yellow]")
    
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Edit config/credentials.yaml with your journal credentials")
    console.print("2. Run 'editorial-assistant config' to verify configuration")
    console.print("3. Run 'editorial-assistant extract MF' to start extracting")


if __name__ == "__main__":
    cli()