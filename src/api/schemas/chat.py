from pydantic import BaseModel


class UserInfo(BaseModel):
    """Optional user identification sent by the client on each request."""
    external_user_id: str | None = None
    name: str | None = None
    email: str | None = None
    business_name: str | None = None
    extra_metadata: dict | None = None


class SessionContext(BaseModel):
    """Optional session context sent by the client."""
    entry_url: str | None = None
    exit_url: str | None = None
    device_type: str | None = None
    browser: str | None = None
    extra_metadata: dict | None = None


class ChatRequest(BaseModel):
    app_id: str
    session_id: str
    message: str
    stream: bool = False
    provider_override: str | None = None
    user_info: UserInfo | None = None
    session_context: SessionContext | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    token_usage: dict[str, int]
    timestamp: str           # ISO — server time of assistant turn
    user_timestamp: str      # ISO — server time of user turn


# ── Session lifecycle ─────────────────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    session_id: str
    app_id: str
    user_info: UserInfo | None = None
    session_context: SessionContext | None = None


class SessionEndRequest(BaseModel):
    session_id: str
    app_id: str
    exit_url: str | None = None


class SessionReviewRequest(BaseModel):
    session_id: str
    app_id: str
    rating: int          # 1–5
    emoji_label: str | None = None
    comment: str | None = None


class UserLookupRequest(BaseModel):
    app_id: str
    email: str


# ── History / session list ────────────────────────────────────────────────────

class MessageRecord(BaseModel):
    role: str
    content: str
    timestamp: str       # ISO from DB


class SessionRecord(BaseModel):
    session_id: str
    started_at: str
    ended_at: str | None
    message_count: int
    preview: str | None
    messages: list[MessageRecord]


class SessionListResponse(BaseModel):
    sessions: list[SessionRecord]


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageRecord]
