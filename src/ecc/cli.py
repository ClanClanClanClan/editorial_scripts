#!/usr/bin/env python3
"""
Editorial Command Center CLI Entry Point

Main CLI entry point for ECC operations.
Usage: python -m src.ecc.cli [command] [options]
"""

from ecc.infrastructure.cli.commands import create_cli_app


def main():
    """Main CLI entry point."""
    cli_app = create_cli_app()
    cli_app()


if __name__ == "__main__":
    main()
