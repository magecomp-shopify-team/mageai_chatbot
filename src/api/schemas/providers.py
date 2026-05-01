from pydantic import BaseModel


class ProviderInfo(BaseModel):
    provider_id: str
    display_name: str
    available: bool
    default_model: str
    models: list[str]


class ProviderHealthResult(BaseModel):
    provider: str
    healthy: bool
    latency_ms: float


class ProviderTestRequest(BaseModel):
    message: str = "Hello! Please reply with a single sentence."
    model: str | None = None


class ProviderTestResult(BaseModel):
    provider: str
    model: str
    reply: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


class EnableProviderRequest(BaseModel):
    enabled: bool
