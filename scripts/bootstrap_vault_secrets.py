#!/usr/bin/env python3
"""
Vault Bootstrap Script for ECC
==============================

Populates HashiCorp Vault KV v2 with ECC secrets for a given environment and namespace.

Env vars:
  VAULT_ADDR, VAULT_TOKEN
  ECC_SECRETS_BASE_PATH (default: secret/data/ecc)
  ECC_ENV (default: development)
  ECC_SECRET_NAMESPACE (default: default)

Usage:
  python scripts/bootstrap_vault_secrets.py \
    --db-host localhost --db-port 5433 --db-name ecc_db --db-user ecc_user --db-password ecc_password \
    --orcid-client-id XXXX --orcid-client-secret YYYY

Optionally provide Gmail secrets as JSON strings or file paths.
"""

import os
import json
import argparse

try:
    import hvac  # type: ignore
except Exception as e:
    print("hvac library required. Install with: pip install hvac")
    raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-host')
    parser.add_argument('--db-port', default='5433')
    parser.add_argument('--db-name')
    parser.add_argument('--db-user')
    parser.add_argument('--db-password')
    parser.add_argument('--orcid-client-id')
    parser.add_argument('--orcid-client-secret')
    parser.add_argument('--gmail-credentials-json')
    parser.add_argument('--gmail-credentials-file')
    parser.add_argument('--gmail-token-json')
    parser.add_argument('--gmail-token-file')
    args = parser.parse_args()

    addr = os.getenv('VAULT_ADDR')
    token = os.getenv('VAULT_TOKEN')
    base = os.getenv('ECC_SECRETS_BASE_PATH', 'secret/data/ecc').rstrip('/')
    env = os.getenv('ECC_ENV', 'development').lower()
    ns = os.getenv('ECC_SECRET_NAMESPACE', 'default').lower()

    if not addr or not token:
        print('VAULT_ADDR and VAULT_TOKEN are required')
        raise SystemExit(1)

    client = hvac.Client(url=addr, token=token)
    path = f"{base}/{env}/{ns}"
    mount = base.replace('secret/data/', '')

    # Load Gmail JSON from file if given
    creds_json = args.gmail_credentials_json
    if not creds_json and args.gmail_credentials_file and os.path.exists(args.gmail_credentials_file):
        creds_json = open(args.gmail_credentials_file).read()
    token_json = args.gmail_token_json
    if not token_json and args.gmail_token_file and os.path.exists(args.gmail_token_file):
        token_json = open(args.gmail_token_file).read()

    payload = {}
    if args.db_host: payload['DB_HOST'] = args.db_host
    if args.db_port: payload['DB_PORT'] = args.db_port
    if args.db_name: payload['DB_NAME'] = args.db_name
    if args.db_user: payload['DB_USER'] = args.db_user
    if args.db_password: payload['DB_PASSWORD'] = args.db_password
    if args.orcid_client_id: payload['ORCID_CLIENT_ID'] = args.orcid_client_id
    if args.orcid_client_secret: payload['ORCID_CLIENT_SECRET'] = args.orcid_client_secret
    if creds_json: payload['GMAIL_CREDENTIALS_JSON'] = creds_json
    if token_json: payload['GMAIL_TOKEN_JSON'] = token_json

    # KV v2 requires relative path
    rel = path.replace('secret/data/', '')
    client.secrets.kv.v2.create_or_update_secret(path=rel, secret=payload)
    print(f"✅ Wrote secrets to {path}")


if __name__ == '__main__':
    main()

