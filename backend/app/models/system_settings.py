"""
SQLAlchemy model for system-wide settings
"""

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.sql import func

from app.db.base import Base


class SystemSettings(Base):
    """
    Model for storing system-wide configuration settings.

    Settings are stored as key-value pairs with optional descriptions.
    This allows for flexible configuration without schema changes.

    Known keys:
    - transcription.max_retries: Maximum retry attempts for transcription (default: 3, 0 = unlimited)
    - transcription.retry_limit_enabled: Whether retry limits are enforced (default: true)
    """

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SystemSettings(key={self.key}, value={self.value})>"
