"""Module 2 — Prompt Intelligence.

Turns the user's short raw description into a detailed, optimized prompt for
the Gemini Image API: composition, lighting, background, commercial nail
photography style. Claude never generates images itself (see CLAUDE.md #3).
"""

from math import gcd

from app.config import Settings, get_settings
from app.services.anthropic_utils import extract_text

_NAMED_ASPECT_RATIOS = {
    "1:1": "square feed post",
    "4:5": "portrait, ideal for an Instagram/Facebook feed post",
    "9:16": "vertical, ideal for Instagram/Facebook Stories and Reels",
    "16:9": "landscape/widescreen",
}


def _size_hint(width: int | None, height: int | None) -> str:
    """Describes the target output size/aspect ratio for the prompt, so Gemini
    frames the shot to match rather than leaving it to a later center-crop."""
    if not width or not height:
        return ""

    divisor = gcd(width, height)
    ratio = f"{width // divisor}:{height // divisor}"
    descriptor = _NAMED_ASPECT_RATIOS.get(ratio)
    ratio_text = f"{ratio} aspect ratio{', ' + descriptor if descriptor else ''}"
    return f" Compose and frame the shot for a {width}x{height}px output ({ratio_text})."


_SYSTEM_PROMPT = (
    "You are a commercial nail-photography prompt engineer for a nail salon "
    "marketing platform. Given a short campaign description and a reference "
    "nail design image plus a hand pose image, write ONE detailed image "
    "generation prompt for an AI image editor. The prompt must: preserve the "
    "hand's exact anatomy and pose from the pose reference, replace only the "
    "nails with the design from the design reference, specify natural/soft "
    "studio lighting, a minimalist commercial background, and high-end "
    "advertising photography style. The prompt must explicitly instruct that "
    "the image contain NO text, letters, numbers, captions, watermarks, or "
    "logos anywhere in the frame. Output ONLY the prompt text, no preamble."
)


def _mock_prompt(
    description: str,
    design_filename: str,
    pose_filename: str,
    variation: int,
    width: int | None = None,
    height: int | None = None,
) -> str:
    base = description.strip() or "elegant nail design"
    return (
        f"Commercial nail photography of '{base}', apply the nail design from "
        f"{design_filename} onto the hand in {pose_filename} while preserving exact "
        f"finger anatomy and pose. Soft natural studio lighting, minimalist neutral "
        f"background, shallow depth of field, high-end advertising style, ultra "
        f"realistic, 4k product photography. (variation {variation})"
        f"{_size_hint(width, height)}"
    )


_EDIT_SYSTEM_PROMPT = (
    "You are a photo-editing prompt engineer for a nail salon marketing platform. "
    "Given a user's short edit instruction and the filename of a reference photo, "
    "rewrite it into ONE detailed instruction for an AI image editor. Preserve "
    "everything in the original photo not mentioned by the user (subject, pose, "
    "background, framing) and apply only the requested change, in clear, "
    "unambiguous, specific language suitable for a commercial photo-editing model. "
    "Unless the user's instruction is specifically about adding text, the rewritten "
    "instruction must explicitly forbid adding any text, captions, watermarks, or "
    "logos to the image. Output ONLY the instruction text, no preamble."
)


def _mock_edit_prompt(user_prompt: str, filename: str, width: int | None = None, height: int | None = None) -> str:
    base = user_prompt.strip() or "improve overall photo quality"
    return (
        f"Edit the photo '{filename}': {base}. Preserve all other details of the "
        f"original image exactly (subject, pose, background, framing) unless stated "
        f"otherwise. Keep the result photorealistic and consistent with commercial "
        f"nail-salon marketing photography.{_size_hint(width, height)}"
    )


class AgentService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client = None
        if self.settings.has_anthropic_key:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    @property
    def is_mock(self) -> bool:
        return self._client is None

    def build_prompt(
        self,
        description: str,
        design_filename: str,
        pose_filename: str,
        variation: int = 1,
        width: int | None = None,
        height: int | None = None,
    ) -> str:
        if self.is_mock:
            return _mock_prompt(description, design_filename, pose_filename, variation, width, height)

        user_message = (
            f"Campaign description: {description}\n"
            f"Design reference file: {design_filename}\n"
            f"Pose reference file: {pose_filename}\n"
            f"Variation number: {variation} (make this variation distinct in framing "
            f"or lighting mood from other variations of the same pair)"
            f"{_size_hint(width, height)}"
        )
        response = self._client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=400,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return extract_text(response)

    def refine_edit_prompt(
        self, user_prompt: str, filename: str, width: int | None = None, height: int | None = None
    ) -> str:
        if self.is_mock:
            return _mock_edit_prompt(user_prompt, filename, width, height)

        user_message = (
            f"Reference photo filename: {filename}\n"
            f"User's edit instruction: {user_prompt}"
            f"{_size_hint(width, height)}"
        )
        response = self._client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=300,
            system=_EDIT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return extract_text(response)
