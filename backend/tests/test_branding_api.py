import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app import main as main_module
    from app.config import get_settings
    from app.database import Base, SessionLocal, engine
    from app.models.db_models import SalonBranding

    Base.metadata.create_all(bind=engine)

    # SalonBranding is a singleton row, unlike the UUID-keyed rows other test
    # files use, so it can leak state across test files sharing the same
    # on-disk SQLite DB. Reset it before each test regardless of run order.
    session = SessionLocal()
    try:
        branding = session.get(SalonBranding, SalonBranding.SINGLETON_ID)
        if branding is not None:
            session.delete(branding)
            session.commit()
    finally:
        session.close()
    for existing in (get_settings().storage_path / "branding").glob("logo.*"):
        existing.unlink(missing_ok=True)

    with TestClient(main_module.app) as test_client:
        yield test_client


def test_get_logo_is_null_before_any_upload(client):
    resp = client.get("/api/branding/logo")
    assert resp.status_code == 200
    assert resp.json()["logo_url"] is None


def test_upload_logo_returns_logo_url(client, tiny_png_bytes):
    resp = client.post("/api/branding/logo", files={"logo": ("logo.png", tiny_png_bytes, "image/png")})
    assert resp.status_code == 201, resp.text
    logo_url = resp.json()["logo_url"]
    assert logo_url
    assert logo_url.startswith("/media/branding/")

    get_resp = client.get("/api/branding/logo")
    assert get_resp.json()["logo_url"] == logo_url


def test_uploading_a_new_logo_replaces_the_old_one(client, tiny_png_bytes):
    first = client.post("/api/branding/logo", files={"logo": ("first.png", tiny_png_bytes, "image/png")})
    second = client.post("/api/branding/logo", files={"logo": ("second.png", tiny_png_bytes, "image/png")})
    assert second.status_code == 201

    get_resp = client.get("/api/branding/logo")
    assert get_resp.json()["logo_url"] == second.json()["logo_url"]

    from app.config import get_settings
    from pathlib import Path

    branding_dir = Path(get_settings().storage_path) / "branding"
    assert len(list(branding_dir.glob("logo.*"))) == 1  # old file was replaced, not left behind


def test_delete_logo_clears_it(client, tiny_png_bytes):
    client.post("/api/branding/logo", files={"logo": ("logo.png", tiny_png_bytes, "image/png")})
    resp = client.delete("/api/branding/logo")
    assert resp.status_code == 200
    assert resp.json()["logo_url"] is None

    get_resp = client.get("/api/branding/logo")
    assert get_resp.json()["logo_url"] is None
