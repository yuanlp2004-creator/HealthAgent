from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "dev"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "sqlite:///./healthagent.db"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:5173"

    ocr_engine: str = "baidu"
    baidu_ocr_ak: str = ""
    baidu_ocr_sk: str = ""
    baidu_ocr_endpoint: str = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate"
    baidu_ocr_timeout: float = 15.0

    dashscope_api_key: str = ""
    dashscope_vl_model: str = "qwen-vl-plus"
    dashscope_timeout: float = 30.0
    ocr_vlm_fallback: bool = True

    dashscope_chat_model: str = "qwen-plus"
    dashscope_embedding_model: str = "text-embedding-v3"
    dashscope_embedding_dim: int = 1024
    dashscope_chat_endpoint: str = (
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    )
    dashscope_embedding_endpoint: str = (
        "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    )
    llm_temperature: float = 0.3
    llm_cache_dir: str = ".cache/llm"
    rag_kb_db_path: str = "storage/kb.sqlite"
    rag_top_k: int = 5
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50

    @field_validator("cors_origins")
    @classmethod
    def check_cors_not_empty(cls, v):
        if not v.strip():
            raise ValueError("CORS_ORIGINS must not be empty")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
