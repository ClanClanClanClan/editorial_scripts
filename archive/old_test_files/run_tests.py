#!/usr/bin/env python3
"""
Test runner for editorial scripts
"""
import sys
import os
import subprocess
import argparse
from pathlib import Path

def run_tests(args):
    """Run tests with pytest"""
    # Ensure we're in the project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Build pytest command
    cmd = ["pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend([
            "--cov=core",
            "--cov=journals",
            "--cov=database",
            "--cov-report=html",
            "--cov-report=term"
        ])
    
    # Add specific test path if provided
    if args.test_path:
        cmd.append(args.test_path)
    else:
        cmd.append("tests/")
    
    # Add markers if specified
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    
    # Add other pytest options
    if args.stop_on_failure:
        cmd.append("-x")
    
    if args.pdb:
        cmd.append("--pdb")
    
    if args.workers:
        cmd.extend(["-n", str(args.workers)])
    
    # Run tests
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode

def main():
    parser = argparse.ArgumentParser(description="Run editorial scripts tests")
    
    parser.add_argument(
        "test_path",
        nargs="?",
        help="Specific test file or directory to run"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests"
    )
    
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run only integration tests"
    )
    
    parser.add_argument(
        "-x", "--stop-on-failure",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--pdb",
        action="store_true",
        help="Drop into debugger on failures"
    )
    
    parser.add_argument(
        "-n", "--workers",
        type=int,
        help="Number of parallel workers"
    )
    
    args = parser.parse_args()
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("pytest is not installed. Please run: pip install pytest pytest-cov pytest-xdist")
        sys.exit(1)
    
    # Run tests
    exit_code = run_tests(args)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()