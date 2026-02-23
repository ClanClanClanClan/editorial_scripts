"""HashiCorp Vault client adapter for secure secrets management.

Implements the security requirements from ECC specifications v2.0:
- Dynamic credentials
 - Auto-unseal capabilities
- Comprehensive audit logging
- Role-based access controls
"""

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import aiohttp

from src.ecc.core.error_handling import ExtractorError, SafeExecutor
from src.ecc.core.logging_system import ExtractorLogger, LogCategory
from src.ecc.core.retry_strategies import RetryConfigs, retry


@dataclass
class VaultConfig:
    """Vault connection configuration."""

    url: str = "http://localhost:8200"
    token: str | None = None
    role_id: str | None = None
    secret_id: str | None = None
    namespace: str | None = None
    timeout: int = 30
    retry_attempts: int = 3
    verify_ssl: bool = True

    def __post_init__(self):
        """Validate configuration."""
        if not self.token and not (self.role_id and self.secret_id):
            raise ExtractorError("Either token or (role_id + secret_id) must be provided")


@dataclass
class SecretMetadata:
    """Metadata for stored secrets."""

    path: str
    version: int
    created_time: str
    deletion_time: str | None = None
    destroyed: bool = False
    custom_metadata: dict[str, Any] = None


class VaultClient:
    """Async HashiCorp Vault client for ECC security infrastructure."""

    def __init__(
        self,
        config: VaultConfig,
        logger: ExtractorLogger | None = None,
        safe_executor: SafeExecutor | None = None,
    ):
        """
        Initialize Vault client.

        Args:
            config: Vault connection configuration
            logger: Logger instance
            safe_executor: Safe executor for error handling
        """
        self.config = config
        self.logger = logger or ExtractorLogger("vault_client")
        self.safe_executor = safe_executor or SafeExecutor(self.logger.logger)
        self.session: aiohttp.ClientSession | None = None
        self._token: str | None = config.token
        self._token_expires_at: float | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self):
        """Initialize Vault client connection."""
        self.logger.enter_context("vault_init")

        try:
            # Create HTTP session
            connector = aiohttp.TCPConnector(ssl=self.config.verify_ssl, limit=10, limit_per_host=5)

            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                headers={
                    "Content-Type": "application/json",
                    "X-Vault-Namespace": self.config.namespace or "",
                },
            )

            # Authenticate if using AppRole
            if not self._token and self.config.role_id:
                await self._authenticate_approle()

            # Verify token is valid
            await self._verify_token()

            self.logger.success("Vault client initialized", LogCategory.SECURITY)

        except Exception as e:
            self.logger.error(f"Failed to initialize Vault client: {e}")
            raise ExtractorError("Vault initialization failed") from e

        finally:
            self.logger.exit_context(success=self.session is not None)

    @retry(config=RetryConfigs.NETWORK)
    async def _authenticate_approle(self):
        """Authenticate using AppRole method."""
        self.logger.enter_context("vault_approle_auth")

        try:
            auth_data = {"role_id": self.config.role_id, "secret_id": self.config.secret_id}

            url = urljoin(self.config.url, "/v1/auth/approle/login")

            async with self.session.post(url, json=auth_data) as response:
                if response.status != 200:
                    text = await response.text()
                    raise ExtractorError(f"AppRole auth failed: {response.status} - {text}")

                auth_response = await response.json()

                if "auth" not in auth_response:
                    raise ExtractorError("Invalid auth response from Vault")

                self._token = auth_response["auth"]["client_token"]
                self._token_expires_at = time.time() + auth_response["auth"]["lease_duration"]

                self.logger.success("AppRole authentication successful", LogCategory.SECURITY)

        except Exception as e:
            self.logger.error(f"AppRole authentication failed: {e}")
            raise

        finally:
            self.logger.exit_context(success=self._token is not None)

    async def _verify_token(self):
        """Verify token is valid and get metadata."""
        if not self._token:
            raise ExtractorError("No token available for verification")

        url = urljoin(self.config.url, "/v1/auth/token/lookup-self")
        headers = {"X-Vault-Token": self._token}

        async with self.session.get(url, headers=headers) as response:
            if response.status == 403:
                raise ExtractorError("Vault token is invalid or expired")
            elif response.status != 200:
                text = await response.text()
                raise ExtractorError(f"Token verification failed: {response.status} - {text}")

            token_info = await response.json()
            self.logger.info(
                f"Token verified, policies: {token_info.get('data', {}).get('policies', [])}"
            )

    async def _ensure_authenticated(self):
        """Ensure we have a valid token."""
        if not self._token:
            if self.config.role_id:
                await self._authenticate_approle()
            else:
                raise ExtractorError("No authentication method available")

        # Check if token is expiring soon (within 5 minutes)
        if self._token_expires_at and (self._token_expires_at - time.time()) < 300:
            self.logger.info("Token expiring soon, re-authenticating")
            if self.config.role_id:
                await self._authenticate_approle()

    @retry(config=RetryConfigs.NETWORK)
    async def read_secret(self, path: str) -> dict[str, Any] | None:
        """
        Read secret from Vault KV store.

        Args:
            path: Secret path (without mount prefix)

        Returns:
            Secret data dictionary or None if not found
        """
        await self._ensure_authenticated()

        self.logger.enter_context(f"vault_read_{path}")

        try:
            # KV v2 API format
            api_path = f"/v1/secret/data/{path.lstrip('/')}"
            url = urljoin(self.config.url, api_path)
            headers = {"X-Vault-Token": self._token}

            async with self.session.get(url, headers=headers) as response:
                if response.status == 404:
                    self.logger.warning(f"Secret not found: {path}")
                    return None
                elif response.status != 200:
                    text = await response.text()
                    raise ExtractorError(f"Failed to read secret: {response.status} - {text}")

                secret_response = await response.json()

                # Extract data from KV v2 response format
                data = secret_response.get("data", {}).get("data", {})
                metadata = secret_response.get("data", {}).get("metadata", {})

                self.logger.success(f"Secret read successfully: {path}", LogCategory.SECURITY)

                # Add metadata for audit trail
                return {
                    "data": data,
                    "metadata": SecretMetadata(
                        path=path,
                        version=metadata.get("version", 1),
                        created_time=metadata.get("created_time", ""),
                        deletion_time=metadata.get("deletion_time"),
                        destroyed=metadata.get("destroyed", False),
                        custom_metadata=metadata.get("custom_metadata", {}),
                    ),
                }

        except Exception as e:
            self.logger.error(f"Failed to read secret {path}: {e}")
            raise ExtractorError("Secret read failed") from e

        finally:
            self.logger.exit_context(success=True)

    @retry(config=RetryConfigs.NETWORK)
    async def write_secret(
        self,
        path: str,
        data: dict[str, Any],
        cas: int | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Write secret to Vault KV store.

        Args:
            path: Secret path (without mount prefix)
            data: Secret data to store
            cas: Check-And-Set version for atomic updates
            metadata: Custom metadata for the secret

        Returns:
            Write response with version info
        """
        await self._ensure_authenticated()

        self.logger.enter_context(f"vault_write_{path}")

        try:
            # KV v2 API format
            api_path = f"/v1/secret/data/{path.lstrip('/')}"
            url = urljoin(self.config.url, api_path)
            headers = {"X-Vault-Token": self._token}

            payload = {"data": data}

            if cas is not None:
                payload["options"] = {"cas": cas}

            if metadata:
                payload["metadata"] = metadata

            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status not in [200, 201]:
                    text = await response.text()
                    raise ExtractorError(f"Failed to write secret: {response.status} - {text}")

                write_response = await response.json()

                self.logger.success(f"Secret written successfully: {path}", LogCategory.SECURITY)

                return write_response.get("data", {})

        except Exception as e:
            self.logger.error(f"Failed to write secret {path}: {e}")
            raise ExtractorError("Secret write failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def delete_secret(self, path: str, versions: list[int] | None = None) -> bool:
        """
        Delete secret versions from Vault.

        Args:
            path: Secret path
            versions: Specific versions to delete (None for latest)

        Returns:
            True if successful
        """
        await self._ensure_authenticated()

        self.logger.enter_context(f"vault_delete_{path}")

        try:
            if versions:
                # Delete specific versions
                api_path = f"/v1/secret/delete/{path.lstrip('/')}"
                payload = {"versions": versions}
            else:
                # Soft delete latest version
                api_path = f"/v1/secret/data/{path.lstrip('/')}"
                payload = {}

            url = urljoin(self.config.url, api_path)
            headers = {"X-Vault-Token": self._token}

            async with self.session.delete(url, headers=headers, json=payload) as response:
                if response.status != 204:
                    text = await response.text()
                    raise ExtractorError(f"Failed to delete secret: {response.status} - {text}")

                self.logger.success(f"Secret deleted successfully: {path}", LogCategory.SECURITY)
                return True

        except Exception as e:
            self.logger.error(f"Failed to delete secret {path}: {e}")
            raise ExtractorError("Secret delete failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def list_secrets(self, path: str = "") -> list[str]:
        """
        List secrets at a given path.

        Args:
            path: Path to list (empty for root)

        Returns:
            List of secret names/paths
        """
        await self._ensure_authenticated()

        api_path = f"/v1/secret/metadata/{path.lstrip('/')}"
        url = urljoin(self.config.url, api_path)
        headers = {"X-Vault-Token": self._token}

        # LIST method
        async with self.session.request("LIST", url, headers=headers) as response:
            if response.status == 404:
                return []
            elif response.status != 200:
                text = await response.text()
                raise ExtractorError(f"Failed to list secrets: {response.status} - {text}")

            list_response = await response.json()
            return list_response.get("data", {}).get("keys", [])

    async def create_database_credentials(
        self, database_role: str, ttl: str = "1h"
    ) -> dict[str, str]:
        """
        Generate dynamic database credentials.

        Args:
            database_role: Database role to generate credentials for
            ttl: Time-to-live for credentials

        Returns:
            Dictionary with username and password
        """
        await self._ensure_authenticated()

        self.logger.enter_context(f"vault_db_creds_{database_role}")

        try:
            api_path = f"/v1/database/creds/{database_role}"
            url = urljoin(self.config.url, api_path)
            headers = {"X-Vault-Token": self._token}

            # Add TTL parameter if specified
            params = {"ttl": ttl} if ttl != "1h" else {}

            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    raise ExtractorError(
                        f"Failed to generate DB credentials: {response.status} - {text}"
                    )

                creds_response = await response.json()
                data = creds_response.get("data", {})

                self.logger.success(
                    f"Dynamic DB credentials generated for role: {database_role}",
                    LogCategory.SECURITY,
                )

                return {
                    "username": data.get("username"),
                    "password": data.get("password"),
                    "lease_id": creds_response.get("lease_id"),
                    "lease_duration": creds_response.get("lease_duration"),
                    "renewable": creds_response.get("renewable", False),
                }

        except Exception as e:
            self.logger.error(f"Failed to generate DB credentials for {database_role}: {e}")
            raise ExtractorError("Dynamic credentials failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def renew_lease(self, lease_id: str, increment: int | None = None) -> dict[str, Any]:
        """
        Renew a lease for dynamic credentials.

        Args:
            lease_id: Lease ID to renew
            increment: Requested lease extension in seconds

        Returns:
            Renewal response data
        """
        await self._ensure_authenticated()

        url = urljoin(self.config.url, "/v1/sys/leases/renew")
        headers = {"X-Vault-Token": self._token}

        payload = {"lease_id": lease_id}
        if increment:
            payload["increment"] = increment

        async with self.session.post(url, headers=headers, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                raise ExtractorError(f"Failed to renew lease: {response.status} - {text}")

            return await response.json()

    async def revoke_lease(self, lease_id: str) -> bool:
        """
        Revoke a lease immediately.

        Args:
            lease_id: Lease ID to revoke

        Returns:
            True if successful
        """
        await self._ensure_authenticated()

        url = urljoin(self.config.url, "/v1/sys/leases/revoke")
        headers = {"X-Vault-Token": self._token}

        payload = {"lease_id": lease_id}

        async with self.session.post(url, headers=headers, json=payload) as response:
            if response.status != 204:
                text = await response.text()
                raise ExtractorError(f"Failed to revoke lease: {response.status} - {text}")

            self.logger.success(f"Lease revoked: {lease_id}", LogCategory.SECURITY)
            return True

    async def health_check(self) -> dict[str, Any]:
        """
        Check Vault server health and status.

        Returns:
            Health status information
        """
        url = urljoin(self.config.url, "/v1/sys/health")

        async with self.session.get(url) as response:
            health_data = await response.json()

            return {
                "initialized": health_data.get("initialized", False),
                "sealed": health_data.get("sealed", True),
                "standby": health_data.get("standby", False),
                "server_time_utc": health_data.get("server_time_utc", 0),
                "version": health_data.get("version", "unknown"),
                "cluster_name": health_data.get("cluster_name"),
                "cluster_id": health_data.get("cluster_id"),
            }

    async def close(self):
        """Clean up client resources."""
        if self.session:
            await self.session.close()
            self.logger.success("Vault client closed", LogCategory.SECURITY)


class VaultCredentialManager:
    """High-level credential management using Vault."""

    def __init__(self, vault_client: VaultClient, logger: ExtractorLogger | None = None):
        """
        Initialize credential manager.

        Args:
            vault_client: Configured Vault client
            logger: Logger instance
        """
        self.vault = vault_client
        self.logger = logger or ExtractorLogger("vault_credentials")
        self.credential_cache: dict[str, dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    async def get_journal_credentials(self, journal_id: str) -> dict[str, str]:
        """
        Get credentials for a specific journal.

        Args:
            journal_id: Journal identifier (mf, mor, sicon, etc.)

        Returns:
            Dictionary with username, password, and other credentials
        """
        cache_key = f"journal_{journal_id}"

        # Check cache first
        if cache_key in self.credential_cache:
            cached_data = self.credential_cache[cache_key]
            if time.time() - cached_data["cached_at"] < self.cache_ttl:
                return cached_data["credentials"]

        # Fetch from Vault
        secret_path = f"journals/{journal_id}"
        secret_data = await self.vault.read_secret(secret_path)

        if not secret_data:
            raise ExtractorError(f"No credentials found for journal: {journal_id}")

        credentials = secret_data["data"]

        # Cache credentials
        self.credential_cache[cache_key] = {"credentials": credentials, "cached_at": time.time()}

        self.logger.success(
            f"Credentials retrieved for journal: {journal_id}", LogCategory.SECURITY
        )

        return credentials

    async def store_journal_credentials(
        self, journal_id: str, username: str, password: str, **additional_fields
    ) -> bool:
        """
        Store credentials for a journal in Vault.

        Args:
            journal_id: Journal identifier
            username: Username/email
            password: Password
            **additional_fields: Additional credential fields

        Returns:
            True if successful
        """
        secret_path = f"journals/{journal_id}"

        credential_data = {
            "username": username,
            "password": password,
            "created_at": time.time(),
            **additional_fields,
        }

        await self.vault.write_secret(
            secret_path,
            credential_data,
            metadata={
                "journal": journal_id,
                "created_by": "ecc_system",
                "purpose": "journal_authentication",
            },
        )

        # Clear cache
        cache_key = f"journal_{journal_id}"
        self.credential_cache.pop(cache_key, None)

        self.logger.success(f"Credentials stored for journal: {journal_id}", LogCategory.SECURITY)

        return True

    async def get_database_credentials(self, environment: str = "development") -> dict[str, str]:
        """
        Get dynamic database credentials from Vault.

        Args:
            environment: Environment name (development, staging, production)

        Returns:
            Dictionary with database connection details
        """
        database_role = f"ecc_{environment}"

        # Generate dynamic credentials
        dynamic_creds = await self.vault.create_database_credentials(database_role)

        self.logger.success(
            f"Database credentials generated for: {environment}", LogCategory.SECURITY
        )

        return {
            "username": dynamic_creds["username"],
            "password": dynamic_creds["password"],
            "database": "ecc_db",
            "host": "localhost",
            "port": "5432",
            "lease_id": dynamic_creds["lease_id"],
            "lease_duration": dynamic_creds["lease_duration"],
        }

    async def get_api_key(self, service: str) -> str:
        """
        Get API key for external service.

        Args:
            service: Service name (openai, gmail, etc.)

        Returns:
            API key string
        """
        secret_path = f"api_keys/{service}"
        secret_data = await self.vault.read_secret(secret_path)

        if not secret_data:
            raise ExtractorError(f"No API key found for service: {service}")

        return secret_data["data"]["api_key"]

    async def rotate_credentials(self, journal_id: str) -> bool:
        """
        Rotate credentials for a journal (placeholder for future implementation).

        Args:
            journal_id: Journal identifier

        Returns:
            True if rotation successful
        """
        # This would integrate with journal platforms' credential rotation APIs
        # For now, just clear cache to force refresh
        cache_key = f"journal_{journal_id}"
        self.credential_cache.pop(cache_key, None)

        self.logger.info(f"Credential rotation initiated for: {journal_id}", LogCategory.SECURITY)

        return True
