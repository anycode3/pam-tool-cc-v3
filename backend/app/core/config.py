import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "PAM Tool"
    DEBUG: bool = True
    STORAGE_PATH: str = os.path.join(os.getcwd(), "storage")
    MAX_GDS_SIZE_MB: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
