from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    MISTRAL_API_KEY: str
    DATABASE_URL: str

    RAG_TOP_K: int = 3
    MISTRAL_CHAT_MODEL: str = "mistral-small-latest"
    MISTRAL_EMBED_MODEL: str = "mistral-embed"

    DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000


settings = Settings()
