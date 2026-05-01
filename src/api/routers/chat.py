import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai import router as ai_router
from src.analytics.service import (
    create_session_record,
    end_session,
    get_user_sessions,
    lookup_user_by_email,
    save_review,
    upsert_session,
    upsert_user,
)
from src.api.deps import get_db
from src.api.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessageRecord,
    SessionCreateRequest,
    SessionEndRequest,
    SessionHistoryResponse,
    SessionListResponse,
    SessionRecord,
    SessionReviewRequest,
    UserLookupRequest,
)
from src.core.chat_debug import debug_log, new_trace_id
from src.core.utils import get_client_ip as _get_client_ip
from src.core.config import load_app_config
from src.pipeline.assembler import assemble
from src.pipeline.history import ConversationTurn, save_turn

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────



async def _capture_analytics(
    db: AsyncSession,
    request: Request,
    body: ChatRequest,
) -> int | None:
    """Upsert user + session; return user_id (or None). Non-fatal — logs on failure."""
    try:
        ip = _get_client_ip(request)
        ua = request.headers.get("user-agent")
        user_id: int | None = None

        if body.user_info:
            ui = body.user_info
            user = await upsert_user(
                db, body.app_id,
                external_user_id=ui.external_user_id,
                name=ui.name,
                email=ui.email,
                business_name=ui.business_name,
                extra_metadata=ui.extra_metadata,
            )
            user_id = user.id if user else None

        sc = body.session_context
        await upsert_session(
            db,
            session_id=body.session_id,
            app_id=body.app_id,
            user_id=user_id,
            entry_url=sc.entry_url if sc else None,
            exit_url=sc.exit_url if sc else None,
            ip_address=ip,
            user_agent=ua,
            device_type=sc.device_type if sc else None,
            browser=sc.browser if sc else None,
            extra_metadata=sc.extra_metadata if sc else None,
        )
        await db.commit()
        return user_id
    except Exception as exc:
        logger.warning("Analytics capture failed (non-fatal): %s", exc)
        return None


# ── Main chat endpoint ────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse | StreamingResponse:
    trace_id = new_trace_id()

    debug_log.request(
        trace_id=trace_id,
        app_id=body.app_id,
        session_id=body.session_id,
        message=body.message,
        stream=body.stream,
        provider_override=body.provider_override,
    )

    await _capture_analytics(db, request, body)

    try:
        load_app_config(body.app_id)
        context = await assemble(body.message, body.session_id, body.app_id, db=db)
    except Exception as exc:
        debug_log.error(trace_id, "assemble", exc)
        raise

    debug_log.assembled_context(
        trace_id=trace_id,
        system_prompt=context.system_prompt,
        messages=context.messages,
        token_breakdown=context.token_breakdown,
        rag_chunks=context.rag_chunks,
    )

    if body.stream:
        async def event_stream():
            full_text = ""
            started = False
            async for chunk in await ai_router.complete(
                context, body.app_id, override_provider=body.provider_override, stream=True
            ):
                full_text += chunk
                if not started:
                    started = True
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            user_turn = await save_turn(db, body.session_id, body.app_id, "user", body.message)
            asst_turn = await save_turn(db, body.session_id, body.app_id, "assistant", full_text)
            yield f"data: {json.dumps({'done': True, 'timestamp': asst_turn.created_at.isoformat(), 'user_timestamp': user_turn.created_at.isoformat()})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # Non-streaming path
    try:
        from config.settings import settings
        _cfg = load_app_config(body.app_id)
        _provider_id = body.provider_override or _cfg.provider
        _model = _cfg.model
        _max_tokens = _cfg.max_response_tokens
        _temperature = _cfg.temperature
    except Exception:
        from config.settings import settings
        _provider_id = body.provider_override or settings.DEFAULT_PROVIDER
        _model = settings.DEFAULT_MODEL
        _max_tokens = 512
        _temperature = 0.7

    debug_log.model_call(
        trace_id=trace_id,
        provider=_provider_id,
        model=_model,
        max_tokens=_max_tokens,
        temperature=_temperature,
        stream=False,
        message_count=len(context.messages),
        system_prompt_len=len(context.system_prompt),
    )

    t0 = time.perf_counter()
    try:
        result = await ai_router.complete(
            context, body.app_id, override_provider=body.provider_override
        )
    except Exception as exc:
        debug_log.error(trace_id, "model_call", exc)
        raise
    latency_ms = (time.perf_counter() - t0) * 1000

    debug_log.response(
        trace_id=trace_id,
        provider=result.provider,
        model=result.model,
        reply=result.text,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        finish_reason=result.finish_reason,
        latency_ms=latency_ms,
    )

    user_turn = await save_turn(db, body.session_id, body.app_id, "user", body.message)
    asst_turn = await save_turn(db, body.session_id, body.app_id, "assistant", result.text)

    return ChatResponse(
        reply=result.text,
        session_id=body.session_id,
        token_usage={"input": result.input_tokens, "output": result.output_tokens},
        timestamp=asst_turn.created_at.isoformat(),
        user_timestamp=user_turn.created_at.isoformat(),
    )


# ── Session lifecycle endpoints ───────────────────────────────────────────────

@router.post("/session/create", status_code=201)
async def create_session(
    body: SessionCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Explicitly create a session record before the first message is sent."""
    ip = _get_client_ip(request)
    ua = request.headers.get("user-agent")

    user_id: int | None = None
    if body.user_info:
        ui = body.user_info
        user = await upsert_user(
            db, body.app_id,
            external_user_id=ui.external_user_id,
            name=ui.name,
            email=ui.email,
            business_name=ui.business_name,
            extra_metadata=ui.extra_metadata,
        )
        user_id = user.id if user else None

    sc = body.session_context
    session = await create_session_record(
        db,
        session_id=body.session_id,
        app_id=body.app_id,
        user_id=user_id,
        entry_url=sc.entry_url if sc else None,
        ip_address=ip,
        user_agent=ua,
        device_type=sc.device_type if sc else None,
        browser=sc.browser if sc else None,
        extra_metadata=sc.extra_metadata if sc else None,
    )
    return {"session_id": session.session_id, "started_at": session.started_at.isoformat()}


@router.post("/session/end", status_code=204)
async def end_session_endpoint(
    body: SessionEndRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark a session as ended and record the exit URL."""
    await end_session(db, body.session_id, body.app_id, body.exit_url)


@router.post("/session/review", status_code=201)
async def submit_review(
    body: SessionReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Store a 1–5 emoji satisfaction rating for a session."""
    if not (1 <= body.rating <= 5):
        raise HTTPException(status_code=422, detail="rating must be between 1 and 5")
    review = await save_review(db, body.session_id, body.app_id, body.rating, body.emoji_label, body.comment)
    return {"success": True, "id": review.id}


# ── User lookup ──────────────────────────────────────────────────────────────

@router.post("/user/lookup")
async def user_lookup(
    body: UserLookupRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check whether a user with this email + app_id already exists.

    Returns their external_user_id so the widget can restore the correct
    identity (and therefore chat history) on first load.
    """
    user = await lookup_user_by_email(db, body.app_id, body.email)
    if user and user.external_user_id:
        return {"found": True, "external_user_id": user.external_user_id}
    return {"found": False, "external_user_id": None}


# ── History / session list endpoints ─────────────────────────────────────────

@router.get("/history/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    app_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionHistoryResponse:
    """Return all messages for a specific session (used for history cache refresh)."""
    result = await db.execute(
        select(ConversationTurn)
        .where(
            ConversationTurn.session_id == session_id,
            ConversationTurn.app_id == app_id,
        )
        .order_by(ConversationTurn.created_at.asc())
    )
    turns = list(result.scalars().all())
    messages = [
        MessageRecord(role=t.role, content=t.content, timestamp=t.created_at.isoformat())
        for t in turns
    ]
    return SessionHistoryResponse(session_id=session_id, messages=messages)


@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(
    app_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """Return the last 10 sessions for a user, each with full message history."""
    sessions = await get_user_sessions(db, app_id, user_id)

    records: list[SessionRecord] = []
    for s in sessions:
        turns_result = await db.execute(
            select(ConversationTurn)
            .where(
                ConversationTurn.session_id == s.session_id,
                ConversationTurn.app_id == app_id,
            )
            .order_by(ConversationTurn.created_at.asc())
        )
        turns = list(turns_result.scalars().all())
        messages = [
            MessageRecord(role=t.role, content=t.content, timestamp=t.created_at.isoformat())
            for t in turns
        ]
        first_user = next((t.content for t in turns if t.role == "user"), None)
        preview = (first_user[:120] + "…") if first_user and len(first_user) > 120 else first_user

        records.append(SessionRecord(
            session_id=s.session_id,
            started_at=s.started_at.isoformat(),
            ended_at=s.ended_at.isoformat() if s.ended_at else None,
            message_count=s.message_count or len(turns),
            preview=preview,
            messages=messages,
        ))

    return SessionListResponse(sessions=records)
