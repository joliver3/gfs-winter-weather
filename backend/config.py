from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gfs_cache_ttl_minutes: int = 60

    class Config:
        env_prefix = ""


settings = Settings()
