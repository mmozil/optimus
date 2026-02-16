"""
Agent Optimus — Authentication Service (Phase 15).
Handles user registration, login, JWT tokens, and API key management.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from src.core.config import settings

logger = logging.getLogger(__name__)

# Role hierarchy — higher index = more permissions
ROLE_HIERARCHY = {"viewer": 0, "user": 1, "admin": 2}


class AuthService:
    """
    Manages user authentication, JWT tokens, and API keys.
    Uses bcrypt-like hashing via hashlib (no extra dependency).
    """

    def __init__(self):
        self._jwt = None  # Lazy import

    @property
    def jwt(self):
        """Lazy-load PyJWT to avoid import errors if not installed."""
        if self._jwt is None:
            try:
                import jwt
                self._jwt = jwt
            except ImportError:
                raise ImportError(
                    "PyJWT não instalado. Rode: pip install PyJWT"
                )
        return self._jwt

    # ============================================
    # Password Hashing (SHA-256 + salt)
    # ============================================

    def _hash_password(self, password: str) -> str:
        """Hash password with random salt using SHA-256."""
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"{salt}${hashed}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against its stored hash."""
        try:
            salt, hashed = stored_hash.split("$", 1)
            return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hashed
        except ValueError:
            return False

    # ============================================
    # JWT Token Management
    # ============================================

    def create_access_token(self, user_id: str, email: str, role: str) -> str:
        """Create a JWT access token."""
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            ),
            "iat": datetime.now(timezone.utc),
        }
        return self.jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a longer-lived refresh token."""
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(
                days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
            ),
            "iat": datetime.now(timezone.utc),
        }
        return self.jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def decode_token(self, token: str) -> dict | None:
        """Decode and validate a JWT token. Returns payload or None."""
        try:
            payload = self.jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except self.jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except self.jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    # ============================================
    # API Key Management
    # ============================================

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure random API key."""
        return f"optimus_{secrets.token_hex(24)}"

    # ============================================
    # User CRUD (via SQLAlchemy)
    # ============================================

    async def register_user(
        self, email: str, password: str, display_name: str = "", role: str = "user"
    ) -> dict:
        """Register a new user and return user data + tokens."""
        from src.infra.supabase_client import get_async_session

        hashed_pw = self._hash_password(password)
        api_key = self.generate_api_key()

        async with get_async_session() as session:
            # Check if email already exists
            check = await session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            )
            if check.fetchone():
                raise ValueError(f"Email '{email}' já está cadastrado.")

            # Insert new user
            result = await session.execute(
                text("""
                    INSERT INTO users (email, hashed_password, display_name, role, api_key)
                    VALUES (:email, :hashed_password, :display_name, :role, :api_key)
                    RETURNING id, email, display_name, role, api_key, created_at
                """),
                {
                    "email": email,
                    "hashed_password": hashed_pw,
                    "display_name": display_name or email.split("@")[0],
                    "role": role,
                    "api_key": api_key,
                },
            )
            row = result.fetchone()
            await session.commit()

        user_id = str(row[0])
        access_token = self.create_access_token(user_id, email, role)
        refresh_token = self.create_refresh_token(user_id)

        logger.info(f"User registered: {email} (role={role})")

        return {
            "user": {
                "id": user_id,
                "email": row[1],
                "display_name": row[2],
                "role": row[3],
                "api_key": row[4],
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def login(self, email: str, password: str) -> dict:
        """Authenticate user and return tokens."""
        from src.infra.supabase_client import get_async_session

        async with get_async_session() as session:
            result = await session.execute(
                text("""
                    SELECT id, email, hashed_password, display_name, role, is_active
                    FROM users WHERE email = :email
                """),
                {"email": email},
            )
            row = result.fetchone()

        if not row:
            raise ValueError("Credenciais inválidas.")

        user_id, user_email, hashed_pw, display_name, role, is_active = row

        if not is_active:
            raise ValueError("Conta desativada. Contate o administrador.")

        if not self._verify_password(password, hashed_pw):
            raise ValueError("Credenciais inválidas.")

        access_token = self.create_access_token(str(user_id), user_email, role)
        refresh_token = self.create_refresh_token(str(user_id))

        logger.info(f"User login: {user_email}")

        return {
            "user": {
                "id": str(user_id),
                "email": user_email,
                "display_name": display_name,
                "role": role,
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def validate_api_key(self, api_key: str) -> dict | None:
        """Validate an API key and return user data if valid."""
        from src.infra.supabase_client import get_async_session

        async with get_async_session() as session:
            result = await session.execute(
                text("""
                    SELECT id, email, display_name, role, is_active
                    FROM users WHERE api_key = :api_key
                """),
                {"api_key": api_key},
            )
            row = result.fetchone()

        if not row or not row[4]:  # not found or not active
            return None

        return {
            "id": str(row[0]),
            "email": row[1],
            "display_name": row[2],
            "role": row[3],
        }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Exchange a valid refresh token for a new access token."""
        payload = self.decode_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            raise ValueError("Refresh token inválido ou expirado.")

        user_id = payload["sub"]

        # Fetch user to get current role/email
        from src.infra.supabase_client import get_async_session

        async with get_async_session() as session:
            result = await session.execute(
                text("SELECT email, role, is_active FROM users WHERE id = :id"),
                {"id": user_id},
            )
            row = result.fetchone()

        if not row or not row[2]:
            raise ValueError("Usuário não encontrado ou desativado.")

        new_access = self.create_access_token(user_id, row[0], row[1])
        return {"access_token": new_access, "token_type": "bearer"}

    # ============================================
    # Role Checks
    # ============================================

    @staticmethod
    def has_role(user_role: str, required_role: str) -> bool:
        """Check if user_role is >= required_role in hierarchy."""
        return ROLE_HIERARCHY.get(user_role, -1) >= ROLE_HIERARCHY.get(required_role, 99)


# Singleton
auth_service = AuthService()
