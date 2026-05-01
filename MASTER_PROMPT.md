# Master Claude Code Prompt
# Multi-App RAG Chatbot — Multi-Provider AI + Master Admin Portal
# Copy this entire prompt into Claude Code to scaffold the full project from zero.

---

You are a senior Python backend engineer with 10+ years of production experience in
LLM systems, multi-provider AI integration, vector databases, FastAPI, async Python,
and web application security. You write clean, typed, testable, production-grade code.
You never cut corners on error handling, logging, separation of concerns, or security.

## Your task

Build a complete **multi-app RAG-powered chatbot backend** with:
1. **Multi-provider AI routing** — Anthropic, OpenAI, Google Gemini, DeepSeek, Mistral,
   Cohere, Groq, Ollama, and any OpenAI-compatible endpoint — each app picks its own
   provider and model via YAML config.
2. **Secure master admin portal** — Jinja2 HTML, JWT + bcrypt auth, drag-drop document
   upload, knowledge base management, provider health dashboard, full audit log.
3. **Provider-agnostic architecture** — zero changes outside `src/ai/` to add a new provider.

Follow `CLAUDE.md` exactly for all rules, module contracts, naming, and anti-patterns.

---

## Phase 0 — Python virtual environment setup

Before creating any files, set up an isolated Python virtual environment:

```bash
# 1. Create venv (requires Python 3.11+)
python3.11 -m venv .venv

# 2. Activate venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows (PowerShell)

# 3. Upgrade pip + core build tools
pip install --upgrade pip setuptools wheel

# 4. Install the project in editable mode (picks up pyproject.toml deps)
pip install -e ".[dev]"

# 5. Verify
python --version          # must be 3.11+
pip list | grep fastapi   # should show fastapi
```

> **Rule**: Never install packages globally. All commands in subsequent phases
> assume the venv is active. Add `.venv/` to `.gitignore`.

---

## Phase 1 — Project scaffold

Create the complete directory structure from `CLAUDE.md`. Then:

### `pyproject.toml`
```toml
[project]
name = "chatbot-backend"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
  # Web framework
  "fastapi>=0.111",
  "uvicorn[standard]",
  "python-multipart",
  "jinja2",
  "aiofiles",
  "itsdangerous",

  # AI providers
  "anthropic>=0.49",             # Anthropic Claude
  "openai>=1.30",                # OpenAI + DeepSeek + Groq + OpenAI-compat
  "google-generativeai>=0.8",    # Google Gemini
  "mistralai>=1.0",              # Mistral AI
  "cohere>=5.0",                 # Cohere
  "groq>=0.9",                   # Groq (also uses openai SDK internally)
  "httpx>=0.27",                 # Ollama HTTP calls + general async HTTP

  # Vector DB + Embedding
  "chromadb>=0.5",
  "sentence-transformers>=3.0",

  # Database
  "sqlalchemy>=2.0",
  "aiosqlite",
  "alembic",

  # Config + validation
  "pydantic>=2.0",
  "pydantic-settings",
  "pyyaml",

  # Token counting
  "tiktoken",

  # Auth + security
  "python-jose[cryptography]",
  "passlib[bcrypt]",
  "pyotp",
  "cryptography",
  "slowapi",
  "qrcode[pil]",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio", "httpx", "anyio"]
```

### `.env.example`
Include all variables from `CLAUDE.md` environment variables section exactly.

### `config/settings.py`
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AI providers — all optional, provider disabled if key missing/empty
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    COHERE_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # OpenAI-compatible extras
    TOGETHER_API_KEY: str = ""
    PERPLEXITY_API_KEY: str = ""
    FIREWORKS_API_KEY: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""

    # System defaults
    DEFAULT_PROVIDER: str = "anthropic"
    DEFAULT_MODEL: str = "claude-haiku-4-5-20251001"

    # Storage
    STORAGE_ROOT: Path = Path("./storage/files")
    CHROMA_PATH: Path = Path("./storage/chroma_db")
    META_DB_PATH: Path = Path("./storage/meta.json")
    HISTORY_DB_URL: str = "sqlite+aiosqlite:///./storage/app.db"

    # Embedding
    EMBED_MODEL: str = "all-MiniLM-L6-v2"
    EMBED_BATCH_SIZE: int = 64

    # Token budgets
    DEFAULT_MAX_HISTORY_TOKENS: int = 800
    DEFAULT_MAX_RAG_TOKENS: int = 1200
    DEFAULT_MAX_SYSTEM_TOKENS: int = 600

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Master admin auth
    MASTER_ADMIN_USERNAME: str = "master_admin"
    MASTER_ADMIN_PASSWORD_HASH: str = ""
    AUTH_SECRET_KEY: str = ""
    AUTH_ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    AUTH_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_TOTP_ENABLED: bool = False
    ADMIN_TOTP_ENCRYPTION_KEY: str = ""
    CSRF_SECRET_KEY: str = ""
    RATE_LIMIT_LOGIN: str = "5/15minute"

settings = Settings()
```

---

## Phase 2 — Core infrastructure

### `src/core/exceptions.py`
Full exception hierarchy from `CLAUDE.md` — ALL exceptions with docstrings:
```python
class ChatbotError(Exception): ...

# Provider
class ProviderNotFoundError(ChatbotError): ...
class ProviderAuthError(ChatbotError): ...
class ProviderRateLimitError(ChatbotError): ...
class ProviderTimeoutError(ChatbotError): ...
class ProviderUnavailableError(ChatbotError): ...
class ModelNotFoundError(ChatbotError): ...

# App
class AppNotFoundError(ChatbotError): ...
class DocumentNotFoundError(ChatbotError): ...
class EmbedFailedError(ChatbotError): ...
class TokenBudgetExceededError(ChatbotError): ...
class HistoryCompressionError(ChatbotError): ...

# Auth
class AuthenticationError(ChatbotError): ...
class InsufficientPermissionsError(ChatbotError): ...
```

### `src/core/embedder.py`
- Singleton `SentenceTransformer` via `lru_cache`
- `encode(texts: list[str]) -> list[list[float]]` — always batch
- Log model load time at INFO on first call

### `src/core/chroma.py`
- Singleton `chromadb.PersistentClient` via `lru_cache`
- `get_or_create_collection(app_id: str) -> Collection` — always `{app_id}_app`
- `collection_exists(app_id: str) -> bool`

### `src/core/tokenizer.py`
- `count_tokens(text: str) -> int` — tiktoken `cl100k_base`
- `truncate_to_tokens(text: str, max_tokens: int) -> str`

### `src/core/config.py`
- `load_app_config(app_id: str) -> AppConfig`
- `reload_app_config(app_id: str) -> AppConfig`
- `list_app_ids() -> list[str]`
- `AppConfig` pydantic model includes `provider: str` and `model: str` fields

---

## Phase 3 — Multi-provider AI layer (build before anything calls AI)

This is the architectural core. Build it completely before pipeline or API layers.

### `src/ai/base.py`
Implement the `AIProvider` abstract base class and `NormalisedResponse` pydantic model
exactly as specified in `CLAUDE.md` module contracts. Every concrete provider must
implement ALL four abstract methods: `complete`, `list_models`, `health_check`, `count_tokens`.

### `src/ai/normaliser.py`
One function per provider that converts the provider's raw response object into
`NormalisedResponse`. Extract: `text`, `input_tokens`, `output_tokens`, `model`,
`finish_reason`, and store the full raw response in `raw`.

```python
def normalise_anthropic(response) -> NormalisedResponse:
    return NormalisedResponse(
        text=response.content[0].text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=response.model,
        provider="anthropic",
        finish_reason=response.stop_reason or "stop",
        raw=response.model_dump(),
    )

def normalise_openai(response) -> NormalisedResponse:
    choice = response.choices[0]
    return NormalisedResponse(
        text=choice.message.content or "",
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        model=response.model,
        provider="openai",
        finish_reason=choice.finish_reason or "stop",
        raw=response.model_dump(),
    )

# normalise_gemini, normalise_mistral, normalise_cohere, normalise_groq, normalise_ollama
# follow the same pattern — extract tokens and text from provider-specific response shapes
```

### `src/ai/providers/` — all 8 provider files
Implement every provider exactly as specified in `CLAUDE.md` provider implementations section.
Critical rules for every provider:
- Constructor creates the SDK client once — stored as `self._client`
- Wrap ALL SDK calls in try/except:
  - HTTP 401/403 → raise `ProviderAuthError`
  - HTTP 429 → raise `ProviderRateLimitError`
  - Timeout → raise `ProviderTimeoutError`
  - Connection error / 5xx → raise `ProviderUnavailableError`
  - Model not found → raise `ModelNotFoundError`
- Streaming: use `async for` with `yield` — implement as async generator
- Non-streaming: return `NormalisedResponse` (via normaliser function)
- Log at DEBUG: provider, model, input tokens, latency

### `src/ai/registry.py`
```python
import logging
from functools import lru_cache
from src.ai.base import AIProvider

logger = logging.getLogger(__name__)

class ProviderInfo(BaseModel):
    provider_id: str
    display_name: str
    available: bool          # API key present
    default_model: str
    models: list[str]

class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, AIProvider] = {}

    def register(self, provider: AIProvider) -> None:
        self._providers[provider.provider_id] = provider
        logger.info("Registered AI provider: %s", provider.provider_id)

    def get(self, provider_id: str) -> AIProvider:
        if provider_id not in self._providers:
            raise ProviderNotFoundError(f"Unknown provider: {provider_id}")
        return self._providers[provider_id]

    def is_available(self, provider_id: str) -> bool:
        """Provider registered AND API key non-empty."""
        ...

    def list_providers(self) -> list[ProviderInfo]:
        ...

    def get_all_ids(self) -> list[str]:
        return list(self._providers.keys())

# Module-level singleton
registry = ProviderRegistry()

def init_registry() -> None:
    """
    Called once on startup. Register all providers whose API key is non-empty.
    Order: Anthropic, OpenAI, Gemini, DeepSeek, Mistral, Cohere, Groq, Ollama.
    Also load any openai_compat providers from config/providers/*.yaml where type=openai_compat.
    """
    from src.ai.providers.anthropic_provider import AnthropicProvider
    # ... import and conditionally register each provider
    if settings.ANTHROPIC_API_KEY:
        registry.register(AnthropicProvider())
    if settings.OPENAI_API_KEY:
        registry.register(OpenAIProvider())
    # ... etc for all providers
    # Ollama: always register — health_check determines availability
    registry.register(OllamaProvider())
    logger.info("Provider registry initialised. Available: %s", registry.get_all_ids())
```

### `src/ai/router.py`
```python
async def resolve_provider(app_id: str, override_provider: str | None = None) -> AIProvider:
    """
    Resolution order:
    1. override_provider if provided AND caller is admin (passed from chat router)
    2. app config provider field
    3. settings.DEFAULT_PROVIDER
    4. First available provider
    Raise ProviderUnavailableError if nothing works.
    Log which provider was resolved and why.
    """

async def complete(
    context: AssembledContext,
    app_id: str,
    override_provider: str | None = None,
    stream: bool = False,
) -> NormalisedResponse | AsyncIterator[str]:
    """
    Single entry point for all AI completions.
    1. resolve_provider()
    2. Load app config for model + max_tokens + temperature
    3. provider.complete(context.system_prompt, context.messages, model, ...)
    4. On ProviderRateLimitError: log and re-raise (do NOT silently retry)
    5. Log: provider, model, token usage, latency
    """
```

---

## Phase 4 — Auth system

### `src/auth/models.py`
Two SQLAlchemy models: `AdminUser` and `AuditLog` — exactly as in `CLAUDE.md`.
`AuditLog` is append-only — no update or delete methods anywhere.

### `src/auth/service.py`
Implement all functions from `CLAUDE.md` auth service contracts:
- `authenticate_admin` — bcrypt verify + TOTP + timing attack prevention
- `create_access_token` / `create_refresh_token` — JWT HS256
- `verify_token` — decode + validate type field
- `change_password` — verify current, hash new, min length 12
- `encrypt_totp_secret` / `decrypt_totp_secret` — Fernet
- `generate_totp_qr_code` — base64 PNG

### `src/auth/deps.py`
- `get_current_admin` — Bearer token → JWT decode → DB load
- `require_cookie_session` — cookie → JWT decode → DB load → redirect on failure
- `get_client_ip` — X-Forwarded-For first, then client.host

### `src/auth/audit.py`
- `log_action` — never raises, JSON-serialises detail, extracts IP + UA from request
- Audit action names from `CLAUDE.md` catalogue — add `provider.test`, `provider.enable`,
  `provider.set_default` to the catalogue

---

## Phase 5 — Pipeline layer

### `src/pipeline/chunker.py`
- `chunk_text(text, chunk_size=450, overlap=50) -> list[str]`
  Split on word boundaries. Overlap = last N words of chunk N repeated at start of chunk N+1.
  Filter chunks < 20 words.
- `estimate_tokens(text) -> int` — word count × 1.3

### `src/pipeline/indexer.py`
`index_file(file_path, app_id, chunk_size=450, force=False) -> IndexResult`:
1. Read file (.md or .txt — raise ValueError otherwise)
2. MD5 hash
3. Check meta.json — skip if hash unchanged + not force
4. chunk_text()
5. Batch encode
6. Delete existing ChromaDB chunks for this file (where source_file=filename)
7. Upsert new chunks: metadata = {source_file, app_id, chunk_index, total_chunks, indexed_at}
8. Copy raw file to storage/files/{app_id}/
9. Upsert meta.json
10. Return IndexResult

### `src/pipeline/retriever.py`
`retrieve(query, app_id, top_k=4, min_relevance=0.0) -> list[Chunk]`:
1. Encode query as list of 1, take [0]
2. Query collection (n_results = top_k + 2)
3. Filter by distance threshold
4. Return top_k, return [] if collection missing

### `src/pipeline/history.py`
DB schema (in shared `app.db`):
```sql
CREATE TABLE conversation_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    app_id TEXT NOT NULL,
    role TEXT CHECK(role IN ('user','assistant')) NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_session_app ON conversation_turns(session_id, app_id, created_at);
```
- `save_turn` — count tokens, insert
- `get_history` — sliding window + compress on overflow
- `compress_history` — use the app's configured provider/model for compression,
  fallback to DEFAULT_PROVIDER. System: "Summarise in 2-3 sentences. Output only summary."
  max_tokens=150.
- `clear_session`

### `src/pipeline/assembler.py`
`assemble(user_message, session_id, app_id) -> AssembledContext`:
1. Load app config
2. Build system prompt: role + tone + rules
3. Retrieve RAG chunks
4. Get history
5. Count tokens using provider's `count_tokens()` method for the app's configured provider
6. Enforce budget (compress history → trim RAG → never truncate user)
7. Return AssembledContext with token_breakdown

---

## Phase 6 — Document manager

### `src/manager/meta_store.py`
Thread-safe asyncio.Lock around meta.json:
- `get_doc`, `upsert_doc`, `remove_doc`, `list_docs`

### `src/manager/doc_manager.py`
- `remove_document` — delete ChromaDB chunks + stored file + meta.json entry
- `remove_chunks` — delete specific chunk IDs from ChromaDB
- `wipe_and_reindex_app` — delete collection, re-index all stored files with force=True
- `delete_app_data` — delete collection + files directory + all meta entries

Log at WARNING before every destructive op.

---

## Phase 7 — FastAPI app factory

### `src/api/main.py`
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Multi-App Chatbot API", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.mount("/static", StaticFiles(directory="admin_ui/static"), name="static")

# Public routers
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(health_router, tags=["health"])
app.include_router(apps_read_router, prefix="/apps", tags=["apps"])
app.include_router(docs_read_router, prefix="/docs", tags=["docs"])
app.include_router(providers_public_router, prefix="/providers", tags=["providers"])

# Admin API (JWT)
app.include_router(docs_admin_router, prefix="/docs", tags=["admin-docs"])
app.include_router(chunks_admin_router, prefix="/chunks", tags=["admin-chunks"])
app.include_router(apps_admin_router, prefix="/apps", tags=["admin-apps"])
app.include_router(providers_admin_router, prefix="/providers", tags=["admin-providers"])
app.include_router(audit_router, prefix="/audit", tags=["audit"])

# Admin portal (cookie + Jinja2)
app.include_router(admin_portal_router, prefix="/admin", tags=["portal"])

# Exception handlers — map ALL domain exceptions from CLAUDE.md
@app.exception_handler(ProviderAuthError)
async def provider_auth(req, exc): return JSONResponse(401, {"error": str(exc)})

@app.exception_handler(ProviderRateLimitError)
async def provider_rate(req, exc): return JSONResponse(429, {"error": str(exc)})

@app.exception_handler(ProviderTimeoutError)
async def provider_timeout(req, exc): return JSONResponse(504, {"error": str(exc)})

@app.exception_handler(ProviderUnavailableError)
async def provider_unavail(req, exc): return JSONResponse(503, {"error": str(exc)})

@app.exception_handler(ModelNotFoundError)
async def model_not_found(req, exc): return JSONResponse(422, {"error": str(exc)})

@app.exception_handler(AppNotFoundError)
async def app_not_found(req, exc): return JSONResponse(404, {"error": str(exc)})

@app.exception_handler(DocumentNotFoundError)
async def doc_not_found(req, exc): return JSONResponse(404, {"error": str(exc)})

@app.exception_handler(AuthenticationError)
async def auth_err(req, exc): return JSONResponse(401, {"error": "Authentication required"})

@app.on_event("startup")
async def startup():
    settings.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    settings.CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    await init_db()
    await ensure_admin()
    init_registry()       # ← register all AI providers
    get_embedder()        # warm embedding model
    logger.info("Chatbot API started. Providers: %s", registry.get_all_ids())
```

---

## Phase 8 — Chat router

### `src/api/routers/chat.py`
```python
class ChatRequest(BaseModel):
    app_id: str
    session_id: str
    message: str
    stream: bool = False
    provider_override: str | None = None   # admin-only field, ignored for non-admin callers

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    provider_used: str
    model_used: str
    token_usage: dict[str, int]   # {"input": N, "output": N}

@router.post("/", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request, db: AsyncSession = Depends(get_db)):
    config = load_app_config(body.app_id)   # raises AppNotFoundError → 404
    context = await assemble(body.message, body.session_id, body.app_id)

    if body.stream:
        async def event_stream():
            full_text = ""
            async for chunk in ai_router.complete(context, body.app_id, stream=True):
                full_text += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            await save_turn(body.session_id, body.app_id, "user", body.message)
            await save_turn(body.session_id, body.app_id, "assistant", full_text)
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    result = await ai_router.complete(context, body.app_id)
    await save_turn(body.session_id, body.app_id, "user", body.message)
    await save_turn(body.session_id, body.app_id, "assistant", result.text)
    return ChatResponse(
        reply=result.text, session_id=body.session_id,
        provider_used=result.provider, model_used=result.model,
        token_usage={"input": result.input_tokens, "output": result.output_tokens}
    )
```

---

## Phase 9 — Provider admin routes

### `src/api/routers/providers.py`

Public:
```python
GET /providers/
  → return registry.list_providers() — id, name, available, default_model, models

GET /providers/{id}/models
  → return provider.list_models()
```

Admin (JWT required):
```python
GET /providers/{id}/health
  → return {"provider": id, "healthy": await provider.health_check(), "latency_ms": N}

POST /providers/{id}/test
  Body: { message: str, model: str | None }
  → call provider.complete() with test message, return NormalisedResponse + latency
  → log_action(action="provider.test", target=id)

POST /providers/{id}/enable
  Body: { enabled: bool }
  → update provider config YAML enabled field
  → log_action(action="provider.enable")

PUT /providers/{id}/default
  → write DEFAULT_PROVIDER to settings (persist to .env)
  → log_action(action="provider.set_default")
```

---

## Phase 10 — Admin portal routes + templates

### `src/api/routers/admin_portal.py`
All routes at prefix `/admin`. Cookie session via `require_cookie_session`.

Implement all routes from `CLAUDE.md` Phase 10 (login, logout, dashboard, upload,
library, chunks, apps, sessions, audit, settings).

Add one new route:
```python
GET /admin/providers
  → load registry.list_providers()
  → for each: run health_check() concurrently (asyncio.gather, timeout=3s)
  → render providers.html with health results
```

### `admin_ui/templates/providers.html`
Provider management page. Extends base.html. Shows:
- Grid of provider cards, one per registered provider
- Each card: provider logo initial, name, status badge (healthy/unavailable/disabled)
- Latency badge (ms from health check)
- Default model shown
- Model dropdown selector (populated from list_models)
- "Test" button → POST /providers/{id}/test → show response in modal
- "Set as default" button
- "Enable / Disable" toggle
- API key status: "configured" (green) or "missing" (red) — never show the actual key

### `admin_ui/templates/apps.html`
Update the "Create app" form to include:
- Provider dropdown: dynamically populated from `/providers/` (available ones only)
- Model input field: pre-filled when provider selected (from list_models)
- Temperature slider: 0.0 – 1.0, default 0.7

### `admin_ui/templates/dashboard.html`
Add a "Provider health" section below the stats row:
- Horizontal row of small status chips: "Anthropic ●", "OpenAI ●", "Gemini ●", etc.
- Green dot = healthy, red = unavailable, gray = disabled/no key

---

## Phase 11 — Provider YAML configs

Create one YAML per provider in `config/providers/`:

**`config/providers/anthropic.yaml`**:
```yaml
provider_id: anthropic
display_name: Anthropic Claude
enabled: true
api_key_env: ANTHROPIC_API_KEY
base_url: null
default_model: claude-haiku-4-5-20251001
available_models:
  - claude-haiku-4-5-20251001
  - claude-sonnet-4-5
  - claude-opus-4-5
  - claude-sonnet-4-6
  - claude-opus-4-6
max_tokens_limit: 8192
default_temperature: 0.7
timeout_seconds: 60
```

**`config/providers/openai.yaml`**:
```yaml
provider_id: openai
display_name: OpenAI
enabled: true
api_key_env: OPENAI_API_KEY
base_url: null
default_model: gpt-4o-mini
available_models:
  - gpt-4o
  - gpt-4o-mini
  - o1
  - o1-mini
  - o3-mini
max_tokens_limit: 16384
default_temperature: 0.7
timeout_seconds: 60
```

**`config/providers/gemini.yaml`**:
```yaml
provider_id: gemini
display_name: Google Gemini
enabled: true
api_key_env: GEMINI_API_KEY
base_url: null
default_model: gemini-2.0-flash
available_models:
  - gemini-2.5-pro
  - gemini-2.5-flash
  - gemini-2.0-flash
  - gemini-2.0-flash-lite
  - gemini-1.5-pro
  - gemini-1.5-flash
max_tokens_limit: 8192
default_temperature: 0.7
timeout_seconds: 90
```

**`config/providers/deepseek.yaml`**:
```yaml
provider_id: deepseek
display_name: DeepSeek
enabled: true
api_key_env: DEEPSEEK_API_KEY
base_url: https://api.deepseek.com/v1
default_model: deepseek-chat
available_models:
  - deepseek-chat
  - deepseek-reasoner
max_tokens_limit: 8192
default_temperature: 0.7
timeout_seconds: 90
```

**`config/providers/mistral.yaml`**:
```yaml
provider_id: mistral
display_name: Mistral AI
enabled: true
api_key_env: MISTRAL_API_KEY
base_url: null
default_model: mistral-small-latest
available_models:
  - mistral-large-latest
  - mistral-medium-latest
  - mistral-small-latest
  - codestral-latest
  - open-mixtral-8x7b
max_tokens_limit: 8192
default_temperature: 0.7
timeout_seconds: 60
```

**`config/providers/cohere.yaml`**:
```yaml
provider_id: cohere
display_name: Cohere
enabled: true
api_key_env: COHERE_API_KEY
base_url: null
default_model: command-r
available_models:
  - command-r-plus
  - command-r
  - command-light
max_tokens_limit: 4096
default_temperature: 0.7
timeout_seconds: 60
```

**`config/providers/groq.yaml`**:
```yaml
provider_id: groq
display_name: Groq
enabled: true
api_key_env: GROQ_API_KEY
base_url: null
default_model: llama-3.3-70b-versatile
available_models:
  - llama-3.3-70b-versatile
  - llama-3.1-8b-instant
  - mixtral-8x7b-32768
  - gemma2-9b-it
  - qwen-qwq-32b
max_tokens_limit: 8192
default_temperature: 0.7
timeout_seconds: 30
```

**`config/providers/ollama.yaml`**:
```yaml
provider_id: ollama
display_name: Ollama (Local)
enabled: true
api_key_env: null
base_url: http://localhost:11434
default_model: llama3.3
available_models:
  - llama3.3
  - mistral
  - phi4
  - qwen2.5
  - deepseek-r1
  - gemma3
max_tokens_limit: 4096
default_temperature: 0.7
timeout_seconds: 120
```

---

## Phase 12 — App configs with provider field

**`config/apps/ecommerce.yaml`**:
```yaml
name: "ShopBot"
role: "You are a helpful shopping assistant for our e-commerce store."
tone: "friendly, concise, solution-focused"
provider: anthropic
model: claude-haiku-4-5-20251001
rules:
  - "Never discuss competitor pricing"
  - "If product availability is unknown, say you will check"
  - "Always suggest related products when relevant"
max_history_turns: 8
max_chunk_tokens: 900
top_k_chunks: 5
min_relevance: 0.25
max_response_tokens: 512
temperature: 0.7
```

**`config/apps/support.yaml`**:
```yaml
name: "SupportBot"
role: "You are a technical support specialist. Diagnose issues systematically."
tone: "calm, precise, professional"
provider: openai
model: gpt-4o-mini
rules:
  - "Ask clarifying questions before suggesting solutions if issue is ambiguous"
  - "Number your steps clearly"
  - "If unsure, say so and offer to escalate"
max_history_turns: 10
max_chunk_tokens: 1000
top_k_chunks: 5
min_relevance: 0.3
max_response_tokens: 768
temperature: 0.4
```

**`config/apps/hr.yaml`**:
```yaml
name: "HRBot"
role: "You are an HR policy assistant. Explain documented policy only."
tone: "warm, clear, neutral"
provider: gemini
model: gemini-2.0-flash
rules:
  - "Only answer based on documented policies in knowledge base"
  - "For sensitive matters, recommend speaking to HR directly"
  - "Cite source document when answering policy questions"
max_history_turns: 6
max_chunk_tokens: 800
top_k_chunks: 4
min_relevance: 0.35
max_response_tokens: 512
temperature: 0.3
```

---

## Phase 13 — Scripts

### `scripts/create_admin.py`
Prompt for password (hidden), bcrypt hash it at cost 12, generate AUTH_SECRET_KEY
and CSRF_SECRET_KEY if missing, write all to .env.

### `scripts/test_provider.py`
```
Usage: python scripts/test_provider.py --provider deepseek --model deepseek-chat --message "Hello"
Sends one message, prints response, tokens, latency.
Useful for verifying API keys before deploying.
```

### `scripts/reindex_app.py`
```
Usage: python scripts/reindex_app.py --app-id ecommerce [--chunk-size 450]
```

### `scripts/bulk_import.py`
```
Usage: python scripts/bulk_import.py --app-id support --folder ./docs/support
```

### `scripts/inspect_chunks.py`
```
Usage: python scripts/inspect_chunks.py --app-id hr --file leave-policy.txt [--limit 5]
```

---

## Phase 14 — Tests

### `tests/test_ai/test_provider_factory.py`
```python
def test_registry_returns_correct_provider():
    registry.register(MockAnthropicProvider())
    p = registry.get("anthropic")
    assert p.provider_id == "anthropic"

def test_registry_raises_on_unknown():
    with pytest.raises(ProviderNotFoundError):
        registry.get("doesnotexist")

async def test_router_uses_app_config_provider():
    # App config has provider: gemini
    # Mock both Anthropic and Gemini providers
    # Verify Gemini.complete() was called, not Anthropic.complete()

async def test_router_falls_back_to_default():
    # App config has no provider field
    # DEFAULT_PROVIDER=anthropic
    # Verify Anthropic.complete() called
```

### `tests/test_ai/test_normaliser.py`
```python
def test_normalise_anthropic():
    raw = MockAnthropicResponse(text="hi", input=10, output=5)
    r = normalise_anthropic(raw)
    assert r.text == "hi"
    assert r.input_tokens == 10
    assert r.provider == "anthropic"

# Same pattern for normalise_openai, normalise_gemini, normalise_deepseek, etc.
```

### `tests/test_ai/test_anthropic_provider.py`
```python
async def test_complete_returns_normalised(mock_anthropic_client):
    provider = AnthropicProvider()
    result = await provider.complete("sys", [{"role":"user","content":"hi"}], "claude-haiku-4-5-20251001")
    assert isinstance(result, NormalisedResponse)
    assert result.provider == "anthropic"

async def test_complete_maps_401_to_provider_auth_error(mock_anthropic_401):
    with pytest.raises(ProviderAuthError):
        await AnthropicProvider().complete(...)

async def test_complete_maps_429_to_provider_rate_limit(mock_anthropic_429):
    with pytest.raises(ProviderRateLimitError):
        await AnthropicProvider().complete(...)
```

### Write equivalent test files for `openai_provider`, `gemini_provider`, `deepseek_provider`.

### `tests/test_auth/test_login.py`
- Valid credentials → 200 + access_token
- Wrong password → 401, generic message, no field hint
- Rate limit: 6th attempt → 429
- Successful login writes audit_log `auth.login`
- Failed login writes audit_log `auth.login_failed`

### `tests/test_auth/test_jwt.py`
- Valid token → 200
- Expired token → 401
- Tampered signature → 401
- Refresh token used as access token → 401

### `tests/test_api/test_docs_auth.py`
Every admin route: test 401 (no token) AND 200 (valid token):
```python
@pytest.mark.parametrize("method,path", [
    ("POST", "/docs/upload"),
    ("DELETE", "/docs/ecommerce/test.md"),
    ("DELETE", "/docs/ecommerce"),
    ("POST", "/docs/ecommerce/reembed"),
    ("DELETE", "/chunks"),
    ("POST", "/apps/"),
    ("POST", "/apps/ecommerce/reload"),
    ("DELETE", "/apps/ecommerce"),
    ("GET", "/providers/anthropic/health"),
    ("POST", "/providers/anthropic/test"),
    ("PUT", "/providers/anthropic/default"),
    ("GET", "/audit"),
])
async def test_requires_auth(client, method, path):
    r = await client.request(method, path)
    assert r.status_code == 401
```

### `tests/test_chunker.py`, `test_retriever.py`, `test_assembler.py`, `test_history.py`
From previous phases — implement fully.

---

## Phase 15 — Final checklist

- [ ] `python scripts/create_admin.py` generates bcrypt hash + writes .env
- [ ] `python scripts/test_provider.py --provider anthropic --message "hi"` returns response
- [ ] `uvicorn src.api.main:app --reload` starts, logs which providers registered
- [ ] `GET /health` → 200
- [ ] `GET /providers/` → list of all registered providers
- [ ] `GET /admin/login` → login form renders
- [ ] Login with correct credentials → redirect to `/admin/`
- [ ] Login with wrong credentials → error message, same delay as success
- [ ] `POST /docs/upload` without token → 401
- [ ] `POST /docs/upload` with token → 200 + IndexResult
- [ ] Upload same file → old chunks removed, new indexed
- [ ] `/admin/providers` shows health status for all configured providers
- [ ] Change app YAML to `provider: deepseek` → next chat uses DeepSeek
- [ ] `ProviderRateLimitError` → 429 HTTP response
- [ ] `python -m pytest` passes with no failures
- [ ] No `import anthropic` (or any provider SDK) outside `src/ai/providers/`
- [ ] No `print()` in `src/`
- [ ] All public functions have type annotations
- [ ] Every admin route has 401 test + success test

---

## Absolute constraints — enforced always

1. Provider SDK imports ONLY in their respective provider file — nowhere else
2. `if provider_id == "anthropic":` logic NEVER appears outside `registry.py` or `router.py`
3. Anthropic/OpenAI/etc API keys NEVER logged, returned in responses, or stored in YAML
4. ChromaDB collections always `{app_id}_app`
5. Files stored at `storage/files/{app_id}/` — never flat
6. History always `(session_id, app_id)` — never session alone
7. `audit_log` has NO UPDATE or NO DELETE anywhere in the codebase
8. CSRF token validated on every HTML form POST
9. Auth failures: identical 401 response regardless of reason
10. `ai_router.complete()` is the ONLY place AI calls originate — never from routers directly

---

## Style guide

- Line length: 100 characters max
- Imports: stdlib → third-party → local, blank lines between groups
- Docstrings: Google-style for complex functions, one-line for simple
- f-strings only — no `.format()` or `%`
- No bare `except:` — always `except SpecificError as e:`
- `Path` objects for all file paths — never string concatenation or `os.path.join()`
- Provider errors caught at the provider class level, re-raised as domain exceptions
