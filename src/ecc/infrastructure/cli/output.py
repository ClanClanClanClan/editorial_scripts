"""
CLI Output Formatting

Handles various output formats for CLI commands.
"""

import json
from datetime import UTC, datetime
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import TaskID
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree


class OutputFormatter:
    """
    Handles formatting and display of CLI output in various formats.

    Supports:
    - Rich tables for structured data
    - JSON output for machine parsing
    - YAML output for configuration
    - Progress bars for long operations
    """

    def __init__(self, console: Console):
        """Initialize output formatter."""
        self.console = console

    def format_data(
        self, data: dict | list | Any, format_type: str = "table", title: str | None = None
    ) -> None:
        """Format and display data in specified format."""

        if format_type == "json":
            self._format_json(data)
        elif format_type == "yaml":
            self._format_yaml(data)
        elif format_type == "table":
            self._format_table(data, title)
        else:
            self.console.print(f"Unsupported format: {format_type}")

    def _format_json(self, data: Any) -> None:
        """Format data as JSON."""
        json_str = json.dumps(data, indent=2, default=str)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
        self.console.print(syntax)

    def _format_yaml(self, data: Any) -> None:
        """Format data as YAML."""
        yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
        syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False)
        self.console.print(syntax)

    def _format_table(self, data: Any, title: str | None = None) -> None:
        """Format data as Rich table."""
        if isinstance(data, list) and data:
            self._format_list_table(data, title)
        elif isinstance(data, dict):
            self._format_dict_table(data, title)
        else:
            # Simple display for other types
            self.console.print(Panel(str(data), title=title or "Data"))

    def _format_list_table(self, data: list[dict], title: str | None = None) -> None:
        """Format list of dictionaries as table."""
        if not data:
            self.console.print("No data to display")
            return

        # Get all unique keys from all dictionaries
        all_keys = set()
        for item in data:
            if isinstance(item, dict):
                all_keys.update(item.keys())

        if not all_keys:
            self.console.print("No structured data to display")
            return

        # Create table
        table = Table(title=title)

        # Add columns
        for key in sorted(all_keys):
            table.add_column(key.replace("_", " ").title(), style="cyan")

        # Add rows
        for item in data:
            if isinstance(item, dict):
                row = []
                for key in sorted(all_keys):
                    value = item.get(key, "")
                    # Format value for display
                    if isinstance(value, datetime):
                        formatted_value = value.strftime("%Y-%m-%d %H:%M:%S")
                    elif isinstance(value, list | dict):
                        formatted_value = f"{type(value).__name__}({len(value)})"
                    else:
                        formatted_value = str(value)[:50]  # Truncate long values
                    row.append(formatted_value)
                table.add_row(*row)

        self.console.print(table)

    def _format_dict_table(self, data: dict, title: str | None = None) -> None:
        """Format dictionary as key-value table."""
        table = Table(title=title or "Configuration")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        for key, value in data.items():
            # Format value for display
            if isinstance(value, datetime):
                formatted_value = value.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(value, list | dict):
                formatted_value = f"{type(value).__name__}({len(value)})"
            elif isinstance(value, bool):
                formatted_value = "✅" if value else "❌"
            else:
                formatted_value = str(value)

            table.add_row(key.replace("_", " ").title(), formatted_value)

        self.console.print(table)

    def format_tree(self, data: dict[str, Any], title: str = "Data Tree") -> None:
        """Format hierarchical data as tree."""
        tree = Tree(f"🌳 [bold]{title}[/bold]")
        self._build_tree(tree, data)
        self.console.print(tree)

    def _build_tree(
        self, parent_node, data: Any, max_depth: int = 3, current_depth: int = 0
    ) -> None:
        """Recursively build tree structure."""
        if current_depth >= max_depth:
            parent_node.add("[dim]...(truncated)[/dim]")
            return

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict | list) and value:
                    branch = parent_node.add(f"[cyan]{key}[/cyan]")
                    self._build_tree(branch, value, max_depth, current_depth + 1)
                else:
                    parent_node.add(f"[cyan]{key}[/cyan]: [yellow]{value}[/yellow]")

        elif isinstance(data, list):
            for i, item in enumerate(data[:5]):  # Limit to first 5 items
                branch = parent_node.add(f"[dim]\\[{i}][/dim]")
                self._build_tree(branch, item, max_depth, current_depth + 1)

            if len(data) > 5:
                parent_node.add(f"[dim]... and {len(data) - 5} more items[/dim]")

    def show_progress(self, operation: str, total: int | None = None) -> TaskID:
        """Start progress display for operation."""
        # This would be used with a context manager in the calling code
        # For now, just return a placeholder
        return TaskID(0)

    def format_extraction_summary(
        self,
        journal: str,
        total_manuscripts: int,
        successful_extractions: int,
        failed_extractions: int,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        """Format extraction operation summary."""

        duration = end_time - start_time
        success_rate = (
            (successful_extractions / total_manuscripts * 100) if total_manuscripts > 0 else 0
        )

        # Create summary panel
        summary_text = f"""
[bold]Journal:[/bold] {journal.upper()}
[bold]Total Manuscripts:[/bold] {total_manuscripts}
[bold]Successful:[/bold] [green]{successful_extractions}[/green]
[bold]Failed:[/bold] [red]{failed_extractions}[/red]
[bold]Success Rate:[/bold] {success_rate:.1f}%
[bold]Duration:[/bold] {duration.total_seconds():.2f} seconds
[bold]Start Time:[/bold] {start_time.strftime('%Y-%m-%d %H:%M:%S')}
[bold]End Time:[/bold] {end_time.strftime('%Y-%m-%d %H:%M:%S')}
"""

        panel = Panel(
            summary_text,
            title="📊 Extraction Summary",
            border_style="green" if failed_extractions == 0 else "yellow",
        )

        self.console.print(panel)

    def format_health_status(self, components: list[dict[str, Any]]) -> None:
        """Format system health status."""

        # Overall health
        all_healthy = all(component.get("healthy", False) for component in components)
        status_color = "green" if all_healthy else "red"

        # Create health table
        table = Table(title=f"[{status_color}]System Health Status[/{status_color}]")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details")
        table.add_column("Last Check")

        for component in components:
            name = component.get("name", "Unknown")
            healthy = component.get("healthy", False)
            details = component.get("details", "")
            last_check = component.get("last_check", datetime.now(UTC))

            status_icon = "🟢 Healthy" if healthy else "🔴 Error"

            table.add_row(
                name,
                status_icon,
                details[:50] + "..." if len(details) > 50 else details,
                last_check.strftime("%H:%M:%S"),
            )

        self.console.print(table)

        # Overall status panel
        status_text = "All systems operational" if all_healthy else "Some systems require attention"
        panel_color = "green" if all_healthy else "red"

        panel = Panel(f"[{panel_color}]{status_text}[/{panel_color}]", title="Overall Status")

        self.console.print(panel)

    def show_error(self, message: str, details: str | None = None) -> None:
        """Display error message."""
        error_text = f"[red]❌ {message}[/red]"

        if details:
            error_text += f"\n[dim]{details}[/dim]"

        panel = Panel(error_text, title="Error", border_style="red")

        self.console.print(panel)

    def show_warning(self, message: str, details: str | None = None) -> None:
        """Display warning message."""
        warning_text = f"[yellow]⚠️  {message}[/yellow]"

        if details:
            warning_text += f"\n[dim]{details}[/dim]"

        panel = Panel(warning_text, title="Warning", border_style="yellow")

        self.console.print(panel)

    def show_success(self, message: str, details: str | None = None) -> None:
        """Display success message."""
        success_text = f"[green]✅ {message}[/green]"

        if details:
            success_text += f"\n[dim]{details}[/dim]"

        panel = Panel(success_text, title="Success", border_style="green")

        self.console.print(panel)
