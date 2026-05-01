# CLAUDE.md — Multi-App AI Chatbot System
# Claude Code Rules & Project Intelligence

## Project identity

This is a **multi-app RAG-powered chatbot backend** built with Python (FastAPI) + ChromaDB
+ SQLite. It supports **multiple AI providers** — Anthropic, OpenAI, Google Gemini, DeepSeek,
Mistral, Cohere, Groq, Ollama (local), and any OpenAI-compatible endpoint — selectable
per-app via config. It includes a **master admin portal** (Jinja2 + JWT) from which only the
master admin can upload documents, manage apps, configure AI providers, and perform all
sensitive operations.

Every design decision must optimise for: token efficiency, per-app isolation,
provider-agnostic AI routing, security-first access control, and production correctness.
You are acting as a senior backend engineer with deep expertise in LLM pipelines,
vector databases, multi-provider API design, and web application security.

---

## Architecture overview

```
chatbot/
├── CLAUDE.md
├── .env
├── .env.example
├── pyproject.toml
├── alembic/
│
├── config/
│   ├── apps/
│   │   ├── ecommerce.yaml
│   │   ├── support.yaml
│   │   ├── hr.yaml
│   │   └── _schema.yaml
│   ├── providers/                     ← ★ AI PROVIDER CONFIGS ★
│   │   ├── anthropic.yaml
│   │   ├── openai.yaml
│   │   ├── gemini.yaml
│   │   ├── deepseek.yaml
│   │   ├── mistral.yaml
│   │   ├── cohere.yaml
│   │   ├── groq.yaml
│   │   ├── ollama.yaml
│   │   └── _schema.yaml
│   └── settings.py
│
├── storage/
│   ├── files/{app_id}/
│   ├── chroma_db/
│   └── meta.json
│
├── src/
│   ├── core/
│   │   ├── config.py
│   │   ├── embedder.py
│   │   ├── chroma.py
│   │   ├── tokenizer.py
│   │   └── exceptions.py
│   │
│   ├── auth/
│   │   ├── models.py
│   │   ├── service.py
│   │   ├── deps.py
│   │   └── audit.py
│   │
│   ├── ai/                            ← ★ MULTI-PROVIDER AI LAYER ★
│   │   ├── base.py                    ← AIProvider abstract base class
│   │   ├── registry.py                ← provider registry + factory
│   │   ├── router.py                  ← select provider for a request
│   │   ├── providers/
│   │   │   ├── anthropic_provider.py  ← Claude (claude-opus-4, sonnet-4, haiku-4)
│   │   │   ├── openai_provider.py     ← GPT-4o, GPT-4o-mini, o1, o3
│   │   │   ├── gemini_provider.py     ← Gemini 2.5 Pro, Flash, Flash-Lite
│   │   │   ├── deepseek_provider.py   ← DeepSeek-V3, DeepSeek-R1
│   │   │   ├── mistral_provider.py    ← Mistral Large, Small, Codestral
│   │   │   ├── cohere_provider.py     ← Command R+, Command R
│   │   │   ├── groq_provider.py       ← Llama 3.3, Mixtral (via Groq)
│   │   │   └── ollama_provider.py     ← any local model via Ollama
│   │   └── normaliser.py              ← unify response format across providers
│   │
│   ├── pipeline/
│   │   ├── chunker.py
│   │   ├── indexer.py
│   │   ├── retriever.py
│   │   ├── history.py
│   │   └── assembler.py
│   │
│   ├── manager/
│   │   ├── doc_manager.py
│   │   └── meta_store.py
│   │
│   └── api/
│       ├── main.py
│       ├── deps.py
│       ├── routers/
│       │   ├── chat.py
│       │   ├── docs.py
│       │   ├── chunks.py
│       │   ├── apps.py
│       │   ├── providers.py           ← /providers/* — list, test, set default
│       │   ├── health.py
│       │   └── admin_portal.py
│       └── schemas/
│           ├── chat.py
│           ├── docs.py
│           ├── apps.py
│           ├── providers.py           ← ProviderConfig, ModelInfo, TestResult
│           └── auth.py
│
├── admin_ui/
│   ├── templates/
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── upload.html
│   │   ├── library.html
│   │   ├── chunks.html
│   │   ├── apps.html
│   │   ├── providers.html             ← ★ PROVIDER MANAGEMENT PAGE ★
│   │   ├── sessions.html
│   │   ├── audit.html
│   │   └── settings.html
│   └── static/
│       ├── admin.css
│       └── admin.js
│
├── scripts/
│   ├── create_admin.py
│   ├── test_provider.py               ← CLI: send a test ping to any provider
│   ├── reindex_app.py
│   ├── bulk_import.py
│   └── inspect_chunks.py
│
└── tests/
    ├── conftest.py
    ├── test_chunker.py
    ├── test_retriever.py
    ├── test_assembler.py
    ├── test_history.py
    ├── test_ai/
    │   ├── test_provider_factory.py
    │   ├── test_anthropic_provider.py
    │   ├── test_openai_provider.py
    │   ├── test_gemini_provider.py
    │   └── test_normaliser.py
    ├── test_auth/
    │   ├── test_login.py
    │   ├── test_jwt.py
    │   └── test_audit.py
    └── test_api/
        ├── test_chat.py
        ├── test_docs.py
        ├── test_providers.py
        └── test_docs_auth.py
```

---

## Non-negotiable rules

### 1. Never put secrets in code
- All API keys live in `.env` — one variable per provider
- Provider configs in YAML never contain actual API key values — only reference the env var name
- `MASTER_ADMIN_PASSWORD_HASH` stores only bcrypt hash — never plaintext

### 2. Type everything
- Full type annotations on every function
- `pydantic.BaseModel` for all data contracts
- `AIProvider` is an abstract base — every concrete provider implements its full interface

### 3. Single responsibility — especially the AI layer
- `base.py` defines the contract — never implements logic
- Each provider file handles exactly one provider's SDK — no cross-provider logic
- `registry.py` does factory/lookup — nothing else
- `router.py` decides which provider to use — nothing else
- `normaliser.py` converts any provider response to `NormalisedResponse` — nothing else

### 4. Provider-agnostic everywhere above the AI layer
- `assembler.py`, `history.py`, `chat.py` router — none of these import provider SDKs directly
- All AI calls flow through `registry.get_provider(provider_id).complete(context)`
- If you add a new provider, zero changes needed outside `src/ai/`

### 5. Token budget is sacred
- Every provider has different token counting — use provider's own tokenizer or tiktoken fallback
- Budget: `system_prompt ≤ 600` + `RAG ≤ 1200` + `history ≤ 800` + `user_msg ≤ 300`
- Compress history first, trim RAG second, never truncate user message

### 6. Error handling is not optional
- Every provider SDK call wrapped in try/except
- Map provider-specific errors to domain exceptions: `ProviderAuthError`, `ProviderRateLimitError`,
  `ProviderTimeoutError`, `ProviderUnavailableError`, `ModelNotFoundError`
- FastAPI returns correct HTTP codes: 401 for auth, 429 for rate limit, 503 for unavailable
- Auth failures: always 401, never reveal username vs password

### 7. Per-app isolation
- ChromaDB collection: `{app_id}_app`
- Files: `storage/files/{app_id}/`
- History: `(session_id, app_id)` — never session_id alone
- Each app picks its own provider + model in YAML — fully independent

### 8. Audit log is append-only forever
- Every admin action (including provider config changes) written to `audit_log`
- No UPDATE or DELETE on `audit_log` — ever

### 9. Async all the way
- All provider HTTP calls are async (aiohttp / httpx / provider async SDK)
- ChromaDB (sync): `asyncio.to_thread()`. File I/O: `aiofiles`.

### 10. Tests before done
- Every provider has a mocked test — never hit real API in tests
- Every admin route: test 401 (no token) + 200 (valid token)

---

## Supported AI providers — full catalogue

### Provider IDs and supported models

| Provider ID | Class | Models (examples) | Auth |
|---|---|---|---|
| `anthropic` | `AnthropicProvider` | `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5` | `ANTHROPIC_API_KEY` |
| `openai` | `OpenAIProvider` | `gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini` | `OPENAI_API_KEY` |
| `gemini` | `GeminiProvider` | `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.0-flash-lite` | `GEMINI_API_KEY` |
| `deepseek` | `DeepSeekProvider` | `deepseek-chat` (V3), `deepseek-reasoner` (R1) | `DEEPSEEK_API_KEY` |
| `mistral` | `MistralProvider` | `mistral-large-latest`, `mistral-small-latest`, `codestral-latest` | `MISTRAL_API_KEY` |
| `cohere` | `CohereProvider` | `command-r-plus`, `command-r`, `command-light` | `COHERE_API_KEY` |
| `groq` | `GroqProvider` | `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`, `gemma2-9b-it` | `GROQ_API_KEY` |
| `ollama` | `OllamaProvider` | `llama3.3`, `mistral`, `phi4`, `qwen2.5`, any local model | none (local) |
| `openai_compat` | `OpenAICompatProvider` | any model — set base URL in config | configurable |

`openai_compat` covers: Together AI, Perplexity, Fireworks, Azure OpenAI, LM Studio,
vLLM, and any endpoint that implements the OpenAI `/v1/chat/completions` schema.

---

## AI layer — module contracts

### `src/ai/base.py`
```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from pydantic import BaseModel

class NormalisedResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    finish_reason: str           # "stop" | "length" | "tool_calls" | "error"
    raw: dict                    # full raw response from provider for debugging

class AIProvider(ABC):
    provider_id: str             # e.g. "anthropic", "openai"
    display_name: str            # e.g. "Anthropic Claude"

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        messages: list[dict],    # [{"role": "user"|"assistant", "content": str}]
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> NormalisedResponse | AsyncIterator[str]: ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Return available model IDs for this provider.""" ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if provider is reachable and API key is valid.""" ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Provider-specific token count, or tiktoken fallback.""" ...
```

### `src/ai/registry.py`
```python
class ProviderRegistry:
    """
    Singleton. Loads provider configs from config/providers/*.yaml on startup.
    Instantiates provider classes lazily (on first use).
    """
    def register(self, provider: AIProvider) -> None: ...
    def get(self, provider_id: str) -> AIProvider: ...        # raises ProviderNotFoundError
    def list_providers(self) -> list[ProviderInfo]: ...       # name, id, available models, health
    def is_available(self, provider_id: str) -> bool: ...     # API key present + provider registered

registry = ProviderRegistry()   # module-level singleton
```

### `src/ai/router.py`
```python
async def resolve_provider(app_id: str, override_provider: str | None = None) -> AIProvider:
    """
    Resolution order:
    1. override_provider if passed in request body (admin testing only)
    2. app config: provider field in {app_id}.yaml
    3. settings.DEFAULT_PROVIDER
    4. First available provider in registry (fallback)
    Raises ProviderUnavailableError if none available.
    """

async def complete(
    context: AssembledContext,
    app_id: str,
    override_provider: str | None = None,
    stream: bool = False,
) -> NormalisedResponse | AsyncIterator[str]:
    """Single entry point for all AI completions."""
```

### `src/ai/normaliser.py`
```python
def normalise_anthropic(response) -> NormalisedResponse: ...
def normalise_openai(response) -> NormalisedResponse: ...
def normalise_gemini(response) -> NormalisedResponse: ...
def normalise_deepseek(response) -> NormalisedResponse: ...
def normalise_mistral(response) -> NormalisedResponse: ...
def normalise_cohere(response) -> NormalisedResponse: ...
def normalise_groq(response) -> NormalisedResponse: ...
def normalise_ollama(response) -> NormalisedResponse: ...
```

---

## Provider implementations

### `src/ai/providers/anthropic_provider.py`
```python
import anthropic

class AnthropicProvider(AIProvider):
    provider_id = "anthropic"
    display_name = "Anthropic Claude"

    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def complete(self, system_prompt, messages, model, max_tokens=512,
                       temperature=0.7, stream=False):
        kwargs = dict(model=model, max_tokens=max_tokens,
                      system=system_prompt, messages=messages)
        if stream:
            async with self._client.messages.stream(**kwargs) as s:
                async for chunk in s.text_stream:
                    yield chunk
        else:
            r = await self._client.messages.create(**kwargs)
            return normalise_anthropic(r)

    async def list_models(self) -> list[str]:
        return ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5-20251001",
                "claude-opus-4-6", "claude-sonnet-4-6"]

    async def health_check(self) -> bool:
        try:
            await self._client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=5,
                messages=[{"role": "user", "content": "hi"}]
            )
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        # Anthropic charges per character approximation: chars / 4
        return len(text) // 4
```

### `src/ai/providers/openai_provider.py`
```python
from openai import AsyncOpenAI

class OpenAIProvider(AIProvider):
    provider_id = "openai"
    display_name = "OpenAI"

    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def complete(self, system_prompt, messages, model, max_tokens=512,
                       temperature=0.7, stream=False):
        msgs = [{"role": "system", "content": system_prompt}] + messages
        if stream:
            async for chunk in await self._client.chat.completions.create(
                model=model, messages=msgs, max_tokens=max_tokens,
                temperature=temperature, stream=True
            ):
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            r = await self._client.chat.completions.create(
                model=model, messages=msgs,
                max_tokens=max_tokens, temperature=temperature
            )
            return normalise_openai(r)

    async def list_models(self) -> list[str]:
        models = await self._client.models.list()
        return [m.id for m in models.data if "gpt" in m.id or m.id.startswith("o")]

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4o")
        return len(enc.encode(text))
```

### `src/ai/providers/gemini_provider.py`
```python
import google.generativeai as genai

class GeminiProvider(AIProvider):
    provider_id = "gemini"
    display_name = "Google Gemini"

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)

    async def complete(self, system_prompt, messages, model, max_tokens=512,
                       temperature=0.7, stream=False):
        # Gemini uses GenerativeModel with system_instruction
        # Convert messages from OpenAI format to Gemini contents format
        gmodel = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens, temperature=temperature
            )
        )
        contents = _messages_to_gemini_contents(messages)
        if stream:
            response = await gmodel.generate_content_async(contents, stream=True)
            async for chunk in response:
                yield chunk.text
        else:
            response = await gmodel.generate_content_async(contents)
            return normalise_gemini(response)

    async def list_models(self) -> list[str]:
        return ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash",
                "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"]

    async def health_check(self) -> bool:
        try:
            m = genai.GenerativeModel("gemini-2.0-flash-lite")
            await m.generate_content_async("hi")
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        return len(text) // 4   # approximate
```

### `src/ai/providers/deepseek_provider.py`
```python
# DeepSeek uses OpenAI-compatible API — use openai SDK with custom base_url
from openai import AsyncOpenAI

class DeepSeekProvider(AIProvider):
    provider_id = "deepseek"
    display_name = "DeepSeek"

    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1"
        )

    async def complete(self, system_prompt, messages, model, max_tokens=512,
                       temperature=0.7, stream=False):
        msgs = [{"role": "system", "content": system_prompt}] + messages
        if stream:
            async for chunk in await self._client.chat.completions.create(
                model=model, messages=msgs, max_tokens=max_tokens,
                temperature=temperature, stream=True
            ):
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            r = await self._client.chat.completions.create(
                model=model, messages=msgs,
                max_tokens=max_tokens, temperature=temperature
            )
            return normalise_openai(r)   # same format — reuse OpenAI normaliser

    async def list_models(self) -> list[str]:
        return ["deepseek-chat", "deepseek-reasoner"]

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
```

### `src/ai/providers/mistral_provider.py`
```python
from mistralai import Mistral

class MistralProvider(AIProvider):
    provider_id = "mistral"
    display_name = "Mistral AI"

    def __init__(self):
        self._client = Mistral(api_key=settings.MISTRAL_API_KEY)

    async def complete(self, system_prompt, messages, model, max_tokens=512,
                       temperature=0.7, stream=False):
        msgs = [{"role": "system", "content": system_prompt}] + messages
        if stream:
            async for event in await self._client.chat.stream_async(
                model=model, messages=msgs, max_tokens=max_tokens, temperature=temperature
            ):
                if event.data.choices[0].delta.content:
                    yield event.data.choices[0].delta.content
        else:
            r = await self._client.chat.complete_async(
                model=model, messages=msgs,
                max_tokens=max_tokens, temperature=temperature
            )
            return normalise_mistral(r)

    async def list_models(self) -> list[str]:
        return ["mistral-large-latest", "mistral-small-latest",
                "codestral-latest", "open-mixtral-8x7b"]

    async def health_check(self) -> bool:
        try:
            await self._client.models.list_async()
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
```

### `src/ai/providers/cohere_provider.py`
```python
import cohere

class CohereProvider(AIProvider):
    provider_id = "cohere"
    display_name = "Cohere"

    def __init__(self):
        self._client = cohere.AsyncClient(api_key=settings.COHERE_API_KEY)

    async def complete(self, system_prompt, messages, model, max_tokens=512,
                       temperature=0.7, stream=False):
        # Cohere v2 API: chat_history + message + preamble
        preamble = system_prompt
        chat_history = _messages_to_cohere_history(messages[:-1])
        user_message = messages[-1]["content"] if messages else ""

        if stream:
            async for event in self._client.chat_stream(
                model=model, message=user_message, preamble=preamble,
                chat_history=chat_history, max_tokens=max_tokens,
                temperature=temperature
            ):
                if event.event_type == "text-generation":
                    yield event.text
        else:
            r = await self._client.chat(
                model=model, message=user_message, preamble=preamble,
                chat_history=chat_history, max_tokens=max_tokens, temperature=temperature
            )
            return normalise_cohere(r)

    async def list_models(self) -> list[str]:
        return ["command-r-plus", "command-r", "command-light", "command-nightly"]

    async def health_check(self) -> bool:
        try:
            await self._client.check_api_key()
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        return len(text) // 4
```

### `src/ai/providers/groq_provider.py`
```python
from groq import AsyncGroq

class GroqProvider(AIProvider):
    provider_id = "groq"
    display_name = "Groq"

    def __init__(self):
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def complete(self, system_prompt, messages, model, max_tokens=512,
                       temperature=0.7, stream=False):
        msgs = [{"role": "system", "content": system_prompt}] + messages
        if stream:
            async for chunk in await self._client.chat.completions.create(
                model=model, messages=msgs, max_tokens=max_tokens,
                temperature=temperature, stream=True
            ):
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            r = await self._client.chat.completions.create(
                model=model, messages=msgs,
                max_tokens=max_tokens, temperature=temperature
            )
            return normalise_openai(r)   # Groq returns OpenAI-compatible format

    async def list_models(self) -> list[str]:
        models = await self._client.models.list()
        return [m.id for m in models.data]

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
```

### `src/ai/providers/ollama_provider.py`
```python
import httpx

class OllamaProvider(AIProvider):
    provider_id = "ollama"
    display_name = "Ollama (Local)"

    def __init__(self):
        self._base_url = settings.OLLAMA_BASE_URL  # default: http://localhost:11434

    async def complete(self, system_prompt, messages, model, max_tokens=512,
                       temperature=0.7, stream=False):
        # Ollama implements /api/chat which is OpenAI-compatible
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "options": {"num_predict": max_tokens, "temperature": temperature},
            "stream": stream,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            if stream:
                async with client.stream("POST", f"{self._base_url}/api/chat",
                                          json=payload) as r:
                    async for line in r.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if not data.get("done"):
                                yield data["message"]["content"]
            else:
                r = await client.post(f"{self._base_url}/api/chat", json={**payload, "stream": False})
                return normalise_ollama(r.json())

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self._base_url}/api/tags")
            return [m["name"] for m in r.json().get("models", [])]

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self._base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        return len(text) // 4
```

### `src/ai/providers/openai_compat_provider.py`
```python
# For: Together AI, Perplexity, Fireworks, Azure OpenAI, LM Studio, vLLM, etc.
from openai import AsyncOpenAI

class OpenAICompatProvider(AIProvider):
    """
    Generic OpenAI-compatible provider. Configure via provider YAML:
      base_url: https://api.together.xyz/v1
      api_key_env: TOGETHER_API_KEY
      models: [meta-llama/Llama-3-70b-chat-hf, mistralai/Mixtral-8x7B-Instruct-v0.1]
    """
    provider_id = "openai_compat"
    display_name = "OpenAI Compatible"

    def __init__(self, base_url: str, api_key: str, provider_label: str = "openai_compat"):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.provider_id = provider_label   # e.g. "together", "perplexity"

    async def complete(self, system_prompt, messages, model, max_tokens=512,
                       temperature=0.7, stream=False):
        msgs = [{"role": "system", "content": system_prompt}] + messages
        if stream:
            async for chunk in await self._client.chat.completions.create(
                model=model, messages=msgs, max_tokens=max_tokens,
                temperature=temperature, stream=True
            ):
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            r = await self._client.chat.completions.create(
                model=model, messages=msgs,
                max_tokens=max_tokens, temperature=temperature
            )
            return normalise_openai(r)

    async def list_models(self) -> list[str]:
        try:
            models = await self._client.models.list()
            return [m.id for m in models.data]
        except Exception:
            return []

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
```

---

## Provider config YAML schema (`config/providers/_schema.yaml`)

Each provider YAML must include:
```yaml
provider_id: str               # must match class provider_id
display_name: str
enabled: bool = true
api_key_env: str               # e.g. "ANTHROPIC_API_KEY" — name of env var, not value
base_url: str | null           # only for openai_compat providers
default_model: str             # model used when app config doesn't specify
available_models: list[str]    # shown in admin dropdown
max_tokens_limit: int          # hard cap for this provider
default_temperature: float = 0.7
timeout_seconds: int = 60
```

Example `config/providers/deepseek.yaml`:
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

---

## App config schema (updated with provider field)

```yaml
# required
name: str
role: str
tone: str
rules: list[str]

# AI provider selection — both required together
provider: str           # provider_id: "anthropic" | "openai" | "gemini" | "deepseek" |
                        #              "mistral" | "cohere" | "groq" | "ollama" | "openai_compat"
model: str              # model ID valid for that provider

# optional with defaults
max_history_turns: int = 6
max_chunk_tokens: int = 800
top_k_chunks: int = 4
min_relevance: float = 0.3
max_response_tokens: int = 512
temperature: float = 0.7
```

---

## Domain exceptions — full set

```python
class ChatbotError(Exception): ...

# Provider exceptions
class ProviderNotFoundError(ChatbotError): ...       # provider_id not in registry
class ProviderAuthError(ChatbotError): ...           # API key invalid or missing
class ProviderRateLimitError(ChatbotError): ...      # 429 from provider
class ProviderTimeoutError(ChatbotError): ...        # request timed out
class ProviderUnavailableError(ChatbotError): ...    # provider API down
class ModelNotFoundError(ChatbotError): ...          # model not available for provider

# App exceptions
class AppNotFoundError(ChatbotError): ...
class DocumentNotFoundError(ChatbotError): ...
class EmbedFailedError(ChatbotError): ...
class TokenBudgetExceededError(ChatbotError): ...
class HistoryCompressionError(ChatbotError): ...

# Auth exceptions
class AuthenticationError(ChatbotError): ...
class InsufficientPermissionsError(ChatbotError): ...
```

HTTP status mapping in `main.py` exception handlers:
- `ProviderAuthError` → 401
- `ProviderRateLimitError` → 429
- `ProviderTimeoutError` → 504
- `ProviderUnavailableError` → 503
- `ModelNotFoundError` → 422
- `AppNotFoundError` → 404
- `DocumentNotFoundError` → 404
- `AuthenticationError` → 401

---

## API routes — providers

### Public
```
GET  /providers/                 list all registered providers with health status
GET  /providers/{id}/models      list available models for a provider
```

### Admin only (JWT required)
```
GET  /providers/{id}/health      live health check for one provider
POST /providers/{id}/test        send a test message, return response + latency
POST /providers/{id}/enable      enable/disable a provider
PUT  /providers/{id}/default     set as system-wide default provider
```

---

## Environment variables (`.env.example`)

```bash
# ── AI PROVIDERS ────────────────────────────────────────────────────
# Add API key for each provider you want to use. Leave blank to disable.
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
GEMINI_API_KEY=AIza-xxx
DEEPSEEK_API_KEY=sk-xxx
MISTRAL_API_KEY=xxx
COHERE_API_KEY=xxx
GROQ_API_KEY=gsk_xxx
OLLAMA_BASE_URL=http://localhost:11434

# OpenAI-compatible providers (add as many as needed)
TOGETHER_API_KEY=xxx
PERPLEXITY_API_KEY=pplx-xxx
FIREWORKS_API_KEY=fw_xxx
AZURE_OPENAI_API_KEY=xxx
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# System default provider (used when app config doesn't specify)
DEFAULT_PROVIDER=anthropic
DEFAULT_MODEL=claude-haiku-4-5-20251001

# ── STORAGE ─────────────────────────────────────────────────────────
STORAGE_ROOT=./storage/files
CHROMA_PATH=./storage/chroma_db
META_DB_PATH=./storage/meta.json
HISTORY_DB_URL=sqlite+aiosqlite:///./storage/app.db

# ── EMBEDDING ───────────────────────────────────────────────────────
EMBED_MODEL=all-MiniLM-L6-v2
EMBED_BATCH_SIZE=64

# ── TOKEN BUDGETS ───────────────────────────────────────────────────
DEFAULT_MAX_HISTORY_TOKENS=800
DEFAULT_MAX_RAG_TOKENS=1200
DEFAULT_MAX_SYSTEM_TOKENS=600

# ── API ─────────────────────────────────────────────────────────────
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# ── MASTER ADMIN AUTH ────────────────────────────────────────────────
MASTER_ADMIN_USERNAME=master_admin
MASTER_ADMIN_PASSWORD_HASH=$2b$12$replace_with_real_bcrypt_hash
AUTH_SECRET_KEY=replace-with-64-char-random-hex
AUTH_ACCESS_TOKEN_EXPIRE_HOURS=8
AUTH_REFRESH_TOKEN_EXPIRE_DAYS=7
ADMIN_TOTP_ENABLED=false
ADMIN_TOTP_ENCRYPTION_KEY=replace-with-fernet-key
CSRF_SECRET_KEY=replace-with-another-64-char-hex
RATE_LIMIT_LOGIN=5/15minute
```

---

## Anti-patterns

| Anti-pattern | Correct approach |
|---|---|
| `import anthropic` in assembler.py or router | Only in `anthropic_provider.py` |
| `if provider == "openai": ...` in chat router | Use `registry.get(provider_id).complete()` |
| Hardcoding model names outside provider files | Model lives in app YAML + provider YAML |
| Swallowing `ProviderRateLimitError` silently | Re-raise — FastAPI returns 429 |
| Calling two different providers in one request | One provider per request, always |
| Storing API keys in provider YAML files | YAML stores env var NAME, not value |
| `except Exception: pass` in provider code | Log + raise mapped domain exception |
| Creating a new HTTP client per request | Provider class owns singleton client |
| Auth failures returning different messages | Always same 401, never field hints |
| `audit_log` UPDATE or DELETE | Append-only, forever |

---

## Testing conventions

```python
# Provider mocking pattern
@pytest.fixture
def mock_anthropic_provider(monkeypatch):
    async def fake_complete(*args, **kwargs):
        return NormalisedResponse(
            text="Mocked reply", input_tokens=10, output_tokens=5,
            model="claude-haiku-4-5-20251001", provider="anthropic",
            finish_reason="stop", raw={}
        )
    monkeypatch.setattr("src.ai.providers.anthropic_provider.AnthropicProvider.complete", fake_complete)

# Test provider routing
async def test_app_uses_configured_provider(client, auth_headers):
    # App config has provider: gemini — verify Gemini SDK was called, not Anthropic

# Test fallback
async def test_falls_back_to_default_when_app_has_no_provider(client):
    ...

# Auth tests
async def test_provider_health_requires_auth(client):
    r = await client.get("/providers/openai/health")
    assert r.status_code == 401

async def test_provider_test_requires_auth(client):
    r = await client.post("/providers/openai/test", json={"message": "hi"})
    assert r.status_code == 401
```

---

## Performance targets

| Metric | Target |
|---|---|
| Provider registry init (startup) | < 1s |
| Provider health check | < 2s |
| JWT decode per request | < 5ms |
| Embed 10 chunks | < 200ms |
| ChromaDB query top-5 | < 50ms |
| Context assembly | < 400ms |
| AI first token — Groq (fastest) | < 400ms |
| AI first token — Anthropic haiku | < 800ms |
| AI first token — Gemini Flash | < 600ms |
| Upload + embed 1MB | < 5s |
| Chat round-trip total | < 3s |

---

## Git commit conventions

```
feat(ai): add Gemini 2.5 Pro provider with streaming support
feat(ai): add DeepSeek-R1 reasoning model via openai_compat
feat(ai): add Groq provider with llama-3.3 and mixtral models
feat(ai): add generic OpenAI-compatible provider for Together/Perplexity
fix(ai): handle Cohere rate limit → ProviderRateLimitError
refactor(ai): extract normaliser functions into normaliser.py
feat(admin): add provider management page to admin portal
test(ai): add mocked tests for all 8 providers
```

Format: `type(module): description` — lowercase, present tense.

uvicorn src.api.main:app --reload
