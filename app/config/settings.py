import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./healthdelt.db"
    JWT_ACCESS_SECRET: str = os.getenv("JWT_ACCESS_SECRET", "healthdelt-access-secret-k9x7m2p4q8w1")
    JWT_REFRESH_SECRET: str = os.getenv("JWT_REFRESH_SECRET", "healthdelt-refresh-secret-j3n5v8b6t0y2")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PORT: int = 5000
    CLIENT_URL: str = "http://localhost:5173"
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760

    model_config = ConfigDict(env_file=".env")


settings = Settings()
