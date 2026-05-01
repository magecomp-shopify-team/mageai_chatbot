# Multi-App RAG Chatbot — App Flow & API Guide

## Quick Start

```bash
# 1. Start the server
uvicorn src.api.main:app --reload

# 2. Create admin user
python scripts/create_admin.py

# 3. Open admin portal
open http://localhost:8000/admin/login
```

---

## System Architecture Flow

```
User Message
     │
     ▼
POST /chat/  ──► AppConfig lookup ──► ProviderRegistry.get(provider_id)
                                              │
                       ┌────────────────────────────────────┐
                       │         Pipeline                   │
                       │  1. History retrieval (SQLite)     │
                       │  2. RAG retrieval (ChromaDB)       │
                       │  3. Context assembly               │
                       │     (token budget enforcement)     │
                       └────────────────────────────────────┘
                                              │
                                              ▼
                                   AI Provider .complete()
                                   (Anthropic / OpenAI / etc.)
                                              │
                                              ▼
                                    NormalisedResponse
                                              │
                                              ▼
                                   Save to history → Return reply
```

---

## Complete App Lifecycle

### Step 1 — Create an App

```http
POST /apps/
Authorization: Bearer <token>
Content-Type: application/json

{
  "app_id": "support",
  "name": "Customer Support Bot",
  "role": "You are a helpful support agent for Acme Corp.",
  "tone": "friendly and professional",
  "rules": [
    "Always greet the customer by name if known",
    "Never promise refunds without manager approval"
  ],
  "provider": "anthropic",
  "model": "claude-haiku-4-5-20251001",
  "max_history_turns": 6,
  "max_chunk_tokens": 800,
  "top_k_chunks": 4,
  "min_relevance": 0.3,
  "max_response_tokens": 512,
  "temperature": 0.7
}
```

Creates `config/apps/support.yaml` on disk.

---

### Step 2 — Upload Documents

```http
POST /docs/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

app_id=support
file=@faq.md
```

Response:
```json
{
  "app_id": "support",
  "filename": "faq.md",
  "chunks_indexed": 38,
  "file_hash": "sha256:abc...",
  "skipped": false
}
```

`skipped: true` means the same file hash was already indexed — no reprocessing needed.

Only `.md` and `.txt` files are accepted.

---

### Step 3 — Chat

```http
POST /chat/
Content-Type: application/json

{
  "app_id": "support",
  "session_id": "user-xyz-session-1",
  "message": "What is your return policy?",
  "stream": false
}
```

Response:
```json
{
  "reply": "Our return policy allows returns within 30 days...",
  "session_id": "user-xyz-session-1",
  "token_usage": { "input": 310, "output": 92 }
}
```

**Session ID** is any string you choose — it persists conversation history for that user across requests.

---

### Step 4 — Streaming Chat

```http
POST /chat/
Accept: text/event-stream
Content-Type: application/json

{
  "app_id": "support",
  "session_id": "user-xyz-session-1",
  "message": "Explain your warranty",
  "stream": true
}
```

SSE event format:
```
data: {"chunk": "Our warranty covers"}
data: {"chunk": " all manufacturing defects"}
data: {"chunk": " for 2 years."}
data: {"done": true}
```

---

## Token Budget (enforced per request)

| Slot | Max Tokens | Priority |
|------|-----------|----------|
| System prompt (role + rules) | 600 | Fixed |
| RAG context (chunks) | 1200 | Trimmed 2nd |
| Conversation history | 800 | Compressed 1st |
| User message | 300 | Never truncated |

History is compressed first when budget is exceeded. RAG chunks are trimmed second. The user's message is never truncated.

---

## Admin Authentication

### Get a Token (via API)

There is no dedicated `/auth/token` REST endpoint — authentication is handled through the admin portal UI (`POST /admin/login`), which sets an `access_token` httpOnly cookie.

For API access (Postman, scripts), use the token from the cookie or generate one via `scripts/create_admin.py`.

### Use the Token

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

All admin endpoints require this header.

---

## Provider Management

### Check Which Providers Are Available

```http
GET /providers/
```

### Test a Specific Provider

```http
POST /providers/anthropic/test
Authorization: Bearer <token>

{
  "message": "Hello! Reply in one sentence.",
  "model": null
}
```

### Switch System Default Provider

```http
PUT /providers/openai/default
Authorization: Bearer <token>
```

### Override Provider Per-Request (Admin Only)

```http
POST /chat/

{
  "app_id": "support",
  "session_id": "test-123",
  "message": "Hello",
  "provider_override": "gemini"
}
```

---

## Supported Providers

| ID | Display Name | Example Models | Env Var |
|----|-------------|---------------|---------|
| `anthropic` | Anthropic Claude | claude-opus-4-5, claude-haiku-4-5-20251001 | `ANTHROPIC_API_KEY` |
| `openai` | OpenAI | gpt-4o, gpt-4o-mini, o1, o3-mini | `OPENAI_API_KEY` |
| `gemini` | Google Gemini | gemini-2.5-pro, gemini-2.5-flash | `GEMINI_API_KEY` |
| `deepseek` | DeepSeek | deepseek-chat, deepseek-reasoner | `DEEPSEEK_API_KEY` |
| `mistral` | Mistral AI | mistral-large-latest, codestral-latest | `MISTRAL_API_KEY` |
| `cohere` | Cohere | command-r-plus, command-r | `COHERE_API_KEY` |
| `groq` | Groq | llama-3.3-70b-versatile, mixtral-8x7b | `GROQ_API_KEY` |
| `ollama` | Ollama (Local) | llama3.3, phi4, qwen2.5 | none |
| `openai_compat` | OpenAI Compatible | any | configurable |

---

## Error Responses

All errors return `{"error": "message"}` with the appropriate HTTP status:

| Status | Meaning |
|--------|---------|
| 401 | Missing/invalid token or provider auth failure |
| 404 | App or document not found |
| 409 | App ID already exists |
| 422 | Invalid file format or model not found |
| 429 | Rate limit exceeded |
| 503 | Provider unavailable |
| 504 | Provider request timed out |

---

## Audit Log

Every admin action is logged permanently. View via:

```http
GET /audit/?limit=100
Authorization: Bearer <token>
```

```json
[
  {
    "id": 42,
    "timestamp": "2026-04-20T12:30:00",
    "username": "master_admin",
    "action": "doc.upload",
    "target": "support/faq.md",
    "ip_address": "127.0.0.1",
    "success": true,
    "detail": null
  }
]
```

Audit logs are append-only — no updates or deletes ever.

---

## Admin Portal (Web UI)

| URL | Purpose |
|-----|---------|
| `/admin/login` | Login form |
| `/admin/` | Dashboard — health + app overview |
| `/admin/upload` | Upload documents |
| `/admin/library` | Browse all indexed documents |
| `/admin/apps` | Manage apps |
| `/admin/providers` | Manage AI providers |
| `/admin/sessions` | View active sessions |
| `/admin/audit` | Audit log viewer |
| `/admin/settings` | Change password, view settings |

---

## Common Workflows

### Add a New Knowledge Base Document

1. Upload the file: `POST /docs/upload`
2. Verify chunks: `GET /chunks/{app_id}?limit=10`
3. Test chat: `POST /chat/` with a question covered by the doc

### Switch an App to a Different AI Provider

1. Edit `config/apps/{app_id}.yaml` — change `provider` and `model`
2. Reload: `POST /apps/{app_id}/reload`
3. Test: `POST /chat/` and confirm the response returns the new reply

### Re-index After Changing Embedding Model

1. Update `EMBED_MODEL` in `.env`
2. Restart the server
3. `POST /docs/{app_id}/reembed` to wipe and rebuild embeddings

### Debug Provider Issues

1. `GET /providers/{id}/health` — check reachability
2. `POST /providers/{id}/test` — send a live test message
3. Check `GET /audit/` for any recent auth errors

---

## Postman Setup

1. Import `docs/postman_collection.json`
2. Set collection variable `base_url` = `http://localhost:8000`
3. Login via admin portal, copy the `access_token` cookie value
4. Set collection variable `token` = the JWT value
5. All admin requests will use `Authorization: Bearer {{token}}`
