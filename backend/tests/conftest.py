import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

# Point at a throwaway SQLite DB and mock-mode API keys before any app module
# is imported, so tests never touch the real Postgres instance or make real
# Claude/Gemini calls.
os.environ["DATABASE_URL"] = f"sqlite:///{BACKEND_ROOT / 'test_nailsocial.db'}"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["STORAGE_ROOT"] = str(BACKEND_ROOT / "test_storage")

import pytest  # noqa: E402


@pytest.fixture
def tiny_png_bytes() -> bytes:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (4, 4), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()
