#!/bin/bash
# Activate fresh virtual environment
source venv_fresh/bin/activate
export PYTHONPATH="$PWD:$PYTHONPATH"
echo "✓ Activated fresh virtual environment"
echo "✓ Python: $(which python)"
echo "✓ PYTHONPATH includes current directory"
