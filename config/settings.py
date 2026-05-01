from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


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
