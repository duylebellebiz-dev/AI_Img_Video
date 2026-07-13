from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://nailsocial:change-me-locally@127.0.0.1:5432/nailsocial"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    gemini_api_key: str = ""
    gemini_image_model: str = "gemini-2.5-flash-image"

    storage_root: str = "./storage"

    # Object storage (Cloudflare R2, S3-compatible) — the durable copy of
    # everything under storage_root. Needed because free-tier web hosts don't
    # give you a persistent disk: local storage_root is just a scratch/cache
    # directory that can be wiped by a restart or scale-to-zero cycle. Leave
    # blank to run local-disk-only (fine for local dev).
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""

    quality_pass_threshold: int = 80
    quality_max_retries: int = 3

    batch_min_images: int = 1
    batch_max_images: int = 100
    # How many images in a batch job to generate concurrently. Generation is
    # I/O-bound (Gemini + Claude network round trips), so running several in
    # parallel cuts wall-clock time for a batch without changing per-image cost.
    batch_concurrency: int = 4

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_root)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def has_anthropic_key(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_r2(self) -> bool:
        return bool(self.r2_account_id and self.r2_access_key_id and self.r2_secret_access_key and self.r2_bucket_name)

    @property
    def r2_endpoint_url(self) -> str:
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
