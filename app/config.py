from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    TEMP_UPLOAD_DIR: str = "temp_uploads"
    PERM_UPLOAD_DIR: str = "perm_uploads"
    CLEANUP_INTERVAL: int = 3600  # seconds
    STALE_THRESHOLD: int = 3600  # seconds (1 hour)

settings = Settings()
