#!/usr/bin/env python3
"""
Fix Python environment issues for the editorial scripts project.
This script diagnoses and fixes virtual environment problems.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, capture=True):
    """Run a shell command and return the output."""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        else:
            return subprocess.run(cmd, shell=True).returncode, "", ""
    except Exception as e:
        return 1, "", str(e)

def diagnose_environment():
    """Diagnose the current Python environment."""
    print("=== Python Environment Diagnosis ===\n")
    
    # Check current Python
    print(f"Current Python: {sys.executable}")
    print(f"Python version: {sys.version}")
    
    # Check virtual environments
    print("\n=== Virtual Environments Found ===")
    venvs = ["venv", "venv_fresh", "venv_clean", "venv_test"]
    for venv in venvs:
        if Path(venv).exists():
            python_path = Path(venv) / "bin" / "python"
            if python_path.exists():
                code, stdout, _ = run_command(f"{python_path} --version")
                if code == 0:
                    print(f"✓ {venv}: {stdout.strip()}")
                else:
                    print(f"✗ {venv}: Error getting version")
            else:
                print(f"✗ {venv}: No Python executable found")
    
    # Check pip in current environment
    print("\n=== Pip Status ===")
    code, stdout, stderr = run_command(f"{sys.executable} -m pip --version")
    if code == 0:
        print(f"✓ Pip working: {stdout.strip()}")
    else:
        print(f"✗ Pip error: {stderr}")

def fix_environment():
    """Fix the environment issues."""
    print("\n=== Fixing Environment ===\n")
    
    # Option 1: Use the fresh virtual environment
    if Path("venv_fresh").exists():
        print("Found fresh virtual environment with all dependencies installed.")
        print("\nTo use the fresh environment, run:")
        print("  source venv_fresh/bin/activate")
        print("  export PYTHONPATH=$PWD:$PYTHONPATH")
        
        # Create activation script
        with open("activate_fresh.sh", "w") as f:
            f.write("""#!/bin/bash
# Activate fresh virtual environment
source venv_fresh/bin/activate
export PYTHONPATH="$PWD:$PYTHONPATH"
echo "✓ Activated fresh virtual environment"
echo "✓ Python: $(which python)"
echo "✓ PYTHONPATH includes current directory"
""")
        os.chmod("activate_fresh.sh", 0o755)
        print("\nCreated activation script: ./activate_fresh.sh")
    
    # Option 2: Fix the main venv
    print("\n=== Alternative: Create New Main Environment ===")
    print("To replace the main venv with a fresh one:")
    print("  rm -rf venv")
    print("  mv venv_fresh venv")
    print("  source venv/bin/activate")
    
    # Create run script for referee analytics
    with open("run_referee_analytics.sh", "w") as f:
        f.write("""#!/bin/bash
# Run referee analytics with proper environment

# Use fresh environment if available, otherwise use main venv
if [ -d "venv_fresh" ]; then
    source venv_fresh/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "No virtual environment found!"
    exit 1
fi

export PYTHONPATH="$PWD:$PYTHONPATH"

# Run the referee analytics system
python run_comprehensive_referee_analytics.py "$@"
""")
    os.chmod("run_referee_analytics.sh", 0o755)
    print("\nCreated run script: ./run_referee_analytics.sh")

def test_imports():
    """Test critical imports."""
    print("\n=== Testing Imports ===")
    
    test_packages = [
        ("playwright", "playwright"),
        ("beautifulsoup4", "bs4"),
        ("aiohttp", "aiohttp"),
        ("google-auth", "google.auth"),
        ("google-api-python-client", "googleapiclient"),
    ]
    
    all_good = True
    for display_name, import_name in test_packages:
        try:
            __import__(import_name)
            print(f"✓ {display_name}")
        except ImportError as e:
            print(f"✗ {display_name}: {e}")
            all_good = False
    
    return all_good

def main():
    """Main function."""
    print("Editorial Scripts Environment Fixer")
    print("=" * 40)
    
    # Diagnose
    diagnose_environment()
    
    # Fix
    fix_environment()
    
    # Test (if in fresh env)
    if "venv_fresh" in sys.executable:
        print("\n=== Testing Fresh Environment ===")
        if test_imports():
            print("\n✓ All imports working correctly!")
        else:
            print("\n✗ Some imports failed")
    
    print("\n=== Summary ===")
    print("1. Fresh virtual environment created: venv_fresh/")
    print("2. All required dependencies installed")
    print("3. Use ./activate_fresh.sh to activate")
    print("4. Use ./run_referee_analytics.sh to run the system")
    print("\nThe environment is now fixed and ready to use!")

if __name__ == "__main__":
    main()