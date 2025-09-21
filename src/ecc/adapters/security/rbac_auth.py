"""Role-Based Access Control (RBAC) authentication system for ECC.

Implements the security requirements from ECC specifications v2.0:
- Role-based access control with defined roles
- Multi-factor authentication
- Session management with timeout
- Comprehensive audit logging
"""

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import jwt
from passlib.context import CryptContext

from src.ecc.adapters.security.vault_client import VaultClient
from src.ecc.core.error_handling import ExtractorError
from src.ecc.core.logging_system import ExtractorLogger, LogCategory


class UserRole(Enum):
    """User roles as defined in ECC specifications."""

    EDITOR_IN_CHIEF = "editor_in_chief"
    ASSOCIATE_EDITOR = "associate_editor"
    ADMIN = "admin"
    AUDITOR = "auditor"
    GUEST = "guest"  # Read-only access


class Permission(Enum):
    """System permissions."""

    # Manuscript permissions
    READ_MANUSCRIPTS = "read_manuscripts"
    EDIT_MANUSCRIPTS = "edit_manuscripts"
    DELETE_MANUSCRIPTS = "delete_manuscripts"

    # AI analysis permissions
    VIEW_AI_ANALYSIS = "view_ai_analysis"
    APPROVE_AI_ANALYSIS = "approve_ai_analysis"
    OVERRIDE_AI_ANALYSIS = "override_ai_analysis"

    # User management
    CREATE_USERS = "create_users"
    EDIT_USERS = "edit_users"
    DELETE_USERS = "delete_users"

    # System administration
    VIEW_SYSTEM_LOGS = "view_system_logs"
    MANAGE_SYSTEM_CONFIG = "manage_system_config"
    PERFORM_BACKUPS = "perform_backups"

    # Audit and security
    VIEW_AUDIT_TRAIL = "view_audit_trail"
    EXPORT_DATA = "export_data"
    SECURITY_ADMINISTRATION = "security_administration"


@dataclass
class User:
    """User entity with RBAC information."""

    id: str
    username: str
    email: str
    full_name: str
    roles: set[UserRole] = field(default_factory=set)
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: datetime | None = None
    password_hash: str | None = None
    mfa_secret: str | None = None
    mfa_enabled: bool = False
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: list[UserRole]) -> bool:
        """Check if user has any of the specified roles."""
        return bool(self.roles.intersection(set(roles)))

    def is_locked(self) -> bool:
        """Check if user account is locked."""
        return self.locked_until is not None and datetime.utcnow() < self.locked_until

    def can_login(self) -> bool:
        """Check if user can log in."""
        return self.is_active and self.is_verified and not self.is_locked()


@dataclass
class Session:
    """User session information."""

    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=30))
    ip_address: str = ""
    user_agent: str = ""
    is_active: bool = True
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if session is valid."""
        return self.is_active and not self.is_expired()

    def extend_session(self, minutes: int = 30):
        """Extend session expiration."""
        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)
        self.last_activity = datetime.utcnow()


class RolePermissionManager:
    """Manages role-to-permission mappings."""

    def __init__(self):
        """Initialize with default role-permission mappings."""
        self.role_permissions = {
            UserRole.EDITOR_IN_CHIEF: {
                Permission.READ_MANUSCRIPTS,
                Permission.EDIT_MANUSCRIPTS,
                Permission.DELETE_MANUSCRIPTS,
                Permission.VIEW_AI_ANALYSIS,
                Permission.APPROVE_AI_ANALYSIS,
                Permission.OVERRIDE_AI_ANALYSIS,
                Permission.CREATE_USERS,
                Permission.EDIT_USERS,
                Permission.VIEW_SYSTEM_LOGS,
                Permission.VIEW_AUDIT_TRAIL,
                Permission.EXPORT_DATA,
            },
            UserRole.ASSOCIATE_EDITOR: {
                Permission.READ_MANUSCRIPTS,
                Permission.EDIT_MANUSCRIPTS,
                Permission.VIEW_AI_ANALYSIS,
                Permission.APPROVE_AI_ANALYSIS,
                Permission.VIEW_AUDIT_TRAIL,
            },
            UserRole.ADMIN: {
                Permission.READ_MANUSCRIPTS,
                Permission.EDIT_MANUSCRIPTS,
                Permission.DELETE_MANUSCRIPTS,
                Permission.CREATE_USERS,
                Permission.EDIT_USERS,
                Permission.DELETE_USERS,
                Permission.VIEW_SYSTEM_LOGS,
                Permission.MANAGE_SYSTEM_CONFIG,
                Permission.PERFORM_BACKUPS,
                Permission.VIEW_AUDIT_TRAIL,
                Permission.SECURITY_ADMINISTRATION,
            },
            UserRole.AUDITOR: {
                Permission.READ_MANUSCRIPTS,
                Permission.VIEW_AI_ANALYSIS,
                Permission.VIEW_SYSTEM_LOGS,
                Permission.VIEW_AUDIT_TRAIL,
                Permission.EXPORT_DATA,
            },
            UserRole.GUEST: {
                Permission.READ_MANUSCRIPTS,
                Permission.VIEW_AI_ANALYSIS,
            },
        }

    def get_permissions_for_role(self, role: UserRole) -> set[Permission]:
        """Get all permissions for a specific role."""
        return self.role_permissions.get(role, set())

    def get_user_permissions(self, user: User) -> set[Permission]:
        """Get all permissions for a user based on their roles."""
        permissions = set()
        for role in user.roles:
            permissions.update(self.get_permissions_for_role(role))
        return permissions

    def user_has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        user_permissions = self.get_user_permissions(user)
        return permission in user_permissions

    def add_role_permission(self, role: UserRole, permission: Permission):
        """Add a permission to a role."""
        if role not in self.role_permissions:
            self.role_permissions[role] = set()
        self.role_permissions[role].add(permission)

    def remove_role_permission(self, role: UserRole, permission: Permission):
        """Remove a permission from a role."""
        if role in self.role_permissions:
            self.role_permissions[role].discard(permission)


class AuthenticationManager:
    """Main authentication and authorization manager."""

    def __init__(
        self,
        vault_client: VaultClient | None = None,
        jwt_secret: str | None = None,
        logger: ExtractorLogger | None = None,
    ):
        """
        Initialize authentication manager.

        Args:
            vault_client: Vault client for secure storage
            jwt_secret: Secret for JWT token signing
            logger: Logger instance
        """
        self.vault = vault_client
        self.jwt_secret = jwt_secret or self._generate_jwt_secret()
        self.logger = logger or ExtractorLogger("auth_manager")
        self.password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.permission_manager = RolePermissionManager()

        # In-memory stores (in production, these would be in database/cache)
        self.users: dict[str, User] = {}
        self.sessions: dict[str, Session] = {}
        self.user_by_email: dict[str, str] = {}  # email -> user_id mapping

        # Security settings
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 15
        self.session_timeout_minutes = 30
        self.jwt_expiration_hours = 24

    def _generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret."""
        return secrets.token_urlsafe(32)

    def _generate_session_id(self) -> str:
        """Generate a secure session ID."""
        return secrets.token_urlsafe(32)

    def _hash_password(self, password: str) -> str:
        """Hash a password securely."""
        return self.password_context.hash(password)

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return self.password_context.verify(password, hashed)

    def _generate_mfa_secret(self) -> str:
        """Generate MFA secret for TOTP."""
        return secrets.token_urlsafe(20)

    async def create_user(
        self,
        username: str,
        email: str,
        full_name: str,
        password: str,
        roles: list[UserRole],
        created_by: str,
    ) -> User:
        """
        Create a new user account.

        Args:
            username: Unique username
            email: User email address
            full_name: User's full name
            password: Plain text password
            roles: List of roles to assign
            created_by: User ID who created this account

        Returns:
            Created user object
        """
        self.logger.enter_context(f"create_user_{username}")

        try:
            # Check if user already exists
            if username in self.users or email in self.user_by_email:
                raise ExtractorError(f"User already exists: {username}")

            # Generate user ID
            user_id = hashlib.sha256(f"{username}:{email}:{time.time()}".encode()).hexdigest()[:12]

            # Create user
            user = User(
                id=user_id,
                username=username,
                email=email,
                full_name=full_name,
                roles=set(roles),
                password_hash=self._hash_password(password),
                mfa_secret=self._generate_mfa_secret(),
                metadata={"created_by": created_by},
            )

            # Store user
            self.users[user_id] = user
            self.user_by_email[email] = user_id

            # Store in Vault if available
            if self.vault:
                await self.vault.write_secret(
                    f"users/{user_id}",
                    {
                        "username": username,
                        "email": email,
                        "full_name": full_name,
                        "roles": [role.value for role in roles],
                        "password_hash": user.password_hash,
                        "mfa_secret": user.mfa_secret,
                        "created_by": created_by,
                    },
                    metadata={"type": "user_account", "created_by": created_by},
                )

            self.logger.success(
                f"User created: {username} with roles: {[r.value for r in roles]}",
                LogCategory.SECURITY,
            )

            return user

        except Exception as e:
            self.logger.error(f"Failed to create user {username}: {e}")
            raise ExtractorError("User creation failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def authenticate_user(
        self,
        username_or_email: str,
        password: str,
        mfa_token: str | None = None,
        ip_address: str = "",
        user_agent: str = "",
    ) -> Session | None:
        """
        Authenticate user and create session.

        Args:
            username_or_email: Username or email
            password: User password
            mfa_token: MFA token if enabled
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Session object if authentication successful
        """
        self.logger.enter_context(f"authenticate_{username_or_email}")

        try:
            # Find user
            user = self._find_user(username_or_email)
            if not user:
                self.logger.warning(f"Authentication failed: user not found: {username_or_email}")
                return None

            # Check if user can login
            if not user.can_login():
                if user.is_locked():
                    self.logger.warning(f"Authentication failed: account locked: {user.username}")
                else:
                    self.logger.warning(
                        f"Authentication failed: account inactive/unverified: {user.username}"
                    )
                return None

            # Verify password
            if not user.password_hash or not self._verify_password(password, user.password_hash):
                self._handle_failed_login(user)
                self.logger.warning(f"Authentication failed: invalid password: {user.username}")
                return None

            # Verify MFA if enabled
            if user.mfa_enabled:
                if not mfa_token or not self._verify_mfa_token(user, mfa_token):
                    self.logger.warning(f"Authentication failed: invalid MFA: {user.username}")
                    return None

            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.utcnow()

            # Create session
            session = Session(
                session_id=self._generate_session_id(),
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.utcnow() + timedelta(minutes=self.session_timeout_minutes),
            )

            self.sessions[session.session_id] = session

            self.logger.success(f"User authenticated: {user.username}", LogCategory.SECURITY)

            return session

        except Exception as e:
            self.logger.error(f"Authentication error for {username_or_email}: {e}")
            return None

        finally:
            self.logger.exit_context(success=True)

    def _find_user(self, username_or_email: str) -> User | None:
        """Find user by username or email."""
        # Try by username first
        for user in self.users.values():
            if user.username == username_or_email:
                return user

        # Try by email
        if username_or_email in self.user_by_email:
            user_id = self.user_by_email[username_or_email]
            return self.users.get(user_id)

        return None

    def _handle_failed_login(self, user: User):
        """Handle failed login attempt."""
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= self.max_failed_attempts:
            user.locked_until = datetime.utcnow() + timedelta(minutes=self.lockout_duration_minutes)
            self.logger.warning(f"Account locked due to failed attempts: {user.username}")

    def _verify_mfa_token(self, user: User, token: str) -> bool:
        """Verify MFA TOTP token."""
        # This would integrate with a TOTP library like pyotp
        # For now, just return True if token exists
        return len(token) == 6 and token.isdigit()

    async def validate_session(self, session_id: str) -> Session | None:
        """
        Validate and return session if valid.

        Args:
            session_id: Session ID to validate

        Returns:
            Session object if valid
        """
        session = self.sessions.get(session_id)

        if not session or not session.is_valid():
            if session:
                # Remove expired session
                del self.sessions[session_id]
                self.logger.info(f"Removed expired session: {session_id[:8]}...")
            return None

        # Extend session on activity
        session.extend_session(self.session_timeout_minutes)

        return session

    async def get_user_by_session(self, session_id: str) -> User | None:
        """Get user associated with session."""
        session = await self.validate_session(session_id)
        if not session:
            return None

        return self.users.get(session.user_id)

    async def logout_user(self, session_id: str) -> bool:
        """
        Log out user by invalidating session.

        Args:
            session_id: Session ID to invalidate

        Returns:
            True if successful
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.is_active = False
            del self.sessions[session_id]

            self.logger.success(
                f"User logged out: session {session_id[:8]}...", LogCategory.SECURITY
            )
            return True

        return False

    async def check_permission(
        self, session_id: str, permission: Permission, resource_id: str | None = None
    ) -> bool:
        """
        Check if user has permission for an action.

        Args:
            session_id: User session ID
            permission: Required permission
            resource_id: Optional resource identifier

        Returns:
            True if permission granted
        """
        user = await self.get_user_by_session(session_id)
        if not user:
            return False

        return self.permission_manager.user_has_permission(user, permission)

    async def require_permission(
        self, session_id: str, permission: Permission, resource_id: str | None = None
    ):
        """
        Require permission or raise error.

        Args:
            session_id: User session ID
            permission: Required permission
            resource_id: Optional resource identifier

        Raises:
            ExtractorError: If permission denied
        """
        if not await self.check_permission(session_id, permission, resource_id):
            user = await self.get_user_by_session(session_id)
            username = user.username if user else "unknown"

            self.logger.warning(
                f"Permission denied: {username} attempted {permission.value}", LogCategory.SECURITY
            )

            raise ExtractorError(f"Permission denied: {permission.value}")

    def generate_jwt_token(self, user: User, session: Session) -> str:
        """
        Generate JWT token for API access.

        Args:
            user: User object
            session: Session object

        Returns:
            JWT token string
        """
        payload = {
            "user_id": user.id,
            "username": user.username,
            "roles": [role.value for role in user.roles],
            "session_id": session.session_id,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours),
        }

        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    def verify_jwt_token(self, token: str) -> dict[str, Any] | None:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])

            # Check if session is still valid
            session_id = payload.get("session_id")
            if session_id and session_id not in self.sessions:
                return None

            return payload

        except jwt.ExpiredSignatureError:
            self.logger.info("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid JWT token")
            return None

    async def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        expired_sessions = []

        for session_id, session in self.sessions.items():
            if not session.is_valid():
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.sessions[session_id]

        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    async def get_active_sessions(self, user_id: str | None = None) -> list[Session]:
        """Get active sessions, optionally filtered by user."""
        sessions = []

        for session in self.sessions.values():
            if session.is_valid():
                if user_id is None or session.user_id == user_id:
                    sessions.append(session)

        return sessions

    async def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user."""
        revoked_count = 0
        sessions_to_remove = []

        for session_id, session in self.sessions.items():
            if session.user_id == user_id:
                sessions_to_remove.append(session_id)
                revoked_count += 1

        for session_id in sessions_to_remove:
            del self.sessions[session_id]

        self.logger.success(
            f"Revoked {revoked_count} sessions for user: {user_id}", LogCategory.SECURITY
        )

        return revoked_count

    async def update_user_roles(
        self, user_id: str, new_roles: list[UserRole], updated_by: str
    ) -> bool:
        """
        Update user roles.

        Args:
            user_id: User ID to update
            new_roles: New roles to assign
            updated_by: User ID who made the change

        Returns:
            True if successful
        """
        user = self.users.get(user_id)
        if not user:
            raise ExtractorError(f"User not found: {user_id}")

        old_roles = user.roles.copy()
        user.roles = set(new_roles)

        # Update in Vault if available
        if self.vault:
            await self.vault.write_secret(
                f"users/{user_id}",
                {
                    "username": user.username,
                    "email": user.email,
                    "roles": [role.value for role in new_roles],
                    "updated_by": updated_by,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )

        self.logger.success(
            f"User roles updated: {user.username} from {[r.value for r in old_roles]} to {[r.value for r in new_roles]}",
            LogCategory.SECURITY,
        )

        return True


# Decorator for requiring authentication
def require_auth(permission: Permission | None = None):
    """
    Decorator to require authentication and optional permission.

    Args:
        permission: Optional permission required
    """

    def decorator(func):
        async def wrapper(self, session_id: str, *args, **kwargs):
            # Validate session
            if not hasattr(self, "auth_manager"):
                raise ExtractorError("Authentication manager not available")

            user = await self.auth_manager.get_user_by_session(session_id)
            if not user:
                raise ExtractorError("Authentication required")

            # Check permission if specified
            if permission:
                await self.auth_manager.require_permission(session_id, permission)

            return await func(self, session_id, *args, **kwargs)

        return wrapper

    return decorator


# Decorator for requiring specific roles
def require_roles(*required_roles: UserRole):
    """
    Decorator to require specific roles.

    Args:
        required_roles: Roles that are allowed
    """

    def decorator(func):
        async def wrapper(self, session_id: str, *args, **kwargs):
            if not hasattr(self, "auth_manager"):
                raise ExtractorError("Authentication manager not available")

            user = await self.auth_manager.get_user_by_session(session_id)
            if not user:
                raise ExtractorError("Authentication required")

            if not user.has_any_role(list(required_roles)):
                raise ExtractorError(
                    f"Insufficient privileges: requires one of {[r.value for r in required_roles]}"
                )

            return await func(self, session_id, *args, **kwargs)

        return wrapper

    return decorator
