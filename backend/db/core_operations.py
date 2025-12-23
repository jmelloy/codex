"""Core database operations for user authentication and workspace management."""

from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from db.core_models import (
    RefreshToken,
    User,
    get_core_engine,
    get_core_session,
    init_core_db,
)


class CoreDatabaseManager:
    """Manager for core database operations (users, auth)."""

    def __init__(self, db_path: Path):
        """Initialize the core database manager.
        
        Args:
            db_path: Path to the core database file
        """
        self.db_path = db_path
        self.engine = None
        self._session = None

    def initialize(self):
        """Initialize the core database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = init_core_db(str(self.db_path))

    def get_session(self) -> Session:
        """Get a database session."""
        if self.engine is None:
            self.engine = get_core_engine(str(self.db_path))
        return get_core_session(self.engine)

    # User operations
    def create_user(
        self,
        username: str,
        email: str,
        hashed_password: str,
        workspace_path: str,
    ) -> User:
        """Create a new user."""
        session = self.get_session()
        try:
            user = User.create(
                session,
                username=username,
                email=email,
                hashed_password=hashed_password,
                workspace_path=workspace_path,
                is_active=True,
            )
            session.commit()
            return user
        finally:
            session.close()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        session = self.get_session()
        try:
            return User.find_one_by(session, username=username)
        finally:
            session.close()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        session = self.get_session()
        try:
            return User.get_by_id(session, user_id)
        finally:
            session.close()

    # Refresh token operations
    def create_refresh_token(
        self, token: str, user_id: int, expires_at
    ) -> RefreshToken:
        """Create a refresh token."""
        session = self.get_session()
        try:
            refresh_token = RefreshToken.create(
                session,
                validate_fk=False,
                token=token,
                user_id=user_id,
                expires_at=expires_at,
            )
            session.commit()
            return refresh_token
        finally:
            session.close()

    def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        """Get a refresh token by token string."""
        session = self.get_session()
        try:
            return RefreshToken.find_one_by(session, token=token)
        finally:
            session.close()

    def revoke_refresh_token(self, token: str) -> bool:
        """Revoke a refresh token."""
        session = self.get_session()
        try:
            refresh_token = RefreshToken.find_one_by(session, token=token)
            if refresh_token:
                refresh_token.update(session, revoked=True)
                session.commit()
                return True
            return False
        finally:
            session.close()
