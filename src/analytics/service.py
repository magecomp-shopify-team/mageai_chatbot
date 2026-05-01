import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.models import ChatSession, SessionReview, UserProfile

logger = logging.getLogger(__name__)


async def upsert_user(
    db: AsyncSession,
    app_id: str,
    external_user_id: str | None,
    name: str | None,
    email: str | None,
    business_name: str | None,
    extra_metadata: dict | None,
) -> UserProfile | None:
    """Find-or-create a UserProfile. Returns None if no identifying info provided."""
    if not any([external_user_id, name, email, business_name]):
        return None

    user: UserProfile | None = None

    if external_user_id:
        result = await db.execute(
            select(UserProfile).where(
                UserProfile.app_id == app_id,
                UserProfile.external_user_id == external_user_id,
            )
        )
        user = result.scalar_one_or_none()

    if user is None and email:
        result = await db.execute(
            select(UserProfile).where(
                UserProfile.app_id == app_id,
                UserProfile.email == email,
            )
        )
        user = result.scalar_one_or_none()

    now = datetime.utcnow()
    if user is None:
        user = UserProfile(
            app_id=app_id,
            external_user_id=external_user_id,
            name=name,
            email=email,
            business_name=business_name,
            extra_metadata=json.dumps(extra_metadata) if extra_metadata else None,
            created_at=now,
            last_seen_at=now,
        )
        db.add(user)
    else:
        if name:
            user.name = name
        if email:
            user.email = email
        if business_name:
            user.business_name = business_name
        if extra_metadata:
            user.extra_metadata = json.dumps(extra_metadata)
        user.last_seen_at = now

    await db.flush()
    return user


async def upsert_session(
    db: AsyncSession,
    session_id: str,
    app_id: str,
    user_id: int | None,
    entry_url: str | None,
    exit_url: str | None,
    ip_address: str | None,
    user_agent: str | None,
    device_type: str | None,
    browser: str | None,
    extra_metadata: dict | None,
) -> ChatSession:
    """Find-or-create a ChatSession and update activity fields."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.app_id == app_id,
        )
    )
    session: ChatSession | None = result.scalar_one_or_none()
    now = datetime.utcnow()

    if session is None:
        session = ChatSession(
            session_id=session_id,
            app_id=app_id,
            user_id=user_id,
            started_at=now,
            last_active_at=now,
            entry_url=entry_url,
            exit_url=exit_url,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
            browser=browser,
            message_count=1,
            extra_metadata=json.dumps(extra_metadata) if extra_metadata else None,
            is_live=True,
        )
        db.add(session)
    else:
        session.last_active_at = now
        session.is_live = True
        session.message_count = (session.message_count or 0) + 1
        if exit_url:
            session.exit_url = exit_url
        if user_id and not session.user_id:
            session.user_id = user_id
        if extra_metadata:
            session.extra_metadata = json.dumps(extra_metadata)

    await db.flush()
    return session


async def create_session_record(
    db: AsyncSession,
    session_id: str,
    app_id: str,
    user_id: int | None,
    entry_url: str | None,
    ip_address: str | None,
    user_agent: str | None,
    device_type: str | None,
    browser: str | None,
    extra_metadata: dict | None,
) -> ChatSession:
    """Explicitly create a new session record (idempotent — returns existing if found)."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.app_id == app_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    now = datetime.utcnow()
    session = ChatSession(
        session_id=session_id,
        app_id=app_id,
        user_id=user_id,
        started_at=now,
        last_active_at=now,
        entry_url=entry_url,
        ip_address=ip_address,
        user_agent=user_agent,
        device_type=device_type,
        browser=browser,
        message_count=0,
        extra_metadata=json.dumps(extra_metadata) if extra_metadata else None,
        is_live=True,
    )
    db.add(session)
    await db.commit()
    return session


async def get_user_sessions(
    db: AsyncSession,
    app_id: str,
    external_user_id: str,
    limit: int = 10,
) -> list[ChatSession]:
    """Return the most recent sessions for a user, newest first."""
    user_result = await db.execute(
        select(UserProfile).where(
            UserProfile.app_id == app_id,
            UserProfile.external_user_id == external_user_id,
        )
    )
    user = user_result.scalar_one_or_none()
    if not user:
        return []

    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id, ChatSession.app_id == app_id)
        .order_by(ChatSession.started_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def save_review(
    db: AsyncSession,
    session_id: str,
    app_id: str,
    rating: int,
    emoji_label: str | None,
    comment: str | None = None,
) -> SessionReview:
    """Save a user satisfaction rating (and optional comment) against a session."""
    async with db.begin_nested():
        review = SessionReview(
            session_id=session_id,
            app_id=app_id,
            rating=rating,
            emoji_label=emoji_label,
            comment=comment or None,
            created_at=datetime.utcnow(),
        )
        db.add(review)
    await db.commit()
    return review


async def lookup_user_by_email(
    db: AsyncSession,
    app_id: str,
    email: str,
) -> UserProfile | None:
    """Return the UserProfile matching app_id + email, or None."""
    result = await db.execute(
        select(UserProfile).where(
            UserProfile.app_id == app_id,
            UserProfile.email == email,
        )
    )
    return result.scalar_one_or_none()


async def end_session(db: AsyncSession, session_id: str, app_id: str, exit_url: str | None = None) -> None:
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.app_id == app_id,
        )
    )
    session = result.scalar_one_or_none()
    if session:
        now = datetime.utcnow()
        session.ended_at = now
        session.is_live = False
        session.closed_at = now
        if exit_url:
            session.exit_url = exit_url
        await db.commit()
