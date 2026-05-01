"""Domain exception hierarchy for the chatbot backend."""


class ChatbotError(Exception):
    """Base exception for all chatbot errors."""


# ── Provider exceptions ───────────────────────────────────────────────────────

class ProviderNotFoundError(ChatbotError):
    """provider_id not registered in the registry."""


class ProviderAuthError(ChatbotError):
    """API key invalid, missing, or rejected by the provider."""


class ProviderRateLimitError(ChatbotError):
    """Provider returned HTTP 429 — rate limit exceeded."""


class ProviderTimeoutError(ChatbotError):
    """Request to the provider timed out."""


class ProviderUnavailableError(ChatbotError):
    """Provider API is down or returned 5xx."""


class ModelNotFoundError(ChatbotError):
    """Requested model not available for the provider."""


# ── App exceptions ────────────────────────────────────────────────────────────

class AppNotFoundError(ChatbotError):
    """App config YAML does not exist for the given app_id."""


class DocumentNotFoundError(ChatbotError):
    """Requested document not found in storage or meta."""


class EmbedFailedError(ChatbotError):
    """Embedding generation failed."""


class TokenBudgetExceededError(ChatbotError):
    """Assembled context exceeds the allowed token budget."""


class HistoryCompressionError(ChatbotError):
    """Failed to compress conversation history."""


# ── Auth exceptions ───────────────────────────────────────────────────────────

class AuthenticationError(ChatbotError):
    """Invalid credentials or token."""


class InsufficientPermissionsError(ChatbotError):
    """Authenticated user lacks required permissions."""
