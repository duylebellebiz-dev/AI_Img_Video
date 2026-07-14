from pathlib import Path

from PIL import Image

# Pillow's JPEG default (quality=75, 2x2 chroma subsampling) is too lossy for
# commercial nail photography — it visibly softens skin texture and gem/rhinestone
# detail. Applied to every in-place re-save below; harmless no-ops for PNG output.
_JPEG_SAVE_KWARGS = {"quality": 95, "subsampling": 0}


def detect_image_mime_type(path: Path) -> str:
    with Image.open(path) as img:
        fmt = (img.format or "").upper()

    format_to_mime = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "GIF": "image/gif",
        "BMP": "image/bmp",
    }

    return format_to_mime.get(fmt, "application/octet-stream")


def extension_for_mime_type(mime_type: str) -> str:
    mime_to_extension = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
    }
    return mime_to_extension.get(mime_type, ".bin")


def validate_size(width: int | None, height: int | None, min_dim: int = 256, max_dim: int = 4096) -> None:
    """Raises ValueError if width/height are missing a partner or out of range.
    Both None (no size constraint) is valid; both set is valid; one-without-
    the-other is not."""
    if (width is None) != (height is None):
        raise ValueError("image_width and image_height must be provided together")
    if width is None or height is None:
        return
    if not (min_dim <= width <= max_dim) or not (min_dim <= height <= max_dim):
        raise ValueError(f"image_width and image_height must each be between {min_dim} and {max_dim}px")


def apply_watermark(image_path: Path, logo_path: Path, margin_ratio: float = 0.03, logo_width_ratio: float = 0.16) -> None:
    """Composites the salon logo onto the bottom-right corner of image_path,
    in place. Pure image compositing (no AI call) so it's free to apply to
    every generated/edited image. Preserves the logo's alpha channel if it
    has one (typical for a transparent-background PNG logo).
    """
    with Image.open(image_path) as base:
        base = base.convert("RGBA")

        with Image.open(logo_path) as logo:
            logo = logo.convert("RGBA")
            target_width = max(1, round(base.width * logo_width_ratio))
            target_height = max(1, round(logo.height * (target_width / logo.width)))
            logo = logo.resize((target_width, target_height), Image.LANCZOS)

            margin = round(base.width * margin_ratio)
            position = (base.width - target_width - margin, base.height - target_height - margin)
            base.alpha_composite(logo, position)

        base.convert("RGB").save(image_path, **_JPEG_SAVE_KWARGS)


def fit_to_size(image_path: Path, width: int, height: int) -> None:
    """Resizes + center-crops the image in place to exactly width x height
    (cover fit — fills the frame with no distortion, cropping any overflow),
    so campaign images match the social-media template the user picked
    regardless of what aspect ratio the model actually returned.
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        src_ratio = img.width / img.height
        target_ratio = width / height

        if src_ratio > target_ratio:
            scaled_height = height
            scaled_width = round(img.width * (height / img.height))
        else:
            scaled_width = width
            scaled_height = round(img.height * (width / img.width))

        img = img.resize((scaled_width, scaled_height), Image.LANCZOS)

        left = (scaled_width - width) // 2
        top = (scaled_height - height) // 2
        img = img.crop((left, top, left + width, top + height))
        img.save(image_path, **_JPEG_SAVE_KWARGS)
