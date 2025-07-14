#!/usr/bin/env python3
"""
Migration script to move credentials from .env to 1Password
"""
import os
import sys
import subprocess
from dotenv import load_dotenv
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

console = Console()

# Load existing .env file
load_dotenv()

# Credential mappings
CREDENTIAL_MAPPINGS = {
    'SICON': {
        'username': 'SICON_USERNAME',
        'password': 'SICON_PASSWORD'
    },
    'SIFIN': {
        'username': 'SIFIN_USERNAME', 
        'password': 'SIFIN_PASSWORD'
    },
    'MOR': {
        'email': 'MOR_USER',
        'password': 'MOR_PASSWORD'
    },
    'MF': {
        'email': 'MF_USER',
        'password': 'MF_PASS'
    },
    'NACO': {
        'username': 'NACO_USER',
        'password': 'NACO_PASS'
    },
    'JOTA': {
        'username': 'JOTA_USER',
        'password': 'JOTA_PASS'
    },
    'MAFE': {
        'username': 'MAFE_USER',
        'password': 'MAFE_PASS'
    },
    'ORCID': {
        'email': 'ORCID_EMAIL',
        'password': 'ORCID_PASSWORD'
    },
    'GMAIL': {
        'username': 'GMAIL_USER',
        'app_password': 'GMAIL_APP_PASSWORD'
    },
    'RECIPIENT': {
        'email': 'RECIPIENT_EMAIL'
    }
}

def check_1password_cli():
    """Check if 1Password CLI is installed and authenticated"""
    try:
        result = subprocess.run(['op', '--version'], capture_output=True, text=True)
        console.print(f"✓ 1Password CLI version: {result.stdout.strip()}", style="green")
        
        # Check if signed in
        result = subprocess.run(['op', 'vault', 'list'], capture_output=True)
        if result.returncode != 0:
            console.print("✗ Not signed in to 1Password", style="red")
            console.print("\nPlease run: [bold]op signin[/bold]")
            return False
        
        console.print("✓ Signed in to 1Password", style="green")
        return True
        
    except FileNotFoundError:
        console.print("✗ 1Password CLI not found", style="red")
        console.print("\nPlease install from: https://1password.com/downloads/command-line/")
        return False

def create_1password_item(service: str, fields: dict, vault: str = "Editorial Scripts"):
    """Create a new 1Password item"""
    # Build field arguments
    field_args = []
    for field_name, env_var in fields.items():
        value = os.getenv(env_var)
        if value:
            field_args.extend([f'{field_name}={value}'])
    
    if not field_args:
        return False
    
    # Create the item
    cmd = [
        'op', 'item', 'create',
        '--category=login',
        f'--title={service}',
        f'--vault={vault}'
    ]
    
    # Add fields
    for field_arg in field_args:
        cmd.extend(['--fields', field_arg])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"✓ Created {service} in 1Password", style="green")
            return True
        else:
            console.print(f"✗ Failed to create {service}: {result.stderr}", style="red")
            return False
    except Exception as e:
        console.print(f"✗ Error creating {service}: {e}", style="red")
        return False

@click.command()
@click.option('--vault', default='Editorial Scripts', help='1Password vault name')
@click.option('--dry-run', is_flag=True, help='Show what would be migrated without doing it')
def migrate(vault, dry_run):
    """Migrate credentials from .env to 1Password"""
    
    console.print("\n[bold]Editorial Scripts Credential Migration[/bold]\n")
    
    # Check 1Password CLI
    if not dry_run and not check_1password_cli():
        sys.exit(1)
    
    # Show current credentials
    table = Table(title="Credentials to Migrate")
    table.add_column("Service", style="cyan")
    table.add_column("Fields", style="magenta")
    table.add_column("Status", style="green")
    
    for service, fields in CREDENTIAL_MAPPINGS.items():
        field_list = []
        has_values = False
        
        for field_name, env_var in fields.items():
            value = os.getenv(env_var)
            if value:
                field_list.append(f"{field_name} ✓")
                has_values = True
            else:
                field_list.append(f"{field_name} ✗")
        
        status = "Ready" if has_values else "No data"
        table.add_row(service, ", ".join(field_list), status)
    
    console.print(table)
    
    if dry_run:
        console.print("\n[yellow]Dry run mode - no changes will be made[/yellow]")
        return
    
    # Confirm migration
    if not Confirm.ask("\nProceed with migration?"):
        console.print("Migration cancelled")
        return
    
    # Perform migration
    console.print("\n[bold]Migrating credentials...[/bold]\n")
    
    success_count = 0
    fail_count = 0
    
    for service, fields in CREDENTIAL_MAPPINGS.items():
        # Check if we have any values for this service
        has_values = any(os.getenv(env_var) for env_var in fields.values())
        
        if has_values:
            if create_1password_item(service, fields, vault):
                success_count += 1
            else:
                fail_count += 1
        else:
            console.print(f"⚪ Skipping {service} (no credentials found)", style="dim")
    
    # Summary
    console.print(f"\n[bold]Migration complete![/bold]")
    console.print(f"✓ Migrated: {success_count} services", style="green")
    if fail_count > 0:
        console.print(f"✗ Failed: {fail_count} services", style="red")
    
    # Next steps
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Verify credentials in 1Password")
    console.print("2. Test the application with: python main.py --dry-run")
    console.print("3. Once verified, rename .env to .env.backup")
    console.print("4. Update any deployment scripts to remove .env dependencies")

if __name__ == '__main__':
    migrate()