#!/usr/bin/env python3
"""
Simple extraction wrapper - automatically loads credentials
Usage: python3 extract.py SICON
       python3 extract.py SIFIN
"""

import os
import sys
import subprocess

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 extract.py [SICON|SIFIN]")
        return 1
    
    journal = sys.argv[1].upper()
    
    if journal not in ['SICON', 'SIFIN']:
        print("Available journals: SICON, SIFIN")
        return 1
    
    # Run with environment loaded
    cmd = [
        'zsh', '-c', 
        f'source ~/.zshrc && python3 run_unified_extraction.py --journal {journal}'
    ]
    
    return subprocess.run(cmd).returncode

if __name__ == "__main__":
    exit(main())