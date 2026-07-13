import pytest
from PIL import Image

from app.services.media_utils import apply_watermark, fit_to_size, validate_size


def test_validate_size_allows_both_none():
    validate_size(None, None)  # should not raise


def test_validate_size_allows_valid_pair():
    validate_size(1080, 1350)  # should not raise


@pytest.mark.parametrize("width,height", [(1080, None), (None, 1350)])
def test_validate_size_rejects_one_without_the_other(width, height):
    with pytest.raises(ValueError, match="together"):
        validate_size(width, height)


@pytest.mark.parametrize("width,height", [(100, 1350), (1080, 100), (5000, 1350), (1080, 5000)])
def test_validate_size_rejects_out_of_range_dimensions(width, height):
    with pytest.raises(ValueError, match="between"):
        validate_size(width, height)


def test_fit_to_size_produces_exact_dimensions_for_wide_source(tmp_path):
    path = tmp_path / "wide.png"
    Image.new("RGB", (2000, 1000), color=(255, 0, 0)).save(path)

    fit_to_size(path, 1080, 1350)

    with Image.open(path) as img:
        assert img.size == (1080, 1350)


def test_fit_to_size_produces_exact_dimensions_for_tall_source(tmp_path):
    path = tmp_path / "tall.png"
    Image.new("RGB", (500, 2000), color=(0, 255, 0)).save(path)

    fit_to_size(path, 1080, 1920)

    with Image.open(path) as img:
        assert img.size == (1080, 1920)


def test_apply_watermark_keeps_original_image_dimensions(tmp_path):
    image_path = tmp_path / "photo.png"
    Image.new("RGB", (800, 500), color=(240, 240, 240)).save(image_path)
    logo_path = tmp_path / "logo.png"
    Image.new("RGBA", (300, 100), color=(10, 20, 30, 255)).save(logo_path)

    apply_watermark(image_path, logo_path)

    with Image.open(image_path) as img:
        assert img.size == (800, 500)


def test_apply_watermark_draws_logo_pixels_in_bottom_right_corner(tmp_path):
    image_path = tmp_path / "photo.png"
    Image.new("RGB", (800, 500), color=(255, 255, 255)).save(image_path)
    logo_path = tmp_path / "logo.png"
    Image.new("RGBA", (300, 100), color=(255, 0, 0, 255)).save(logo_path)

    apply_watermark(image_path, logo_path)

    # Same geometry apply_watermark computes internally (defaults: margin_ratio=0.03,
    # logo_width_ratio=0.16), sampled at the center of the pasted logo rect.
    target_width = round(800 * 0.16)
    target_height = round(100 * (target_width / 300))
    margin = round(800 * 0.03)
    logo_x = 800 - target_width - margin
    logo_y = 500 - target_height - margin

    with Image.open(image_path) as img:
        img = img.convert("RGB")
        inside_logo_pixel = img.getpixel((logo_x + target_width // 2, logo_y + target_height // 2))
        opposite_corner_pixel = img.getpixel((5, 5))

    assert inside_logo_pixel != (255, 255, 255)  # logo was drawn
    assert opposite_corner_pixel == (255, 255, 255)  # top-left untouched


def test_apply_watermark_respects_transparent_logo_background(tmp_path):
    """A logo with a fully transparent background shouldn't paint a solid
    rectangle over the photo — only the logo's opaque pixels should show."""
    image_path = tmp_path / "photo.png"
    Image.new("RGB", (800, 500), color=(255, 255, 255)).save(image_path)
    logo_path = tmp_path / "logo.png"
    logo = Image.new("RGBA", (300, 100), color=(0, 0, 0, 0))  # fully transparent
    logo.save(logo_path)

    apply_watermark(image_path, logo_path)

    with Image.open(image_path) as img:
        img = img.convert("RGB")
        corner_pixel = img.getpixel((img.width - 5, img.height - 5))

    assert corner_pixel == (255, 255, 255)  # transparent logo left the photo untouched


def test_fit_to_size_crops_center_without_distorting_aspect(tmp_path):
    """A 2:1 source cropped to a 1:1 target should keep the full height and
    trim equally from both sides, not squash the image."""
    path = tmp_path / "banner.png"
    canvas = Image.new("RGB", (200, 100), color=(0, 0, 0))
    for x in range(200):
        for y in range(100):
            canvas.putpixel((x, y), (x % 256, 0, 0))
    canvas.save(path)

    fit_to_size(path, 100, 100)

    with Image.open(path) as img:
        assert img.size == (100, 100)
