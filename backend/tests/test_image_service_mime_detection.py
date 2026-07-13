from io import BytesIO
from types import SimpleNamespace

from PIL import Image

from app.services.image_service import _extract_and_verify_image


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), color=(10, 20, 30)).save(buf, format="JPEG")
    return buf.getvalue()


def _fake_response(data: bytes, reported_mime_type: str | None):
    part = SimpleNamespace(inline_data=SimpleNamespace(data=data, mime_type=reported_mime_type))
    return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))])


def test_corrects_extension_and_mime_type_when_gemini_mislabels_jpeg_as_png(tmp_path):
    """Regression guard: Gemini has been observed to report inline_data.mime_type
    as image/png for bytes that are actually JPEG-encoded, which made the
    downstream Vision QA call to Claude fail with a media-type mismatch. The
    saved file's real content must win over Gemini's self-reported label."""
    out_path = tmp_path / "some-id.png"
    response = _fake_response(_jpeg_bytes(), reported_mime_type="image/png")

    final_path, mime_type = _extract_and_verify_image(response, out_path)

    assert mime_type == "image/jpeg"
    assert final_path.suffix == ".jpg"
    assert final_path.exists()
    assert not out_path.exists()  # the wrongly-suffixed temp file was renamed away
    assert Image.open(final_path).format == "JPEG"


def test_keeps_reported_mime_type_when_it_matches_actual_content(tmp_path):
    out_path = tmp_path / "some-id.png"
    response = _fake_response(_jpeg_bytes(), reported_mime_type="image/jpeg")

    final_path, mime_type = _extract_and_verify_image(response, out_path)

    assert mime_type == "image/jpeg"
    assert final_path.suffix == ".jpg"


def test_defaults_reported_mime_type_to_png_when_gemini_omits_it(tmp_path):
    out_path = tmp_path / "some-id.png"
    response = _fake_response(_jpeg_bytes(), reported_mime_type=None)

    final_path, mime_type = _extract_and_verify_image(response, out_path)

    # Even with no hint at all, real content still wins.
    assert mime_type == "image/jpeg"
    assert final_path.suffix == ".jpg"


def test_raises_when_response_has_no_inline_image_data(tmp_path):
    import pytest

    out_path = tmp_path / "some-id.png"
    response = SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[]))])

    with pytest.raises(RuntimeError, match="did not contain image data"):
        _extract_and_verify_image(response, out_path)
