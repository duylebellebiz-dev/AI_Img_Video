"""Module 1 support — talks to the Gemini Image API to generate/edit images.

Gemini is responsible for image generation/editing/variation only; it never
decides marketing strategy or scores its own output (see CLAUDE.md #3).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import Settings, get_settings
from app.services.media_utils import detect_image_mime_type, extension_for_mime_type, fit_to_size

# Appended to every real Gemini prompt regardless of who authored it (Claude
# or the mock builder). Gemini image models frequently hallucinate stock-photo
# style watermarks, captions, or lorem-ipsum placeholder text onto "commercial
# advertising photography" style outputs unless explicitly told not to — this
# was observed in production output and is cheaper to forbid here, once, than
# to rely on every prompt author remembering to say it.
_NO_TEXT_SUFFIX = (
    " Do not render any text, letters, numbers, words, captions, watermarks, "
    "logos, or writing of any kind anywhere in the image — the image must be "
    "completely free of overlaid or embedded text."
)


def _mock_generate(
    design_path: Path,
    pose_path: Path,
    prompt: str,
    variation: int,
    attempt: int,
    out_path: Path,
    width: int | None = None,
    height: int | None = None,
) -> tuple[Path, str]:
    """Deterministic placeholder so the pipeline is fully testable without a
    real GEMINI_API_KEY: composites the design + pose thumbnails side by side
    with the prompt text overlaid, so it's visibly a stand-in, not real output.
    """
    canvas = Image.new("RGB", (800, 500), color=(245, 240, 235))
    thumb_size = (360, 360)

    for src_path, x in ((design_path, 20), (pose_path, 420)):
        try:
            with Image.open(src_path) as img:
                img = img.convert("RGB")
                img.thumbnail(thumb_size)
                canvas.paste(img, (x, 20))
        except Exception:
            placeholder = Image.new("RGB", thumb_size, color=(200, 200, 200))
            canvas.paste(placeholder, (x, 20))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()

    label = f"[MOCK GEMINI OUTPUT] variation {variation} attempt {attempt}\n{prompt[:180]}"
    draw.multiline_text((20, 400), label, fill=(30, 30, 30), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG")
    if width and height:
        fit_to_size(out_path, width, height)
    return out_path, "image/png"


def _mock_edit(
    image_path: Path,
    prompt: str,
    attempt: int,
    out_path: Path,
    width: int | None = None,
    height: int | None = None,
) -> tuple[Path, str]:
    """Deterministic placeholder for single-image edits (see _mock_generate)."""
    canvas = Image.new("RGB", (800, 500), color=(245, 240, 235))
    thumb_size = (760, 370)

    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            img.thumbnail(thumb_size)
            canvas.paste(img, (20, 15))
    except Exception:
        placeholder = Image.new("RGB", thumb_size, color=(200, 200, 200))
        canvas.paste(placeholder, (20, 15))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()

    label = f"[MOCK GEMINI EDIT] attempt {attempt}\n{prompt[:180]}"
    draw.multiline_text((20, 400), label, fill=(30, 30, 30), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG")
    if width and height:
        fit_to_size(out_path, width, height)
    return out_path, "image/png"


def _extract_and_verify_image(
    response, out_path: Path, width: int | None = None, height: int | None = None
) -> tuple[Path, str]:
    """Writes the first inline image part to disk and re-detects its real mime
    type from the actual bytes, rather than trusting Gemini's self-reported
    inline_data.mime_type (which has been observed to say "image/png" for
    content that is really a JPEG) — that mismatch is what previously made
    the Vision QA step's Claude call fail with a media-type-mismatch 400.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) is not None:
            reported_mime_type = getattr(part.inline_data, "mime_type", None) or "image/png"
            tmp_path = out_path.with_suffix(extension_for_mime_type(reported_mime_type))
            tmp_path.write_bytes(part.inline_data.data)

            actual_mime_type = detect_image_mime_type(tmp_path)
            final_path = out_path.with_suffix(extension_for_mime_type(actual_mime_type))
            if final_path != tmp_path:
                tmp_path.replace(final_path)
            if width and height:
                fit_to_size(final_path, width, height)
            return final_path, actual_mime_type

    raise RuntimeError("Gemini response did not contain image data")


class ImageService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client = None
        if self.settings.has_gemini_key:
            from google import genai

            self._client = genai.Client(api_key=self.settings.gemini_api_key)

    @property
    def is_mock(self) -> bool:
        return self._client is None

    def generate_image(
        self,
        design_path: Path,
        pose_path: Path,
        prompt: str,
        variation: int,
        out_path: Path,
        attempt: int = 1,
        width: int | None = None,
        height: int | None = None,
    ) -> tuple[Path, str]:
        if self.is_mock:
            return _mock_generate(design_path, pose_path, prompt, variation, attempt, out_path, width, height)

        from google.genai import types

        design_bytes = design_path.read_bytes()
        pose_bytes = pose_path.read_bytes()

        response = self._client.models.generate_content(
            model=self.settings.gemini_image_model,
            contents=[
                prompt + _NO_TEXT_SUFFIX,
                types.Part.from_bytes(data=design_bytes, mime_type=detect_image_mime_type(design_path)),
                types.Part.from_bytes(data=pose_bytes, mime_type=detect_image_mime_type(pose_path)),
            ],
        )

        return _extract_and_verify_image(response, out_path, width, height)

    def edit_image(
        self,
        image_path: Path,
        prompt: str,
        out_path: Path,
        attempt: int = 1,
        width: int | None = None,
        height: int | None = None,
    ) -> tuple[Path, str]:
        """Edits a single uploaded photo per a freeform instruction (as opposed to
        generate_image, which composites a design + pose pair)."""
        if self.is_mock:
            return _mock_edit(image_path, prompt, attempt, out_path, width, height)

        from google.genai import types

        image_bytes = image_path.read_bytes()

        response = self._client.models.generate_content(
            model=self.settings.gemini_image_model,
            contents=[
                prompt + _NO_TEXT_SUFFIX,
                types.Part.from_bytes(data=image_bytes, mime_type=detect_image_mime_type(image_path)),
            ],
        )

        return _extract_and_verify_image(response, out_path, width, height)
