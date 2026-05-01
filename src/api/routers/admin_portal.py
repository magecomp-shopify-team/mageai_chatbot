import asyncio
import json
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.ai.registry import registry
from src.api.deps import get_db
from src.auth.audit import log_action
from src.auth.deps import require_cookie_session
from src.auth.models import AdminUser, AuditLog
from src.auth.service import (
    authenticate_admin,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from src.core.config import list_app_ids, load_app_config
from src.core.exceptions import AuthenticationError
from src.manager.meta_store import MetaStore
from src.pipeline.indexer import index_file

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="admin_ui/templates")


def _get_user_or_redirect(user_or_redirect):
    if isinstance(user_or_redirect, RedirectResponse):
        return None, user_or_redirect
    return user_or_redirect, None


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    totp_code: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await authenticate_admin(username, password, totp_code or None, db)
        access_token = create_access_token(user.username)
        await log_action(db, username, "auth.login", request=request)
        response = RedirectResponse(url="/admin/", status_code=302)
        response.set_cookie("access_token", access_token, httponly=True, samesite="lax")
        return response
    except AuthenticationError:
        await log_action(db, username, "auth.login_failed", success=False, request=request)
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid credentials"}, status_code=401
        )


@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("access_token")
    return response


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_cookie_session),
):
    if isinstance(user, RedirectResponse):
        return user

    provider_ids = registry.get_all_ids()
    health_tasks = [registry.get(pid).health_check() for pid in provider_ids]
    health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
    providers_health = [
        {"id": pid, "healthy": (r is True)}
        for pid, r in zip(provider_ids, health_results)
    ]

    app_ids = list_app_ids()
    meta = MetaStore()
    doc_counts = {}
    for app_id in app_ids:
        docs = await meta.list_docs(app_id)
        doc_counts[app_id] = len(docs)

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "providers_health": providers_health,
        "app_ids": app_ids,
        "doc_counts": doc_counts,
    })


# ── Upload ────────────────────────────────────────────────────────────────────

@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, user=Depends(require_cookie_session)):
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse(request, "upload.html", {
        "user": user, "app_ids": list_app_ids(), "result": None, "error": None,
    })


@router.post("/upload", response_class=HTMLResponse)
async def upload_submit(
    request: Request,
    app_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_cookie_session),
):
    if isinstance(user, RedirectResponse):
        return user

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".md", ".txt", ".pdf"):
        from fastapi.responses import HTMLResponse as _HR
        return templates.TemplateResponse(request, "upload.html", {
            "user": user,
            "app_ids": list_app_ids(),
            "result": None,
            "error": "Only .md, .txt, and .pdf files are supported.",
        })

    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        result = await index_file(tmp_path, app_id)
    finally:
        tmp_path.unlink(missing_ok=True)

    await log_action(db, user.username, "doc.upload", target=f"{app_id}/{file.filename}", request=request)
    return templates.TemplateResponse(request, "upload.html", {
        "user": user, "app_ids": list_app_ids(), "result": result, "error": None,
    })


# ── Library ───────────────────────────────────────────────────────────────────

@router.get("/library", response_class=HTMLResponse)
async def library_page(request: Request, user=Depends(require_cookie_session)):
    if isinstance(user, RedirectResponse):
        return user
    meta = MetaStore()
    all_docs = {}
    for app_id in list_app_ids():
        all_docs[app_id] = await meta.list_docs(app_id)
    return templates.TemplateResponse(request, "library.html", {
        "user": user, "all_docs": all_docs
    })


# ── Apps ──────────────────────────────────────────────────────────────────────

@router.get("/apps", response_class=HTMLResponse)
async def apps_page(request: Request, user=Depends(require_cookie_session)):
    if isinstance(user, RedirectResponse):
        return user
    apps = []
    for app_id in list_app_ids():
        try:
            cfg = load_app_config(app_id)
            apps.append({"app_id": app_id, "config": cfg})
        except Exception:
            pass
    provider_infos = []
    for pid in registry.get_all_ids():
        p = registry.get(pid)
        try:
            models = await p.list_models()
            default_model = models[0] if models else ""
        except Exception:
            models = []
            default_model = ""
        provider_infos.append({"id": pid, "name": p.display_name, "default_model": default_model, "models": models})
    token = request.cookies.get("access_token", "")
    return templates.TemplateResponse(request, "apps.html", {
        "user": user, "apps": apps, "providers": provider_infos, "access_token": token,
    })


# ── Providers ─────────────────────────────────────────────────────────────────

@router.get("/providers", response_class=HTMLResponse)
async def providers_page(request: Request, user=Depends(require_cookie_session)):
    if isinstance(user, RedirectResponse):
        return user
    provider_ids = registry.get_all_ids()
    health_tasks = [registry.get(pid).health_check() for pid in provider_ids]
    health_results = await asyncio.gather(*[
        asyncio.wait_for(t, timeout=10.0) for t in health_tasks
    ], return_exceptions=True)

    providers = []
    for pid, health in zip(provider_ids, health_results):
        p = registry.get(pid)
        if isinstance(health, Exception):
            logger.warning("Health check failed for provider %s: %s", pid, health)
        try:
            models = await p.list_models()
        except Exception:
            models = []
        providers.append({
            "id": pid,
            "name": p.display_name,
            "healthy": health is True,
            "models": models,
            "default_model": models[0] if models else "",
        })

    token = request.cookies.get("access_token", "")
    return templates.TemplateResponse(request, "providers.html", {
        "user": user, "providers": providers, "access_token": token,
    })


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions", response_class=HTMLResponse)
async def sessions_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_cookie_session),
):
    if isinstance(user, RedirectResponse):
        return user
    from src.pipeline.history import ConversationTurn
    result = await db.execute(
        select(ConversationTurn.session_id, ConversationTurn.app_id)
        .distinct()
        .order_by(ConversationTurn.session_id)
    )
    sessions = [{"session_id": r[0], "app_id": r[1]} for r in result.all()]
    return templates.TemplateResponse(request, "sessions.html", {
        "user": user, "sessions": sessions
    })


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/audit", response_class=HTMLResponse)
async def audit_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_cookie_session),
):
    if isinstance(user, RedirectResponse):
        return user

    PAGE_SIZE = 25
    page = max(1, int(request.query_params.get("page", 1)))
    action_filter = request.query_params.get("action", "")
    status_filter = request.query_params.get("status", "")

    query = select(AuditLog)
    count_query = select(func.count()).select_from(AuditLog)

    if action_filter:
        query = query.where(AuditLog.action.like(f"%{action_filter}%"))
        count_query = count_query.where(AuditLog.action.like(f"%{action_filter}%"))
    if status_filter in ("1", "0"):
        query = query.where(AuditLog.success == bool(int(status_filter)))
        count_query = count_query.where(AuditLog.success == bool(int(status_filter)))

    total = (await db.execute(count_query)).scalar_one()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)

    result = await db.execute(
        query.order_by(AuditLog.timestamp.desc())
             .offset((page - 1) * PAGE_SIZE)
             .limit(PAGE_SIZE)
    )
    logs = result.scalars().all()

    action_types_result = await db.execute(
        select(AuditLog.action).distinct().order_by(AuditLog.action)
    )
    action_types = [row[0] for row in action_types_result.all()]

    return templates.TemplateResponse(request, "audit.html", {
        "user": user,
        "logs": logs,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "page_size": PAGE_SIZE,
        "action_filter": action_filter,
        "status_filter": status_filter,
        "action_types": action_types,
    })


# ── Settings ──────────────────────────────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user=Depends(require_cookie_session)):
    if isinstance(user, RedirectResponse):
        return user
    from config.settings import settings as app_settings
    return templates.TemplateResponse(request, "settings.html", {
        "user": user, "settings": app_settings
    })


@router.post("/settings/password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_cookie_session),
):
    if isinstance(user, RedirectResponse):
        return user
    from src.auth.service import change_password as svc_change_password
    await svc_change_password(user, current_password, new_password, db)
    await log_action(db, user.username, "auth.change_password", request=request)
    return templates.TemplateResponse(request, "settings.html", {
        "user": user, "message": "Password changed successfully"
    })


# ── Analytics ─────────────────────────────────────────────────────────────────

async def _run(db: AsyncSession, sql: str, params: dict | None = None):
    result = await db.execute(text(sql), params or {})
    return result.fetchall()


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_cookie_session),
    date_range: str = Query(default="30", alias="range"),  # "7" | "30" | "90" | "all"
):
    if isinstance(user, RedirectResponse):
        return user

    # ── Date filter ───────────────────────────────────────────────────────────
    now = datetime.utcnow()
    if date_range == "7":
        since = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    elif date_range == "90":
        since = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    elif date_range == "all":
        since = "2000-01-01"
    else:
        date_range = "30"
        since = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    # ── Section 1: KPI cards ──────────────────────────────────────────────────
    (total_sessions,) = (await _run(db, "SELECT COUNT(*) FROM chat_sessions"))[0]
    (live_sessions,) = (await _run(db, "SELECT COUNT(*) FROM chat_sessions WHERE is_live = 1"))[0]
    (total_users,) = (await _run(db, "SELECT COUNT(*) FROM user_profiles"))[0]
    (total_messages,) = (await _run(
        db, "SELECT COUNT(*) FROM conversation_turns WHERE role = 'user'"))[0]
    (total_tokens,) = (await _run(
        db, "SELECT COALESCE(SUM(token_count), 0) FROM conversation_turns"))[0]
    (avg_messages,) = (await _run(
        db, "SELECT COALESCE(AVG(CAST(message_count AS FLOAT)), 0) FROM chat_sessions"))[0]

    # Average session duration (seconds) — use ended_at or closed_at
    dur_rows = await _run(db, """
        SELECT started_at,
               COALESCE(ended_at, closed_at) AS finished_at
        FROM chat_sessions
        WHERE started_at IS NOT NULL
          AND COALESCE(ended_at, closed_at) IS NOT NULL
    """)
    durations = []
    for row in dur_rows:
        try:
            start = datetime.fromisoformat(str(row[0]))
            end = datetime.fromisoformat(str(row[1]))
            diff = (end - start).total_seconds()
            if 0 <= diff < 86400:
                durations.append(diff)
        except Exception:
            pass
    avg_duration_sec = int(sum(durations) / len(durations)) if durations else 0
    avg_duration_fmt = f"{avg_duration_sec // 60}m {avg_duration_sec % 60}s"

    # ── Section 2: Sessions & messages over time ──────────────────────────────
    sessions_over_time = await _run(db, """
        SELECT DATE(started_at) AS day, COUNT(*) AS cnt
        FROM chat_sessions
        WHERE DATE(started_at) >= :since
        GROUP BY day
        ORDER BY day
    """, {"since": since})

    messages_over_time = await _run(db, """
        SELECT DATE(created_at) AS day, COUNT(*) AS cnt
        FROM conversation_turns
        WHERE role = 'user' AND DATE(created_at) >= :since
        GROUP BY day
        ORDER BY day
    """, {"since": since})

    # Merge into a unified day list
    sessions_map = {str(r[0]): r[1] for r in sessions_over_time}
    messages_map = {str(r[0]): r[1] for r in messages_over_time}
    all_days = sorted(set(list(sessions_map.keys()) + list(messages_map.keys())))
    timeline_labels = all_days
    timeline_sessions = [sessions_map.get(d, 0) for d in all_days]
    timeline_messages = [messages_map.get(d, 0) for d in all_days]

    # ── Section 3: Device & browser breakdown ─────────────────────────────────
    device_rows = await _run(db, """
        SELECT COALESCE(device_type, 'Unknown') AS dt, COUNT(*) AS cnt
        FROM chat_sessions
        GROUP BY dt ORDER BY cnt DESC
    """)
    browser_rows = await _run(db, """
        SELECT COALESCE(browser, 'Unknown') AS br, COUNT(*) AS cnt
        FROM chat_sessions
        GROUP BY br ORDER BY cnt DESC
    """)

    # ── Section 4: Token usage per app per day ────────────────────────────────
    token_rows = await _run(db, """
        SELECT app_id, DATE(created_at) AS day, SUM(token_count) AS total
        FROM conversation_turns
        WHERE DATE(created_at) >= :since
        GROUP BY app_id, day
        ORDER BY day, app_id
    """, {"since": since})

    # Build per-app datasets for stacked bar chart
    token_apps: dict[str, dict[str, int]] = {}
    token_days_set: set[str] = set()
    for app_id, day, total in token_rows:
        day = str(day)
        token_days_set.add(day)
        token_apps.setdefault(app_id, {})[day] = int(total or 0)
    token_days = sorted(token_days_set)

    token_chart_datasets = []
    colors = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7", "#f97316"]
    for i, (app_id, day_map) in enumerate(token_apps.items()):
        token_chart_datasets.append({
            "label": app_id,
            "data": [day_map.get(d, 0) for d in token_days],
            "backgroundColor": colors[i % len(colors)],
        })

    # Per-app summary table
    token_summary = await _run(db, """
        SELECT
            ct.app_id,
            COALESCE(SUM(ct.token_count), 0) AS total_tokens,
            COUNT(*) AS total_turns,
            COALESCE(AVG(CAST(ct.token_count AS FLOAT)), 0) AS avg_tokens_per_turn,
            COALESCE(AVG(cs_agg.session_tokens), 0) AS avg_tokens_per_session
        FROM conversation_turns ct
        LEFT JOIN (
            SELECT session_id, app_id, SUM(token_count) AS session_tokens
            FROM conversation_turns
            GROUP BY session_id, app_id
        ) cs_agg ON ct.session_id = cs_agg.session_id AND ct.app_id = cs_agg.app_id
        GROUP BY ct.app_id
        ORDER BY total_tokens DESC
    """)

    # ── Section 5: Session reviews ────────────────────────────────────────────
    rating_rows = await _run(db, """
        SELECT rating, COUNT(*) AS cnt
        FROM session_reviews
        GROUP BY rating
        ORDER BY rating
    """)
    rating_map = {r: c for r, c in rating_rows}
    emoji_map = {1: "😡 Very Bad", 2: "😞 Bad", 3: "😐 Normal", 4: "😊 Good", 5: "😍 Very Good"}
    rating_labels = [emoji_map[i] for i in range(1, 6)]
    rating_counts = [rating_map.get(i, 0) for i in range(1, 6)]

    avg_rating_row = await _run(db, "SELECT AVG(CAST(rating AS FLOAT)), COUNT(*) FROM session_reviews")
    avg_rating = round(avg_rating_row[0][0] or 0, 2)
    total_reviews = avg_rating_row[0][1]

    avg_emoji = emoji_map.get(round(avg_rating) if avg_rating else 0, "—")

    recent_reviews = await _run(db, """
        SELECT session_id, emoji_label, rating, created_at, comment
        FROM session_reviews
        ORDER BY created_at DESC
        LIMIT 20
    """)

    # ── Section 6: Top entry/exit URLs ───────────────────────────────────────
    top_entry_urls = await _run(db, """
        SELECT COALESCE(entry_url, '(none)') AS url, COUNT(*) AS cnt
        FROM chat_sessions
        WHERE entry_url IS NOT NULL
        GROUP BY url ORDER BY cnt DESC LIMIT 10
    """)
    top_exit_urls = await _run(db, """
        SELECT COALESCE(exit_url, '(none)') AS url, COUNT(*) AS cnt
        FROM chat_sessions
        WHERE exit_url IS NOT NULL
        GROUP BY url ORDER BY cnt DESC LIMIT 10
    """)

    # ── Section 7: IP activity ────────────────────────────────────────────────
    ip_rows = await _run(db, """
        SELECT
            cs.ip_address,
            COUNT(*) AS session_cnt,
            MAX(cs.last_active_at) AS last_seen,
            GROUP_CONCAT(DISTINCT cs.app_id) AS apps
        FROM chat_sessions cs
        WHERE cs.ip_address IS NOT NULL
        GROUP BY cs.ip_address
        ORDER BY session_cnt DESC
        LIMIT 50
    """)

    ip_table = []
    for ip, cnt, last_seen, apps in ip_rows:
        # Check audit_log too
        audit_hit = await _run(db,
            "SELECT COUNT(*) FROM audit_log WHERE ip_address = :ip", {"ip": ip})
        audit_cnt = audit_hit[0][0] if audit_hit else 0
        ip_table.append({
            "ip": ip,
            "session_cnt": cnt,
            "last_seen": last_seen,
            "apps": apps or "",
            "audit_cnt": audit_cnt,
            "high_freq": cnt > 20,
        })

    # ── Section 8: Audit log (paginated via query param) ─────────────────────
    audit_page = int(request.query_params.get("audit_page", 1))
    audit_page = max(1, audit_page)
    audit_action_filter = request.query_params.get("audit_action", "")
    audit_success_filter = request.query_params.get("audit_success", "")

    audit_where = "WHERE 1=1"
    audit_params: dict = {}
    if audit_action_filter:
        audit_where += " AND action LIKE :action"
        audit_params["action"] = f"%{audit_action_filter}%"
    if audit_success_filter in ("1", "0"):
        audit_where += " AND success = :success"
        audit_params["success"] = int(audit_success_filter)

    (audit_total,) = (await _run(db, f"SELECT COUNT(*) FROM audit_log {audit_where}", audit_params))[0]
    audit_offset = (audit_page - 1) * 20
    audit_params["limit"] = 20
    audit_params["offset"] = audit_offset
    audit_rows = await _run(db, f"""
        SELECT timestamp, username, action, target, ip_address, success
        FROM audit_log {audit_where}
        ORDER BY timestamp DESC
        LIMIT :limit OFFSET :offset
    """, audit_params)
    audit_pages = max(1, (audit_total + 19) // 20)

    # Distinct action types for filter dropdown
    action_types = await _run(db, "SELECT DISTINCT action FROM audit_log ORDER BY action")

    # ── Section 9: Recent sessions table ─────────────────────────────────────
    sessions_page = int(request.query_params.get("sess_page", 1))
    sessions_page = max(1, sessions_page)
    sess_offset = (sessions_page - 1) * 50

    recent_sessions = await _run(db, """
        SELECT
            cs.session_id,
            cs.app_id,
            up.name AS user_name,
            cs.started_at,
            cs.message_count,
            cs.device_type,
            cs.browser,
            cs.is_live,
            sr.rating,
            sr.emoji_label,
            sr.comment
        FROM chat_sessions cs
        LEFT JOIN user_profiles up ON cs.user_id = up.id
        LEFT JOIN session_reviews sr ON cs.session_id = sr.session_id AND cs.app_id = sr.app_id
        ORDER BY cs.started_at DESC
        LIMIT 50 OFFSET :offset
    """, {"offset": sess_offset})

    (sess_total,) = (await _run(db, "SELECT COUNT(*) FROM chat_sessions"))[0]
    sess_pages = max(1, (sess_total + 49) // 50)

    return templates.TemplateResponse(request, "analytics.html", {
        "user": user,
        "date_range": date_range,
        # KPIs
        "total_sessions": total_sessions,
        "live_sessions": live_sessions,
        "total_users": total_users,
        "total_messages": total_messages,
        "total_tokens": total_tokens,
        "avg_messages": round(avg_messages, 1),
        "avg_duration": avg_duration_fmt,
        # Timeline chart
        "timeline_labels": json.dumps(timeline_labels),
        "timeline_sessions": json.dumps(timeline_sessions),
        "timeline_messages": json.dumps(timeline_messages),
        # Device/browser
        "device_labels": json.dumps([r[0] for r in device_rows]),
        "device_counts": json.dumps([r[1] for r in device_rows]),
        "browser_labels": json.dumps([r[0] for r in browser_rows]),
        "browser_counts": json.dumps([r[1] for r in browser_rows]),
        # Token usage
        "token_days": json.dumps(token_days),
        "token_chart_datasets": json.dumps(token_chart_datasets),
        "token_summary": token_summary,
        # Reviews
        "rating_labels": json.dumps(rating_labels),
        "rating_counts": json.dumps(rating_counts),
        "avg_rating": avg_rating,
        "avg_emoji": avg_emoji,
        "total_reviews": total_reviews,
        "recent_reviews": recent_reviews,
        # URLs
        "top_entry_urls": top_entry_urls,
        "top_exit_urls": top_exit_urls,
        # IP table
        "ip_table": ip_table,
        # Audit log
        "audit_rows": audit_rows,
        "audit_page": audit_page,
        "audit_pages": audit_pages,
        "audit_total": audit_total,
        "audit_action_filter": audit_action_filter,
        "audit_success_filter": audit_success_filter,
        "action_types": [r[0] for r in action_types],
        # Recent sessions
        "recent_sessions": recent_sessions,
        "sessions_page": sessions_page,
        "sess_pages": sess_pages,
        "sess_total": sess_total,
    })


@router.get("/analytics/session-turns")
async def analytics_session_turns(
    request: Request,
    session_id: str = Query(...),
    app_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_cookie_session),
):
    if isinstance(user, RedirectResponse):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    rows = await _run(db, """
        SELECT role, content, token_count, created_at
        FROM conversation_turns
        WHERE session_id = :sid AND app_id = :app_id
        ORDER BY created_at ASC
    """, {"sid": session_id, "app_id": app_id})
    turns = [
        {"role": r[0], "content": r[1], "token_count": r[2], "created_at": str(r[3])}
        for r in rows
    ]
    return JSONResponse({"turns": turns})
