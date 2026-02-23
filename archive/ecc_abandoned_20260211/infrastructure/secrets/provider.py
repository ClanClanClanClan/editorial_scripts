"""Secrets provider abstraction for ECC.

Supports multiple backends with graceful fallback:
- Environment variables (always available)
- macOS Keychain or system keyring (via `keyring`, optional)
- (Future) HashiCorp Vault
"""

from __future__ import annotations

import os


class SecretProvider:
    def get(self, name: str) -> str | None:
        raise NotImplementedError


class EnvSecretProvider(SecretProvider):
    def get(self, name: str) -> str | None:
        return os.getenv(name)


class KeychainSecretProvider(SecretProvider):
    def __init_subclass__(cls):
        return super().__init_subclass__()

    def get(self, name: str) -> str | None:
        try:
            import keyring  # type: ignore
        except Exception:
            return None
        # Use a fixed service name for ECC
        service = os.getenv("ECC_KEYCHAIN_SERVICE", "ecc")
        try:
            return keyring.get_password(service, name)
        except Exception:
            return None


def get_secret(name: str) -> str | None:
    """Fetch secret from providers in order of precedence."""
    for provider in (EnvSecretProvider(), KeychainSecretProvider()):
        val = provider.get(name)
        if val:
            return val
    return None


class VaultSecretProvider(SecretProvider):
    """Optional HashiCorp Vault provider. Uses hvac if available.

    Configure:
      VAULT_ADDR, VAULT_TOKEN, ECC_SECRETS_PATH (default: secret/data/ecc)
    Keys are read from the data dict of KV v2.
    """

    def __init__(self):
        self.addr = os.getenv("VAULT_ADDR")
        self.token = os.getenv("VAULT_TOKEN")
        # Base path and contextual paths by env/namespace
        self.base_path = os.getenv("ECC_SECRETS_BASE_PATH", "secret/data/ecc").rstrip("/")
        self.env = os.getenv("ECC_ENV", "development").lower()
        self.namespace = os.getenv("ECC_SECRET_NAMESPACE", "default").lower()
        self._client = None
        if self.addr and self.token:
            try:
                import hvac  # type: ignore

                self._client = hvac.Client(url=self.addr, token=self.token)
            except Exception:
                self._client = None

    def get(self, name: str) -> str | None:
        if not self._client:
            return None
        try:
            # Try multiple contextual paths (KV v2):
            #  - base
            #  - base/{env}
            #  - base/{env}/{namespace}
            def read_path(p: str) -> str | None:
                # v2 expects path without leading 'secret/data/' when using kv.v2 helper
                rel = p.replace("secret/data/", "")
                res = self._client.secrets.kv.v2.read_secret_version(path=rel)
                data = res.get("data", {}).get("data", {})
                return data.get(name)

            for p in (
                self.base_path,
                f"{self.base_path}/{self.env}",
                f"{self.base_path}/{self.env}/{self.namespace}",
            ):
                val = read_path(p)
                if val:
                    return val
            return None
        except Exception:
            return None


def get_secret_with_vault(name: str) -> str | None:
    for provider in (EnvSecretProvider(), KeychainSecretProvider(), VaultSecretProvider()):
        val = provider.get(name)
        if val:
            return val
    return None
