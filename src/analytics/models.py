from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from src.auth.models import Base


class SessionReview(Base):
    __tablename__ = "session_reviews"
    __table_args__ = (
        Index("idx_review_session_app", "session_id", "app_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), nullable=False)
    app_id = Column(String(64), nullable=False)
    rating = Column(Integer, nullable=False)        # 1 (Very Bad) – 5 (Very Good)
    emoji_label = Column(String(64), nullable=True) # "Very Bad", "Bad", …
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        Index("idx_user_app_external", "app_id", "external_user_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_id = Column(String(64), nullable=False)
    external_user_id = Column(String(256), nullable=True)  # client-provided identifier
    name = Column(String(256), nullable=True)
    email = Column(String(256), nullable=True)
    business_name = Column(String(256), nullable=True)
    extra_metadata = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sessions = relationship("ChatSession", back_populates="user", lazy="dynamic")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("idx_chat_session_app", "session_id", "app_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), nullable=False)
    app_id = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=True)

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    entry_url = Column(String(2048), nullable=True)
    exit_url = Column(String(2048), nullable=True)

    device_type = Column(String(64), nullable=True)   # "desktop" | "mobile" | "tablet"
    browser = Column(String(128), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)

    message_count = Column(Integer, default=0, nullable=False)
    extra_metadata = Column(Text, nullable=True)  # JSON string

    is_live = Column(Boolean, default=False, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    user = relationship("UserProfile", back_populates="sessions")
