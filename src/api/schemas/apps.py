from pydantic import BaseModel


class AppInfo(BaseModel):
    app_id: str
    name: str
    provider: str
    model: str
    doc_count: int = 0


class UpdateProviderRequest(BaseModel):
    provider: str
    model: str


class AppDetail(BaseModel):
    app_id: str
    name: str
    role: str
    tone: str
    rules: list[str]
    provider: str
    model: str
    max_history_turns: int
    max_chunk_tokens: int
    top_k_chunks: int
    min_relevance: float
    max_response_tokens: int
    temperature: float


class UpdateAppRequest(BaseModel):
    name: str
    role: str
    tone: str
    rules: list[str]
    provider: str
    model: str
    max_history_turns: int = 6
    max_chunk_tokens: int = 800
    top_k_chunks: int = 4
    min_relevance: float = 0.3
    max_response_tokens: int = 512
    temperature: float = 0.7


class CreateAppRequest(BaseModel):
    app_id: str
    name: str
    role: str
    tone: str
    rules: list[str]
    provider: str
    model: str
    max_history_turns: int = 6
    max_chunk_tokens: int = 800
    top_k_chunks: int = 4
    min_relevance: float = 0.3
    max_response_tokens: int = 512
    temperature: float = 0.7
