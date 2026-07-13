"""Cloudflare R2 (S3-compatible) client — the durable copy of everything under
storage_root. Free-tier web hosts (e.g. Render's free web service) don't offer
a persistent disk, so local storage_root is treated as a scratch/cache
directory that can be wiped by a restart or scale-to-zero cycle; R2 is what
actually survives. All methods are no-ops when R2 isn't configured, so local
dev (and CI) keeps working purely on local disk without any credentials.
"""

import logging
from pathlib import Path

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class R2Client:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client = None
        if self.settings.has_r2:
            import boto3

            self._client = boto3.client(
                "s3",
                endpoint_url=self.settings.r2_endpoint_url,
                aws_access_key_id=self.settings.r2_access_key_id,
                aws_secret_access_key=self.settings.r2_secret_access_key,
                region_name="auto",
            )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def upload_file(self, local_path: Path, key: str) -> None:
        if not self.is_configured or not local_path.exists():
            return
        try:
            self._client.upload_file(str(local_path), self.settings.r2_bucket_name, key)
        except Exception:  # noqa: BLE001 - best-effort; local disk still has the file for this process's lifetime
            logger.exception("R2 upload failed for key=%s", key)

    def download_file(self, key: str, local_path: Path) -> bool:
        if not self.is_configured:
            return False
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self._client.download_file(self.settings.r2_bucket_name, key, str(local_path))
            return True
        except Exception:  # noqa: BLE001 - object may simply not exist (never uploaded, or already deleted)
            return False

    def delete_file(self, key: str) -> None:
        if not self.is_configured:
            return
        try:
            self._client.delete_object(Bucket=self.settings.r2_bucket_name, Key=key)
        except Exception:  # noqa: BLE001 - best-effort cleanup, never block the caller's main flow
            logger.exception("R2 delete failed for key=%s", key)
