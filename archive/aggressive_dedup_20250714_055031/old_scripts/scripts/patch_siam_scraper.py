#!/usr/bin/env python3
"""Patch SIAM scraper to fix StealthConfig issue"""

import os

# Read the siam_scraper.py file
siam_scraper_path = "src/infrastructure/scrapers/siam_scraper.py"

with open(siam_scraper_path, 'r') as f:
    content = f.read()

# Find and fix the StealthConfig instantiation
# The issue might be that StealthConfig is being called incorrectly
# Let's check if there's a problem with the import or usage

print("Checking StealthConfig usage in siam_scraper.py...")

# Check imports
if "from src.infrastructure.scrapers.stealth_manager import StealthManager, StealthConfig" in content:
    print("✓ Import looks correct")
else:
    print("✗ Import issue found")

# Check usage
stealth_config_line = None
lines = content.split('\n')
for i, line in enumerate(lines):
    if "StealthConfig(" in line:
        print(f"Found StealthConfig usage at line {i+1}: {line.strip()}")
        stealth_config_line = i

# The issue might be with how the stealth_config is being passed
# Let's create a simpler initialization
if stealth_config_line is not None:
    print("\nCreating a simplified StealthManager initialization...")
    
    # Create a backup
    backup_path = siam_scraper_path + ".backup"
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"Backup created: {backup_path}")
    
    # Replace the StealthConfig initialization with a simpler approach
    new_lines = []
    skip_lines = 0
    
    for i, line in enumerate(lines):
        if skip_lines > 0:
            skip_lines -= 1
            continue
            
        if i == stealth_config_line:
            # Replace the StealthConfig block with a simpler initialization
            new_lines.append("        # Initialize stealth manager with simplified config")
            new_lines.append("        self.stealth_manager = StealthManager()")
            # Skip the next lines that are part of the StealthConfig block
            j = i + 1
            while j < len(lines) and (lines[j].strip().startswith(")") == False or "self.stealth_manager" not in lines[j]):
                skip_lines += 1
                j += 1
        else:
            new_lines.append(line)
    
    # Write the patched file
    with open(siam_scraper_path, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print("✓ Patched siam_scraper.py to use simplified StealthManager initialization")
else:
    print("✗ Could not find StealthConfig usage to patch")

print("\nDone!")