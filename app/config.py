from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    KEITARO_URL: str
    KEITARO_API_KEY: str
    DATABASE_URL: str = "sqlite+aiosqlite:///./keitaro_app.db"

    class Config:
        env_file = ".env"

settings = Settings()