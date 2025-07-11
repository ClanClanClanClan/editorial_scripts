#!/usr/bin/env python3
"""Convert pickle token to JSON format"""

import pickle
import json
from google.oauth2.credentials import Credentials

# Read pickle token
with open('token.json', 'rb') as f:
    creds = pickle.load(f)

# Convert to JSON format
token_data = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "scopes": creds.scopes,
    "expiry": creds.expiry.isoformat() if creds.expiry else None
}

# Write JSON token
with open('token.json', 'w') as f:
    json.dump(token_data, f, indent=2)

print("✅ Token converted to JSON format")