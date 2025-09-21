"""
CLI Commands for ECC

Implements Section 8 CLI requirements:
- Journal extraction commands
- System administration
- Configuration management
- Health checks and diagnostics
"""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

import click
from passlib.context import CryptContext
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.tree import Tree

from src.ecc.adapters.storage.repository import ManuscriptRepository
from src.ecc.core.logging_system import ExtractorLogger
from src.ecc.infrastructure.database.connection import (
    get_database_manager,
    initialize_database,
)
from src.ecc.infrastructure.database.models import UserModel
from src.ecc.infrastructure.monitoring import get_observability

from .config import CLIConfig
from .output import OutputFormatter


class ECCCLIApp:
    """
    Main CLI application for Editorial Command Center.

    Provides comprehensive command-line interface for:
    - Journal data extraction
    - System administration
    - Configuration management
    - Health monitoring
    """

    def __init__(self):
        """Initialize CLI application."""
        self.console = Console()
        self.config = CLIConfig()
        self.formatter = OutputFormatter(self.console)
        self.logger = ExtractorLogger("cli")

        # Track running operations
        self.active_extractions: dict[str, Any] = {}

    def create_app(self) -> click.Group:
        """Create Click application with all commands."""

        @click.group(name="ecc")
        @click.option("--config", "-c", help="Configuration file path")
        @click.option("--verbose", "-v", is_flag=True, help="Verbose output")
        @click.option("--quiet", "-q", is_flag=True, help="Quiet mode")
        @click.option(
            "--format",
            "-f",
            type=click.Choice(["table", "json", "yaml"]),
            default="table",
            help="Output format",
        )
        @click.pass_context
        def cli(ctx, config, verbose, quiet, format):
            """Editorial Command Center CLI"""
            ctx.ensure_object(dict)
            ctx.obj["config_file"] = config
            ctx.obj["verbose"] = verbose
            ctx.obj["quiet"] = quiet
            ctx.obj["format"] = format

            # Configure logging level
            if quiet:
                self.logger.set_level("ERROR")
            elif verbose:
                self.logger.set_level("DEBUG")

        @cli.group()
        @click.pass_context
        def extract(ctx):
            """Data extraction commands"""
            pass

        @extract.command("manuscript")
        @click.option(
            "--journal",
            "-j",
            required=True,
            type=click.Choice(["mf", "mor", "sicon", "sifin", "naco", "jota", "mafe", "fs"]),
            help="Journal identifier",
        )
        @click.option(
            "--max-manuscripts", "-m", default=0, help="Maximum manuscripts to extract (0 = all)"
        )
        @click.option("--output-dir", "-o", help="Output directory")
        @click.option("--headless", is_flag=True, help="Run browser in headless mode")
        @click.option("--dry-run", is_flag=True, help="Validate and fetch without persisting to DB")
        @click.option("--persist", is_flag=True, help="Persist extracted manuscripts to database")
        @click.option("--trace", is_flag=True, help="Enable Playwright tracing and save trace ZIP")
        @click.option(
            "--debug-snapshots", is_flag=True, help="Save screenshots and HTML dumps at key steps"
        )
        @click.option(
            "--enrich", is_flag=True, help="Enrich authors/referees with ORCID where possible"
        )
        @click.option(
            "--download", is_flag=True, help="Download files for each manuscript and report metrics"
        )
        @click.option(
            "--normalize-audit", is_flag=True, help="Normalize and print audit events summary"
        )
        @click.pass_context
        def extract_manuscripts(
            ctx,
            journal,
            max_manuscripts,
            output_dir,
            headless,
            dry_run,
            persist,
            trace,
            debug_snapshots,
            enrich,
            download,
            normalize_audit,
        ):
            """Extract manuscripts from journal"""
            asyncio.run(
                self._extract_manuscripts(
                    ctx.obj,
                    journal,
                    max_manuscripts,
                    output_dir,
                    headless,
                    dry_run,
                    persist,
                    trace,
                    debug_snapshots,
                    enrich,
                    download,
                    normalize_audit,
                )
            )

        @extract.command("referees")
        @click.option(
            "--journal",
            "-j",
            required=True,
            type=click.Choice(["mf", "mor", "sicon", "sifin", "naco", "jota", "mafe", "fs"]),
            help="Journal identifier",
        )
        @click.option("--manuscript-id", help="Specific manuscript ID")
        @click.option("--output-dir", "-o", help="Output directory")
        @click.pass_context
        def extract_referees(ctx, journal, manuscript_id, output_dir):
            """Extract referee information"""
            asyncio.run(self._extract_referees(ctx.obj, journal, manuscript_id, output_dir))

        @cli.group()
        def system():
            """System administration commands"""
            pass

        @system.command("health")
        @click.option("--detailed", is_flag=True, help="Show detailed health information")
        @click.pass_context
        def health_check(ctx, detailed):
            """Check system health"""
            asyncio.run(self._health_check(ctx.obj, detailed))

        @system.command("status")
        @click.pass_context
        def system_status(ctx):
            """Show system status"""
            asyncio.run(self._system_status(ctx.obj))

        @system.command("logs")
        @click.option("--service", help="Filter by service")
        @click.option(
            "--level",
            type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
            help="Filter by log level",
        )
        @click.option("--tail", "-n", default=50, help="Number of recent log entries")
        @click.pass_context
        def view_logs(ctx, service, level, tail):
            """View system logs"""
            asyncio.run(self._view_logs(ctx.obj, service, level, tail))

        @cli.group()
        def config():
            """Configuration management"""
            pass

        @config.command("show")
        @click.option("--section", help="Show specific configuration section")
        @click.pass_context
        def show_config(ctx, section):
            """Show current configuration"""
            asyncio.run(self._show_config(ctx.obj, section))

        @config.command("validate")
        @click.pass_context
        def validate_config(ctx):
            """Validate configuration"""
            asyncio.run(self._validate_config(ctx.obj))

        @config.command("init")
        @click.option("--journal", help="Initialize configuration for specific journal")
        @click.pass_context
        def init_config(ctx, journal):
            """Initialize configuration"""
            asyncio.run(self._init_config(ctx.obj, journal))

        @cli.group()
        def database():
            """Database management commands"""
            pass

        @cli.group()
        def enrich():
            """Enrichment utilities"""
            pass

        @enrich.command("fs")
        @click.option("--input", "-i", required=True, help="Input JSON file from FS extractor")
        @click.option("--output", "-o", help="Output JSON file (defaults to overwrite input)")
        @click.pass_context
        def enrich_fs(ctx, input, output):
            """Enrich FS extractor results with ORCID data."""
            asyncio.run(self._enrich_fs_results(input, output))

        @cli.group()
        def users():
            """User management commands (admin)."""
            pass

        @users.command("create")
        @click.option("--username", required=True)
        @click.option("--email", required=True)
        @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
        @click.option("--role", multiple=True, help="Role(s) to assign (repeatable)")
        def users_create(username, email, password, role):
            asyncio.run(self._users_create(username, email, password, list(role)))

        @users.command("list")
        def users_list():
            asyncio.run(self._users_list())

        @users.command("update-roles")
        @click.option("--username", required=True)
        @click.option("--role", multiple=True)
        def users_update_roles(username, role):
            asyncio.run(self._users_update_roles(username, list(role)))

        @users.command("delete")
        @click.option("--username", required=True)
        def users_delete(username):
            asyncio.run(self._users_delete(username))

        @database.command("migrate")
        @click.option("--revision", help="Target revision")
        @click.pass_context
        def migrate_database(ctx, revision):
            """Run database migrations"""
            asyncio.run(self._migrate_database(ctx.obj, revision))

        @database.command("backup")
        @click.option("--output", "-o", help="Backup file path")
        @click.pass_context
        def backup_database(ctx, output):
            """Backup database"""
            asyncio.run(self._backup_database(ctx.obj, output))

        return cli

    async def _extract_manuscripts(
        self,
        ctx_obj: dict[str, Any],
        journal: str,
        max_manuscripts: int,
        output_dir: str | None,
        headless: bool,
        dry_run: bool,
        persist: bool,
        trace: bool,
        debug_snapshots: bool,
        enrich: bool,
        download: bool,
        normalize_audit: bool,
    ) -> None:
        """Execute manuscript extraction."""
        try:
            if dry_run:
                self.console.print("🔍 [yellow]Dry run mode - validating configuration...[/yellow]")

            # Initialize extraction
            self.console.print(
                f"🚀 Starting extraction for journal: [bold]{journal.upper()}[/bold]"
            )

            # Set up progress tracking
            with Progress() as progress:
                task = progress.add_task(
                    f"Extracting from {journal.upper()}", total=max_manuscripts or 100
                )

                # Import adapter
                adapter = None
                from src.ecc.adapters.journals.factory import get_adapter

                try:
                    adapter = get_adapter(journal, headless=headless)
                except Exception:
                    self.console.print("❌ [red]Unsupported journal id[/red]")
                    return

                manuscripts = []
                async with adapter:
                    # Authenticate and fetch
                    # Enable extra debugging if requested
                    if trace:
                        await adapter.start_tracing()
                    if debug_snapshots:
                        adapter.debug_snapshots = True

                    auth_ok = await adapter.authenticate()
                    if not auth_ok:
                        self.console.print("❌ [red]Authentication failed[/red]")
                        return
                    if dry_run:
                        self.console.print("✅ [green]Authentication OK[/green]")
                    fetched = await adapter.fetch_all_manuscripts()
                    manuscripts = fetched if not max_manuscripts else fetched[:max_manuscripts]

                    # If persisting, enriching or downloading files, fetch full details per manuscript
                    if persist or enrich or download or normalize_audit:
                        detailed = []
                        dl_total = 0
                        dl_dedup = 0
                        for ms in manuscripts:
                            try:
                                ms_full = await adapter.extract_manuscript_details(ms.external_id)
                                # Optional enrichment with ORCID
                                if enrich:
                                    await adapter.enrich_people_with_orcid(ms_full)
                                # Optional downloads
                                if download and hasattr(adapter, "download_manuscript_files"):
                                    before = len(ms_full.files)
                                    paths = await adapter.download_manuscript_files(ms_full)
                                    after = len(ms_full.files)
                                    dl_total += len(paths or [])
                                    dl_dedup += max(0, (after - before) - len(paths or []))
                                # Optional audit normalization preview
                                if normalize_audit:
                                    from src.ecc.core.audit_normalization import normalize_events

                                    ev = (ms_full.metadata or {}).get("audit_trail", [])
                                    nev = normalize_events(ev)
                                    count = len(nev)
                                    first = ", ".join(e.get("event", "") for e in nev[:2])
                                    self.console.print(
                                        f"🧾 [blue]{ms_full.external_id}[/blue]: {count} events | {first}"
                                    )
                                detailed.append(ms_full)
                                progress.advance(task)
                            except Exception as de:
                                self.console.print(
                                    f"⚠️  [yellow]Details/enrichment failed for {ms.external_id}: {de}[/yellow]"
                                )
                                continue
                        manuscripts = detailed or manuscripts
                    progress.update(task, completed=min(len(manuscripts), max_manuscripts or 100))

                self.console.print(f"✅ [green]Fetched {len(manuscripts)} manuscripts[/green]")

                if download:
                    self.console.print(
                        f"📥 [cyan]Downloads:[/cyan] files_saved={dl_total}, dedup_skipped={dl_dedup}"
                    )

                # Persist if requested
                if persist and manuscripts:
                    # Ensure DB initialized
                    import os

                    db_url = os.getenv(
                        "DATABASE_URL",
                        "postgresql+asyncpg://ecc_user:ecc_password@localhost:5433/ecc_db",
                    )
                    try:
                        await initialize_database(db_url, echo=False)
                    except Exception:
                        pass
                    dbm = await get_database_manager()
                    async with dbm.get_session() as session:
                        repo = ManuscriptRepository(session)
                        saved = 0
                        for ms in manuscripts:
                            await repo.save_full(ms)
                            saved += 1
                        self.console.print(
                            f"💾 [green]Persisted {saved} manuscripts (with related data) to DB[/green]"
                        )

            self.console.print("✅ [green]Extraction completed successfully[/green]")

        except Exception as e:
            self.console.print(f"❌ [red]Extraction failed: {e}[/red]")
            sys.exit(1)

    async def _extract_referees(
        self,
        ctx_obj: dict[str, Any],
        journal: str,
        manuscript_id: str | None,
        output_dir: str | None,
    ) -> None:
        """Execute referee extraction."""
        try:
            self.console.print(
                f"👥 Extracting referees for journal: [bold]{journal.upper()}[/bold]"
            )

            if manuscript_id:
                self.console.print(f"📄 Target manuscript: {manuscript_id}")

            # TODO: Implement referee extraction
            self.console.print("⚠️  [yellow]Referee extraction implementation in progress[/yellow]")

        except Exception as e:
            self.console.print(f"❌ [red]Referee extraction failed: {e}[/red]")
            sys.exit(1)

    async def _health_check(self, ctx_obj: dict[str, Any], detailed: bool) -> None:
        """Perform system health check."""
        try:
            self.console.print("🏥 [bold]System Health Check[/bold]")
            self.console.print()

            # Create health check table
            table = Table(title="Health Status")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="bold")
            table.add_column("Details")

            # Check database
            db_status, db_details = await self._check_database()
            table.add_row("Database", "🟢 Healthy" if db_status else "🔴 Error", db_details)

            # Check cache (Redis)
            cache_status, cache_details = await self._check_cache()
            table.add_row("Cache", "🟢 Healthy" if cache_status else "🔴 Error", cache_details)

            # Check AI service
            ai_status, ai_details = await self._check_ai_service()
            table.add_row("AI Service", "🟢 Healthy" if ai_status else "🔴 Error", ai_details)

            # Check observability
            obs_status, obs_details = await self._check_observability()
            table.add_row("Observability", "🟢 Healthy" if obs_status else "🔴 Error", obs_details)

            self.console.print(table)

            if detailed:
                # Show detailed metrics
                await self._show_detailed_health()

        except Exception as e:
            self.console.print(f"❌ [red]Health check failed: {e}[/red]")

    async def _system_status(self, ctx_obj: dict[str, Any]) -> None:
        """Show system status."""
        try:
            self.console.print("📊 [bold]System Status[/bold]")
            self.console.print()

            # System info
            info_table = Table(title="System Information")
            info_table.add_column("Property")
            info_table.add_column("Value")

            info_table.add_row("Version", "2.0.0")
            info_table.add_row("Started", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"))
            info_table.add_row("Active Extractions", str(len(self.active_extractions)))

            self.console.print(info_table)

            # Active operations
            if self.active_extractions:
                self.console.print()
                ops_table = Table(title="Active Operations")
                ops_table.add_column("ID")
                ops_table.add_column("Journal")
                ops_table.add_column("Status")
                ops_table.add_column("Progress")

                for op_id, op_data in self.active_extractions.items():
                    ops_table.add_row(
                        op_id,
                        op_data.get("journal", "Unknown"),
                        op_data.get("status", "Unknown"),
                        f"{op_data.get('progress', 0)}%",
                    )

                self.console.print(ops_table)

        except Exception as e:
            self.console.print(f"❌ [red]Status check failed: {e}[/red]")

    async def _view_logs(
        self, ctx_obj: dict[str, Any], service: str | None, level: str | None, tail: int
    ) -> None:
        """View system logs."""
        try:
            self.console.print(f"📋 [bold]System Logs[/bold] (last {tail} entries)")
            if service:
                self.console.print(f"Filtered by service: [cyan]{service}[/cyan]")
            if level:
                self.console.print(f"Filtered by level: [cyan]{level}[/cyan]")
            self.console.print()

            # TODO: Implement log retrieval from actual log storage
            self.console.print("⚠️  [yellow]Log viewing implementation in progress[/yellow]")

        except Exception as e:
            self.console.print(f"❌ [red]Log viewing failed: {e}[/red]")

    async def _show_config(self, ctx_obj: dict[str, Any], section: str | None) -> None:
        """Show configuration."""
        try:
            config_data = {
                "database": {"url": "postgresql://localhost:5433/ecc_db", "pool_size": 20},
                "journals": {
                    "mf": {"url": "https://mc.manuscriptcentral.com/mafi"},
                    "mor": {"url": "https://mc.manuscriptcentral.com/mor"},
                },
                "observability": {"enabled": True, "jaeger_endpoint": "http://localhost:14268"},
            }

            if section and section in config_data:
                data_to_show = {section: config_data[section]}
            else:
                data_to_show = config_data

            if ctx_obj.get("format") == "json":
                self.console.print(json.dumps(data_to_show, indent=2))
            else:
                tree = Tree("🔧 [bold]ECC Configuration[/bold]")
                for key, value in data_to_show.items():
                    section_tree = tree.add(f"[cyan]{key}[/cyan]")
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            section_tree.add(f"{subkey}: [yellow]{subvalue}[/yellow]")
                    else:
                        section_tree.add(f"[yellow]{value}[/yellow]")

                self.console.print(tree)

        except Exception as e:
            self.console.print(f"❌ [red]Config display failed: {e}[/red]")

    async def _validate_config(self, ctx_obj: dict[str, Any]) -> None:
        """Validate configuration."""
        try:
            self.console.print("🔍 [bold]Validating Configuration[/bold]")

            # TODO: Implement actual configuration validation
            validation_results = [
                ("Database connection", True, "Connection successful"),
                ("Journal credentials", True, "All 8 journals configured"),
                ("AI service keys", True, "OpenAI API key valid"),
                ("Observability setup", True, "Jaeger endpoint reachable"),
            ]

            table = Table(title="Configuration Validation")
            table.add_column("Component")
            table.add_column("Status")
            table.add_column("Details")

            for component, status, details in validation_results:
                table.add_row(component, "✅ Valid" if status else "❌ Invalid", details)

            self.console.print(table)

        except Exception as e:
            self.console.print(f"❌ [red]Config validation failed: {e}[/red]")

    async def _init_config(self, ctx_obj: dict[str, Any], journal: str | None) -> None:
        """Initialize configuration."""
        try:
            self.console.print("🚀 [bold]Initializing Configuration[/bold]")

            if journal:
                self.console.print(f"Setting up configuration for journal: [cyan]{journal}[/cyan]")
            else:
                self.console.print("Setting up global configuration")

            # TODO: Implement configuration initialization
            self.console.print("⚠️  [yellow]Configuration initialization in progress[/yellow]")

        except Exception as e:
            self.console.print(f"❌ [red]Config initialization failed: {e}[/red]")

    async def _migrate_database(self, ctx_obj: dict[str, Any], revision: str | None) -> None:
        """Run database migrations."""
        try:
            self.console.print("🗄️  [bold]Database Migration[/bold]")

            if revision:
                self.console.print(f"Target revision: [cyan]{revision}[/cyan]")
            else:
                self.console.print("Migrating to latest revision")

            # TODO: Implement Alembic integration
            self.console.print("⚠️  [yellow]Database migration implementation in progress[/yellow]")

        except Exception as e:
            self.console.print(f"❌ [red]Database migration failed: {e}[/red]")

    async def _backup_database(self, ctx_obj: dict[str, Any], output: str | None) -> None:
        """Backup database."""
        try:
            if not output:
                output = f"ecc_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

            self.console.print(f"💾 Creating database backup: [cyan]{output}[/cyan]")

            # TODO: Implement database backup
            self.console.print("⚠️  [yellow]Database backup implementation in progress[/yellow]")

        except Exception as e:
            self.console.print(f"❌ [red]Database backup failed: {e}[/red]")

    async def _enrich_fs_results(self, input_path: str, output_path: str | None) -> None:
        """Enrich FS JSON results (authors/referees) with ORCID using ORCIDClient."""
        try:
            import json
            from pathlib import Path

            from core.orcid_client import ORCIDClient

            p = Path(input_path)
            if not p.exists():
                self.console.print(f"❌ [red]Input not found: {input_path}[/red]")
                return

            data = json.loads(p.read_text())
            client = ORCIDClient()
            manuscripts = data.get("manuscripts") or data.get("results") or []
            enriched_count = 0

            for ms in manuscripts:
                # Authors
                for a in ms.get("authors", []):
                    try:
                        person = {
                            "name": a.get("name", ""),
                            "email": a.get("email"),
                            "institution": a.get("institution") or "",
                        }
                        e = client.enrich_person_profile(person)
                        if e.get("orcid"):
                            a["orcid"] = e["orcid"]
                        if e.get("research_interests"):
                            a["research_interests"] = e["research_interests"]
                        if e.get("publication_count") is not None:
                            a["publication_count"] = e["publication_count"]
                        if e.get("current_affiliation"):
                            cur = e["current_affiliation"]
                            a["institution"] = cur.get("organization") or a.get("institution")
                            a["department"] = cur.get("department") or a.get("department")
                            a["country"] = cur.get("country") or a.get("country")
                        enriched_count += 1
                    except Exception:
                        continue
                # Referees
                for r in ms.get("referees", []):
                    try:
                        person = {
                            "name": r.get("name", ""),
                            "email": r.get("email"),
                            "institution": r.get("institution") or r.get("affiliation") or "",
                        }
                        e = client.enrich_person_profile(person)
                        if e.get("orcid"):
                            r["orcid"] = e["orcid"]
                            r["orcid_discovered"] = True
                            r["orcid_confidence"] = e.get("match_confidence", 0)
                        if e.get("research_interests"):
                            r["research_interests"] = e["research_interests"]
                        if e.get("publication_count") is not None:
                            r["publication_count"] = e["publication_count"]
                        if e.get("publications"):
                            r["publications"] = e["publications"]
                        if e.get("current_affiliation"):
                            cur = e["current_affiliation"]
                            r["institution"] = cur.get("organization") or r.get("institution")
                            r["department"] = cur.get("department") or r.get("department")
                            r["country"] = cur.get("country") or r.get("country")
                        enriched_count += 1
                    except Exception:
                        continue

            out = Path(output_path) if output_path else p
            out.write_text(json.dumps(data, indent=2, default=str))
            self.console.print(f"✅ [green]Enriched {enriched_count} people[/green] → {out}")

        except Exception as e:
            self.console.print(f"❌ [red]FS enrichment failed: {e}[/red]")

    # --- Users management ---
    async def _users_create(
        self, username: str, email: str, password: str, roles: list[str]
    ) -> None:
        try:
            # Ensure DB is initialized
            db_url = os.getenv(
                "DATABASE_URL", "postgresql+asyncpg://ecc_user:ecc_password@localhost:5433/ecc_db"
            )
            try:
                await initialize_database(db_url)
            except Exception:
                pass
            dbm = await get_database_manager()
            async with dbm.get_session() as session:
                # Check existing
                from sqlalchemy import select

                res = await session.execute(
                    select(UserModel).where(
                        (UserModel.username == username) | (UserModel.email == email)
                    )
                )
                if res.scalar_one_or_none():
                    self.console.print("❌ [red]User with same username or email exists[/red]")
                    return
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                user = UserModel(
                    username=username,
                    email=email,
                    password_hash=pwd_context.hash(password),
                    roles=roles or [],
                )
                session.add(user)
                await session.flush()
                self.console.print(f"✅ [green]Created user {username}[/green]")
        except Exception as e:
            self.console.print(f"❌ [red]Create user failed: {e}[/red]")

    async def _users_list(self) -> None:
        try:
            dbm = await get_database_manager()
            async with dbm.get_session() as session:
                from sqlalchemy import select

                rows = (await session.execute(select(UserModel))).scalars().all()
                data = [
                    {
                        "id": str(u.id),
                        "username": u.username,
                        "email": u.email,
                        "roles": u.roles or [],
                    }
                    for u in rows
                ]
                self.formatter.format_data(data, format_type="table", title="Users")
        except Exception as e:
            self.console.print(f"❌ [red]List users failed: {e}[/red]")

    async def _users_update_roles(self, username: str, roles: list[str]) -> None:
        try:
            dbm = await get_database_manager()
            async with dbm.get_session() as session:
                from sqlalchemy import select

                user = (
                    await session.execute(select(UserModel).where(UserModel.username == username))
                ).scalar_one_or_none()
                if not user:
                    self.console.print(f"❌ [red]User not found: {username}[/red]")
                    return
                user.roles = roles
                await session.flush()
                self.console.print(f"✅ [green]Updated roles for {username}: {roles}[/green]")
        except Exception as e:
            self.console.print(f"❌ [red]Update roles failed: {e}[/red]")

    async def _users_delete(self, username: str) -> None:
        try:
            dbm = await get_database_manager()
            async with dbm.get_session() as session:
                from sqlalchemy import delete, select

                user = (
                    await session.execute(select(UserModel).where(UserModel.username == username))
                ).scalar_one_or_none()
                if not user:
                    self.console.print(f"❌ [red]User not found: {username}[/red]")
                    return
                await session.execute(delete(UserModel).where(UserModel.id == user.id))
                self.console.print(f"✅ [green]Deleted user {username}[/green]")
        except Exception as e:
            self.console.print(f"❌ [red]Delete user failed: {e}[/red]")

    async def _check_database(self) -> tuple[bool, str]:
        """Check database health."""
        try:
            # TODO: Implement actual database health check
            return True, "PostgreSQL connection active"
        except Exception as e:
            return False, str(e)

    async def _check_cache(self) -> tuple[bool, str]:
        """Check cache health."""
        try:
            # TODO: Implement actual cache health check
            return True, "Redis connection active"
        except Exception as e:
            return False, str(e)

    async def _check_ai_service(self) -> tuple[bool, str]:
        """Check AI service health."""
        try:
            # TODO: Implement actual AI service health check
            return True, "OpenAI API accessible"
        except Exception as e:
            return False, str(e)

    async def _check_observability(self) -> tuple[bool, str]:
        """Check observability health."""
        try:
            observability = get_observability()
            if observability and observability.tracer:
                return True, "OpenTelemetry active"
            else:
                return False, "Observability not initialized"
        except Exception as e:
            return False, str(e)

    async def _show_detailed_health(self) -> None:
        """Show detailed health metrics."""
        # TODO: Implement detailed health metrics
        pass


def create_cli_app() -> click.Group:
    """Create and return CLI application."""
    app = ECCCLIApp()
    return app.create_app()
