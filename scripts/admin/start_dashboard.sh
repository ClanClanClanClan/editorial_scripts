#!/bin/bash
source ~/.editorial_scripts/load_all_credentials.sh 2>/dev/null
exec /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
    /Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/scripts/dashboard_server.py
