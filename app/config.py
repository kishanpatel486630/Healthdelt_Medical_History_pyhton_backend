import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Use absolute path to ensure SQLite finds the file
    DATABASE_URL: str = "sqlite:///./healthdelt.db"
    
    # Must match the Node.js JWT secrets exactly for token compatibility
    JWT_ACCESS_SECRET: str = os.getenv("JWT_ACCESS_SECRET", "healthdelt-access-secret-k9x7m2p4q8w1")
    JWT_REFRESH_SECRET: str = os.getenv("JWT_REFRESH_SECRET", "healthdelt-refresh-secret-j3n5v8b6t0y2")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Server
    PORT: int = 5000
    CLIENT_URL: str = "http://localhost:5173"
    
    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB

    class Config:
        env_file = ".env"

settings = Settings()
