"""Encryption services for ECC security infrastructure.

Implements the encryption requirements from ECC specifications v2.0:
- AES-256-GCM for data at rest
- TLS 1.3 for data in transit
- Key rotation and management
- Secure field-level encryption
"""

import base64
import hashlib
import secrets
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiofiles
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from src.ecc.adapters.security.vault_client import VaultClient
from src.ecc.core.error_handling import ExtractorError
from src.ecc.core.logging_system import ExtractorLogger, LogCategory


@dataclass
class EncryptionKey:
    """Encryption key metadata."""

    key_id: str
    algorithm: str
    key_size: int
    created_at: datetime
    expires_at: datetime | None = None
    is_active: bool = True
    rotation_count: int = 0
    purpose: str = "general"  # general, database, file, field
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def is_expired(self) -> bool:
        """Check if key is expired."""
        return self.expires_at is not None and datetime.utcnow() > self.expires_at

    def needs_rotation(self, rotation_days: int = 90) -> bool:
        """Check if key needs rotation."""
        if self.expires_at:
            return datetime.utcnow() > (
                self.expires_at - timedelta(days=7)
            )  # 7 days before expiration

        # Default rotation based on age
        age = datetime.utcnow() - self.created_at
        return age.days >= rotation_days


class FieldEncryptor:
    """Field-level encryption for sensitive data."""

    def __init__(self, encryption_key: bytes, logger: ExtractorLogger | None = None):
        """
        Initialize field encryptor.

        Args:
            encryption_key: 32-byte AES-256 key
            logger: Logger instance
        """
        self.key = encryption_key
        self.logger = logger or ExtractorLogger("field_encryptor")

        if len(encryption_key) != 32:
            raise ExtractorError("Encryption key must be exactly 32 bytes for AES-256")

    def encrypt_field(self, plaintext: str, associated_data: str | None = None) -> str:
        """
        Encrypt a field value using AES-256-GCM.

        Args:
            plaintext: Text to encrypt
            associated_data: Additional authenticated data

        Returns:
            Base64-encoded encrypted data with metadata
        """
        try:
            # Generate random IV (96 bits for GCM)
            iv = secrets.token_bytes(12)

            # Create cipher
            cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv), backend=default_backend())
            encryptor = cipher.encryptor()

            # Add associated data if provided
            if associated_data:
                encryptor.authenticate_additional_data(associated_data.encode("utf-8"))

            # Encrypt
            ciphertext = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()

            # Combine IV + ciphertext + tag
            encrypted_data = iv + ciphertext + encryptor.tag

            # Encode as base64 for storage
            return base64.b64encode(encrypted_data).decode("utf-8")

        except Exception as e:
            self.logger.error(f"Field encryption failed: {e}")
            raise ExtractorError("Encryption failed") from e

    def decrypt_field(self, encrypted_data: str, associated_data: str | None = None) -> str:
        """
        Decrypt a field value using AES-256-GCM.

        Args:
            encrypted_data: Base64-encoded encrypted data
            associated_data: Additional authenticated data (must match encryption)

        Returns:
            Decrypted plaintext
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode("utf-8"))

            # Extract components
            iv = encrypted_bytes[:12]
            tag = encrypted_bytes[-16:]
            ciphertext = encrypted_bytes[12:-16]

            # Create cipher
            cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()

            # Add associated data if provided
            if associated_data:
                decryptor.authenticate_additional_data(associated_data.encode("utf-8"))

            # Decrypt
            plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize()

            return plaintext_bytes.decode("utf-8")

        except Exception as e:
            self.logger.error(f"Field decryption failed: {e}")
            raise ExtractorError("Decryption failed") from e


class FileEncryptor:
    """File-level encryption for data at rest."""

    def __init__(self, encryption_key: bytes, logger: ExtractorLogger | None = None):
        """
        Initialize file encryptor.

        Args:
            encryption_key: 32-byte AES-256 key
            logger: Logger instance
        """
        self.key = encryption_key
        self.logger = logger or ExtractorLogger("file_encryptor")
        self.chunk_size = 64 * 1024  # 64KB chunks

    async def encrypt_file(
        self, input_path: Path, output_path: Path, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Encrypt a file using AES-256-GCM.

        Args:
            input_path: Path to plaintext file
            output_path: Path for encrypted file
            metadata: Optional metadata to include

        Returns:
            Encryption metadata
        """
        self.logger.enter_context(f"encrypt_file_{input_path.name}")

        try:
            # Generate random IV
            iv = secrets.token_bytes(12)

            # Create cipher
            cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv), backend=default_backend())
            encryptor = cipher.encryptor()

            # Calculate file hash for integrity
            file_hash = hashlib.sha256()
            encrypted_size = 0

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Encrypt file in chunks
            async with aiofiles.open(input_path, "rb") as infile:
                async with aiofiles.open(output_path, "wb") as outfile:
                    # Write header with IV
                    await outfile.write(iv)

                    # Encrypt data in chunks
                    while True:
                        chunk = await infile.read(self.chunk_size)
                        if not chunk:
                            break

                        file_hash.update(chunk)
                        encrypted_chunk = encryptor.update(chunk)
                        await outfile.write(encrypted_chunk)
                        encrypted_size += len(encrypted_chunk)

                    # Finalize and write tag
                    final_chunk = encryptor.finalize()
                    await outfile.write(final_chunk)
                    await outfile.write(encryptor.tag)
                    encrypted_size += len(final_chunk) + 16  # tag size

            # Create metadata
            encryption_metadata = {
                "algorithm": "AES-256-GCM",
                "iv_size": 12,
                "tag_size": 16,
                "original_size": input_path.stat().st_size,
                "encrypted_size": encrypted_size,
                "original_hash": file_hash.hexdigest(),
                "encrypted_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }

            self.logger.success(
                f"File encrypted: {input_path} -> {output_path}", LogCategory.SECURITY
            )

            return encryption_metadata

        except Exception as e:
            self.logger.error(f"File encryption failed: {e}")
            raise ExtractorError("File encryption failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def decrypt_file(
        self, input_path: Path, output_path: Path, verify_hash: str | None = None
    ) -> dict[str, Any]:
        """
        Decrypt a file using AES-256-GCM.

        Args:
            input_path: Path to encrypted file
            output_path: Path for decrypted file
            verify_hash: Optional hash to verify integrity

        Returns:
            Decryption metadata
        """
        self.logger.enter_context(f"decrypt_file_{input_path.name}")

        try:
            # Calculate decrypted hash for integrity
            file_hash = hashlib.sha256()
            decrypted_size = 0

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(input_path, "rb") as infile:
                # Read IV from header
                iv = await infile.read(12)

                # Read and separate tag from end
                encrypted_data = await infile.read()
                tag = encrypted_data[-16:]
                ciphertext = encrypted_data[:-16]

                # Create cipher
                cipher = Cipher(
                    algorithms.AES(self.key), modes.GCM(iv, tag), backend=default_backend()
                )
                decryptor = cipher.decryptor()

                # Decrypt in chunks
                async with aiofiles.open(output_path, "wb") as outfile:
                    for i in range(0, len(ciphertext), self.chunk_size):
                        chunk = ciphertext[i : i + self.chunk_size]
                        decrypted_chunk = decryptor.update(chunk)

                        file_hash.update(decrypted_chunk)
                        await outfile.write(decrypted_chunk)
                        decrypted_size += len(decrypted_chunk)

                    # Finalize
                    final_chunk = decryptor.finalize()
                    if final_chunk:
                        file_hash.update(final_chunk)
                        await outfile.write(final_chunk)
                        decrypted_size += len(final_chunk)

            # Verify hash if provided
            calculated_hash = file_hash.hexdigest()
            if verify_hash and calculated_hash != verify_hash:
                raise ExtractorError(
                    f"Hash verification failed: expected {verify_hash}, got {calculated_hash}"
                )

            decryption_metadata = {
                "algorithm": "AES-256-GCM",
                "decrypted_size": decrypted_size,
                "decrypted_hash": calculated_hash,
                "hash_verified": verify_hash is not None,
                "decrypted_at": datetime.utcnow().isoformat(),
            }

            self.logger.success(
                f"File decrypted: {input_path} -> {output_path}", LogCategory.SECURITY
            )

            return decryption_metadata

        except Exception as e:
            self.logger.error(f"File decryption failed: {e}")
            raise ExtractorError("File decryption failed") from e

        finally:
            self.logger.exit_context(success=True)


class KeyManager:
    """Encryption key management with rotation support."""

    def __init__(
        self, vault_client: VaultClient | None = None, logger: ExtractorLogger | None = None
    ):
        """
        Initialize key manager.

        Args:
            vault_client: Vault client for secure key storage
            logger: Logger instance
        """
        self.vault = vault_client
        self.logger = logger or ExtractorLogger("key_manager")
        self.keys: dict[str, EncryptionKey] = {}
        self.key_cache: dict[str, bytes] = {}
        self.cache_ttl = 3600  # 1 hour cache TTL
        self.cache_timestamps: dict[str, float] = {}

    def _generate_key_id(self, purpose: str, algorithm: str) -> str:
        """Generate unique key ID."""
        timestamp = int(time.time())
        random_suffix = secrets.token_hex(8)
        return f"{purpose}_{algorithm}_{timestamp}_{random_suffix}"

    async def generate_key(
        self, algorithm: str = "AES-256", purpose: str = "general", expires_in_days: int | None = 90
    ) -> EncryptionKey:
        """
        Generate a new encryption key.

        Args:
            algorithm: Encryption algorithm
            purpose: Key purpose (general, database, file, field)
            expires_in_days: Key expiration in days (None for no expiration)

        Returns:
            Generated encryption key metadata
        """
        self.logger.enter_context(f"generate_key_{algorithm}_{purpose}")

        try:
            # Generate key based on algorithm
            if algorithm == "AES-256":
                key_bytes = secrets.token_bytes(32)  # 256 bits
                key_size = 256
            elif algorithm == "AES-128":
                key_bytes = secrets.token_bytes(16)  # 128 bits
                key_size = 128
            else:
                raise ExtractorError(f"Unsupported algorithm: {algorithm}")

            # Create key metadata
            key_id = self._generate_key_id(purpose, algorithm)
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

            key_metadata = EncryptionKey(
                key_id=key_id,
                algorithm=algorithm,
                key_size=key_size,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                purpose=purpose,
            )

            # Store in Vault if available
            if self.vault:
                await self.vault.write_secret(
                    f"encryption_keys/{key_id}",
                    {
                        "key_bytes": base64.b64encode(key_bytes).decode("utf-8"),
                        "algorithm": algorithm,
                        "key_size": key_size,
                        "purpose": purpose,
                        "created_at": key_metadata.created_at.isoformat(),
                        "expires_at": expires_at.isoformat() if expires_at else None,
                    },
                    metadata={
                        "key_type": "encryption_key",
                        "algorithm": algorithm,
                        "purpose": purpose,
                    },
                )

            # Store in memory
            self.keys[key_id] = key_metadata
            self.key_cache[key_id] = key_bytes
            self.cache_timestamps[key_id] = time.time()

            self.logger.success(
                f"Generated {algorithm} key for {purpose}: {key_id}", LogCategory.SECURITY
            )

            return key_metadata

        except Exception as e:
            self.logger.error(f"Key generation failed: {e}")
            raise ExtractorError("Key generation failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def get_key(self, key_id: str) -> bytes:
        """
        Retrieve encryption key bytes.

        Args:
            key_id: Key identifier

        Returns:
            Key bytes
        """
        # Check cache first
        if key_id in self.key_cache:
            cache_time = self.cache_timestamps.get(key_id, 0)
            if time.time() - cache_time < self.cache_ttl:
                return self.key_cache[key_id]

        # Load from Vault
        if self.vault:
            secret_data = await self.vault.read_secret(f"encryption_keys/{key_id}")
            if secret_data:
                key_bytes = base64.b64decode(secret_data["data"]["key_bytes"])

                # Cache key
                self.key_cache[key_id] = key_bytes
                self.cache_timestamps[key_id] = time.time()

                return key_bytes

        raise ExtractorError(f"Encryption key not found: {key_id}")

    async def get_active_key(
        self, purpose: str, algorithm: str = "AES-256"
    ) -> EncryptionKey | None:
        """
        Get the active key for a specific purpose.

        Args:
            purpose: Key purpose
            algorithm: Encryption algorithm

        Returns:
            Active key metadata or None
        """
        for key_metadata in self.keys.values():
            if (
                key_metadata.purpose == purpose
                and key_metadata.algorithm == algorithm
                and key_metadata.is_active
                and not key_metadata.is_expired()
            ):
                return key_metadata

        # Try to load from Vault
        if self.vault:
            key_paths = await self.vault.list_secrets("encryption_keys/")
            for key_path in key_paths:
                if purpose in key_path and algorithm.replace("-", "_") in key_path:
                    secret_data = await self.vault.read_secret(f"encryption_keys/{key_path}")
                    if secret_data:
                        data = secret_data["data"]
                        if data.get("purpose") == purpose and data.get("algorithm") == algorithm:
                            # Create key metadata
                            key_metadata = EncryptionKey(
                                key_id=key_path,
                                algorithm=data["algorithm"],
                                key_size=data["key_size"],
                                created_at=datetime.fromisoformat(data["created_at"]),
                                expires_at=(
                                    datetime.fromisoformat(data["expires_at"])
                                    if data.get("expires_at")
                                    else None
                                ),
                                purpose=data["purpose"],
                            )

                            if not key_metadata.is_expired():
                                self.keys[key_path] = key_metadata
                                return key_metadata

        return None

    async def rotate_key(self, key_id: str) -> EncryptionKey:
        """
        Rotate an encryption key.

        Args:
            key_id: Key to rotate

        Returns:
            New key metadata
        """
        old_key = self.keys.get(key_id)
        if not old_key:
            raise ExtractorError(f"Key not found for rotation: {key_id}")

        # Deactivate old key
        old_key.is_active = False
        old_key.rotation_count += 1

        # Generate new key with same properties
        new_key = await self.generate_key(
            algorithm=old_key.algorithm,
            purpose=old_key.purpose,
            expires_in_days=90,  # Standard rotation period
        )

        self.logger.success(f"Key rotated: {key_id} -> {new_key.key_id}", LogCategory.SECURITY)

        return new_key

    async def cleanup_expired_keys(self):
        """Remove expired keys from cache and mark as inactive."""
        expired_keys = []

        for key_id, key_metadata in self.keys.items():
            if key_metadata.is_expired():
                expired_keys.append(key_id)
                key_metadata.is_active = False

        # Clear from cache
        for key_id in expired_keys:
            self.key_cache.pop(key_id, None)
            self.cache_timestamps.pop(key_id, None)

        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired keys")

    def create_field_encryptor(self, key_id: str) -> FieldEncryptor:
        """Create field encryptor with specified key."""
        if key_id not in self.key_cache:
            raise ExtractorError(f"Key not loaded: {key_id}")

        return FieldEncryptor(self.key_cache[key_id], self.logger)

    def create_file_encryptor(self, key_id: str) -> FileEncryptor:
        """Create file encryptor with specified key."""
        if key_id not in self.key_cache:
            raise ExtractorError(f"Key not loaded: {key_id}")

        return FileEncryptor(self.key_cache[key_id], self.logger)


class TLSConfigManager:
    """TLS configuration manager for secure transport."""

    def __init__(self, logger: ExtractorLogger | None = None):
        """Initialize TLS config manager."""
        self.logger = logger or ExtractorLogger("tls_config")

    def create_secure_ssl_context(
        self,
        purpose: ssl.Purpose = ssl.Purpose.SERVER_AUTH,
        cert_file: Path | None = None,
        key_file: Path | None = None,
        ca_file: Path | None = None,
    ) -> ssl.SSLContext:
        """
        Create secure SSL context with TLS 1.3.

        Args:
            purpose: SSL purpose
            cert_file: Certificate file path
            key_file: Private key file path
            ca_file: CA certificate file path

        Returns:
            Configured SSL context
        """
        self.logger.enter_context("create_ssl_context")

        try:
            # Create context with secure defaults
            context = ssl.create_default_context(purpose)

            # Enforce TLS 1.3 (minimum TLS 1.2)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_3

            # Set secure cipher suites
            context.set_ciphers(
                "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
            )

            # Load certificates if provided
            if cert_file and key_file:
                context.load_cert_chain(str(cert_file), str(key_file))
                self.logger.success(f"Loaded certificate: {cert_file}", LogCategory.SECURITY)

            if ca_file:
                context.load_verify_locations(str(ca_file))
                self.logger.success(f"Loaded CA certificates: {ca_file}", LogCategory.SECURITY)

            # Security settings
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED

            # Disable compression to prevent CRIME attacks
            context.options |= ssl.OP_NO_COMPRESSION

            # Disable session resumption to prevent session fixation
            context.options |= ssl.OP_NO_TICKET

            self.logger.success("Secure SSL context created with TLS 1.3", LogCategory.SECURITY)

            return context

        except Exception as e:
            self.logger.error(f"SSL context creation failed: {e}")
            raise ExtractorError("SSL context creation failed") from e

        finally:
            self.logger.exit_context(success=True)

    def validate_certificate(self, cert_file: Path) -> dict[str, Any]:
        """
        Validate SSL certificate.

        Args:
            cert_file: Certificate file path

        Returns:
            Certificate validation results
        """
        try:
            with open(cert_file, "rb") as f:
                cert_data = f.read()

            # Load certificate
            cert = serialization.load_pem_x509_certificate(cert_data, default_backend())

            # Extract information
            subject = cert.subject.rfc4514_string()
            issuer = cert.issuer.rfc4514_string()
            not_before = cert.not_valid_before
            not_after = cert.not_valid_after

            # Check if certificate is valid
            now = datetime.utcnow()
            is_valid = not_before <= now <= not_after
            days_until_expiry = (not_after - now).days

            validation_result = {
                "is_valid": is_valid,
                "subject": subject,
                "issuer": issuer,
                "not_before": not_before.isoformat(),
                "not_after": not_after.isoformat(),
                "days_until_expiry": days_until_expiry,
                "needs_renewal": days_until_expiry < 30,
                "serial_number": str(cert.serial_number),
                "version": cert.version.name,
            }

            self.logger.info(
                f"Certificate validation: {cert_file} - Valid: {is_valid}, Expires in: {days_until_expiry} days"
            )

            return validation_result

        except Exception as e:
            self.logger.error(f"Certificate validation failed: {e}")
            raise ExtractorError("Certificate validation failed") from e


class EncryptionService:
    """High-level encryption service combining all encryption capabilities."""

    def __init__(
        self, vault_client: VaultClient | None = None, logger: ExtractorLogger | None = None
    ):
        """
        Initialize encryption service.

        Args:
            vault_client: Vault client for key management
            logger: Logger instance
        """
        self.key_manager = KeyManager(vault_client, logger)
        self.tls_manager = TLSConfigManager(logger)
        self.logger = logger or ExtractorLogger("encryption_service")

    async def initialize(self):
        """Initialize encryption service."""
        self.logger.enter_context("encryption_service_init")

        try:
            # Ensure we have active keys for common purposes
            purposes = ["general", "database", "field", "file"]

            for purpose in purposes:
                active_key = await self.key_manager.get_active_key(purpose)
                if not active_key:
                    await self.key_manager.generate_key(purpose=purpose)
                    self.logger.success(
                        f"Generated initial key for purpose: {purpose}", LogCategory.SECURITY
                    )

            # Cleanup expired keys
            await self.key_manager.cleanup_expired_keys()

            self.logger.success("Encryption service initialized", LogCategory.SECURITY)

        except Exception as e:
            self.logger.error(f"Encryption service initialization failed: {e}")
            raise ExtractorError("Encryption service initialization failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def encrypt_sensitive_field(
        self, plaintext: str, purpose: str = "field", associated_data: str | None = None
    ) -> dict[str, str]:
        """
        Encrypt a sensitive field value.

        Args:
            plaintext: Text to encrypt
            purpose: Key purpose
            associated_data: Additional authenticated data

        Returns:
            Dictionary with encrypted data and metadata
        """
        active_key = await self.key_manager.get_active_key(purpose)
        if not active_key:
            active_key = await self.key_manager.generate_key(purpose=purpose)

        key_bytes = await self.key_manager.get_key(active_key.key_id)
        encryptor = FieldEncryptor(key_bytes, self.logger)

        encrypted_data = encryptor.encrypt_field(plaintext, associated_data)

        return {
            "encrypted_data": encrypted_data,
            "key_id": active_key.key_id,
            "algorithm": active_key.algorithm,
            "encrypted_at": datetime.utcnow().isoformat(),
        }

    async def decrypt_sensitive_field(
        self, encrypted_field: dict[str, str], associated_data: str | None = None
    ) -> str:
        """
        Decrypt a sensitive field value.

        Args:
            encrypted_field: Dictionary with encrypted data and metadata
            associated_data: Additional authenticated data (must match encryption)

        Returns:
            Decrypted plaintext
        """
        key_id = encrypted_field["key_id"]
        encrypted_data = encrypted_field["encrypted_data"]

        key_bytes = await self.key_manager.get_key(key_id)
        encryptor = FieldEncryptor(key_bytes, self.logger)

        return encryptor.decrypt_field(encrypted_data, associated_data)

    async def encrypt_file_secure(
        self,
        input_path: Path,
        output_path: Path | None = None,
        purpose: str = "file",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Encrypt a file securely.

        Args:
            input_path: Path to plaintext file
            output_path: Path for encrypted file (defaults to input_path + .enc)
            purpose: Key purpose
            metadata: Optional metadata to include

        Returns:
            Encryption metadata
        """
        if output_path is None:
            output_path = input_path.with_suffix(input_path.suffix + ".enc")

        active_key = await self.key_manager.get_active_key(purpose)
        if not active_key:
            active_key = await self.key_manager.generate_key(purpose=purpose)

        key_bytes = await self.key_manager.get_key(active_key.key_id)
        file_encryptor = FileEncryptor(key_bytes, self.logger)

        encryption_metadata = await file_encryptor.encrypt_file(input_path, output_path, metadata)
        encryption_metadata["key_id"] = active_key.key_id

        return encryption_metadata

    async def decrypt_file_secure(
        self,
        input_path: Path,
        key_id: str,
        output_path: Path | None = None,
        verify_hash: str | None = None,
    ) -> dict[str, Any]:
        """
        Decrypt a file securely.

        Args:
            input_path: Path to encrypted file
            key_id: Encryption key ID
            output_path: Path for decrypted file (defaults to input_path without .enc)
            verify_hash: Optional hash to verify integrity

        Returns:
            Decryption metadata
        """
        if output_path is None:
            output_path = input_path.with_suffix("")
            if output_path.suffix == ".enc":
                output_path = output_path.with_suffix("")

        key_bytes = await self.key_manager.get_key(key_id)
        file_encryptor = FileEncryptor(key_bytes, self.logger)

        return await file_encryptor.decrypt_file(input_path, output_path, verify_hash)

    def get_secure_ssl_context(
        self,
        cert_file: Path | None = None,
        key_file: Path | None = None,
        ca_file: Path | None = None,
    ) -> ssl.SSLContext:
        """Get secure SSL context for TLS connections."""
        return self.tls_manager.create_secure_ssl_context(
            cert_file=cert_file, key_file=key_file, ca_file=ca_file
        )

    async def rotate_keys_for_purpose(self, purpose: str) -> list[str]:
        """
        Rotate all keys for a specific purpose.

        Args:
            purpose: Key purpose

        Returns:
            List of new key IDs
        """
        old_keys = [
            k for k in self.key_manager.keys.values() if k.purpose == purpose and k.is_active
        ]
        new_key_ids = []

        for old_key in old_keys:
            if old_key.needs_rotation():
                new_key = await self.key_manager.rotate_key(old_key.key_id)
                new_key_ids.append(new_key.key_id)

        if new_key_ids:
            self.logger.success(
                f"Rotated {len(new_key_ids)} keys for purpose: {purpose}", LogCategory.SECURITY
            )

        return new_key_ids
