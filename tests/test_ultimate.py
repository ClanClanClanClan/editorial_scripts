#!/usr/bin/env python3
"""Test if the ultimate system can be imported and run"""

import sys
import os

# Activate venv programmatically
venv_path = os.path.join(os.path.dirname(__file__), 'venv')
activate_this = os.path.join(venv_path, 'bin', 'activate_this.py')

# For newer venvs without activate_this.py
site_packages = os.path.join(venv_path, 'lib', 'python3.12', 'site-packages')
sys.path.insert(0, site_packages)

# Add ultimate to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'editorial_scripts_ultimate'))

try:
    print("Testing imports...")
    from extractors.siam.optimized_sicon_extractor import OptimizedSICONExtractor
    from core.models.optimized_models import OptimizedExtractionResult
    print("✅ Imports successful!")
    
    print("\nTesting help...")
    os.system("cd editorial_scripts_ultimate && ../venv/bin/python main.py --help")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()