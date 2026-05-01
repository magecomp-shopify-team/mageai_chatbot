from pydantic import BaseModel


class DocMeta(BaseModel):
    filename: str
    hash: str
    chunk_count: int
    indexed_at: str
    file_path: str | None = None


class IndexResultSchema(BaseModel):
    app_id: str
    filename: str
    chunks_indexed: int
    file_hash: str
    skipped: bool = False
