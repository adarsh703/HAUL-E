from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = 'sqlite+aiosqlite:///tms.db'
    GOOGLE_PROJECT_ID: str = 'haul-e-498411'
    GOOGLE_LOCATION: str = 'us-central1'
    GEMINI_MODEL: str = 'gemini-2.5-flash'
    GOOGLE_CREDENTIALS_FILE: str = 'google_credentials.json'
    API_HOST: str = '0.0.0.0'
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = ['http://localhost:3000', 'http://localhost:5173']

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
