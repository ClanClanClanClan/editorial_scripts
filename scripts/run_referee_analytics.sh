#!/bin/bash
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
