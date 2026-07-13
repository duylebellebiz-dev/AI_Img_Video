from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models.db_models import SalonBranding
from app.models.schemas import BrandingOut
from app.services import branding_service
from app.services.storage_service import StorageService

router = APIRouter(prefix="/api/branding", tags=["branding"])


def _to_out(logo_path: Path | None) -> BrandingOut:
    return BrandingOut(logo_url=f"/media/branding/{logo_path.name}" if logo_path else None)


@router.get("/logo", response_model=BrandingOut)
def get_logo(db: Session = Depends(get_db)) -> BrandingOut:
    return _to_out(branding_service.get_logo_path(db))


@router.post("/logo", response_model=BrandingOut, status_code=201)
def upload_logo(
    logo: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BrandingOut:
    storage = StorageService(settings)
    logo_path = branding_service.set_logo(db, storage, logo)
    return _to_out(logo_path)


@router.delete("/logo", response_model=BrandingOut)
def delete_logo(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> BrandingOut:
    storage = StorageService(settings)
    for existing in storage.branding_dir().glob("logo.*"):
        storage.r2.delete_file(storage._key_for(existing))
        existing.unlink(missing_ok=True)
    branding = db.get(SalonBranding, SalonBranding.SINGLETON_ID)
    if branding is not None:
        branding.logo_path = None
        db.commit()
    return _to_out(None)
