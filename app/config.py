from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "CleanQuery AI"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://cleanquery:password@localhost:5432/cleanquery"
    database_pool_size: int = 10

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_model_fast: str = "gpt-4o-mini"
    openai_max_tokens: int = 4096
    openai_temperature: float = 0.1

    max_upload_size_mb: int = 100
    sample_rows_for_mapping: int = 5

    query_timeout_seconds: int = 30
    query_max_rows: int = 10000

    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
