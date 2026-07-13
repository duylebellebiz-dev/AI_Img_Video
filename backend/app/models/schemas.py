from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PairingMode(str, Enum):
    cross = "cross"
    random = "random"
    one_to_one = "one_to_one"


class BatchJobCreateResponse(BaseModel):
    job_id: str
    status: str
    requested_num_images: int
    approved_num_images: int
    progress_total: int
    was_capped: bool
    cap_message: str | None = None


class GeneratedImageOut(BaseModel):
    id: str
    design_filename: str
    pose_filename: str
    variation: int
    prompt_used: str | None
    score: float | None
    score_breakdown: dict | None
    passed: bool
    attempts: int
    status: str
    image_url: str | None

    model_config = {"from_attributes": True}


class BatchJobStatusOut(BaseModel):
    job_id: str
    status: str
    pairing_mode: str
    num_images: int
    description: str
    image_width: int | None
    image_height: int | None
    progress_completed: int
    progress_total: int
    zip_ready: bool
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    images: list[GeneratedImageOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BatchJobCancelResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ImageEditResponse(BaseModel):
    id: str
    status: str
    prompt: str
    prompt_used: str | None
    image_width: int | None
    image_height: int | None
    original_image_url: str | None
    image_url: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EditJobCreateResponse(BaseModel):
    job_id: str
    status: str
    progress_total: int


class EditJobStatusOut(BaseModel):
    job_id: str
    status: str
    prompt: str
    image_width: int | None
    image_height: int | None
    apply_logo: bool
    progress_completed: int
    progress_total: int
    zip_ready: bool
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    edits: list[ImageEditResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class EditJobCancelResponse(BaseModel):
    job_id: str
    status: str
    message: str


class BrandingOut(BaseModel):
    logo_url: str | None
