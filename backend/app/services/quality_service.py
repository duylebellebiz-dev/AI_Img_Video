"""Module 3 — Image Quality Agent.

Scores a freshly generated image against commercial-quality criteria and,
on failure, drives Gemini to regenerate it — capped at `quality_max_retries`
additional attempts (so total attempts = 1 + quality_max_retries) to avoid
infinite loops / runaway API cost. This service owns the generate->score->
retry loop; it never generates images itself (that's ImageService's job).
"""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.config import Settings, get_settings
from app.services.anthropic_utils import extract_text
from app.services.image_service import ImageService
from app.services.media_utils import detect_image_mime_type

_CRITERIA = ["anatomy", "nail_accuracy", "lighting", "background", "realism", "marketing_quality"]

_VISION_RUBRIC = (
    "You are a strict quality-control judge for commercial nail-salon marketing "
    "photos. Score the attached image from 0-100 on each of: anatomy (hand/finger "
    "correctness), nail_accuracy (matches intended design), lighting, background, "
    "realism, marketing_quality (looks like paid advertising photography). "
    "If the image contains ANY visible text, letters, numbers, captions, "
    "watermarks, or logos anywhere in the frame, that is a hard defect: score "
    "both realism and marketing_quality no higher than 20, regardless of how "
    "good the rest of the image looks. "
    "Respond with ONLY a JSON object like "
    '{"anatomy": 90, "nail_accuracy": 85, "lighting": 88, "background": 80, '
    '"realism": 92, "marketing_quality": 87}, no other text.'
)

_CRITERION_FEEDBACK = {
    "anatomy": "the hand and finger anatomy must be accurate — no distorted, missing, or extra fingers",
    "nail_accuracy": "the nail design must match the reference design image precisely in color, pattern, and shape",
    "lighting": "use brighter, more even, soft studio lighting with minimal harsh shadows",
    "background": "use a cleaner, more minimal, uncluttered commercial background",
    "realism": "increase photorealism — avoid artificial, plastic-looking skin or nail textures, and remove any "
    "text, captions, or watermarks from the image",
    "marketing_quality": "elevate the composition and styling to match premium advertising photography, with no "
    "text, captions, watermarks, or logos anywhere in the frame",
}


def _build_retry_feedback(breakdown: dict, threshold: float) -> str:
    """Turns the previous attempt's weak criteria into concrete regeneration
    guidance, so a retry fixes what actually failed instead of re-rolling the
    same prompt and hoping Gemini's stochasticity does better (each retry is
    a full paid Gemini generation, so wasted retries are the single biggest
    cost driver in this pipeline).
    """
    weak = [c for c in _CRITERIA if breakdown.get(c, 100) < threshold]
    if not weak:
        return ""
    notes = "; ".join(_CRITERION_FEEDBACK[c] for c in weak)
    return f" The previous attempt fell short — on this attempt, specifically fix: {notes}."


@dataclass
class QualityResult:
    attempt: int
    passed: bool
    overall: float
    image_path: Path
    breakdown: dict = field(default_factory=dict)
    prompt_used: str = ""


class QualityGateCancelled(RuntimeError):
    def __init__(self, result: QualityResult | None = None):
        super().__init__("Image generation was cancelled by the user.")
        self.result = result


def _mock_score(image_path: Path) -> tuple[float, dict]:
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
    breakdown = {}
    for i, name in enumerate(_CRITERIA):
        chunk = digest[i * 4 : i * 4 + 4]
        breakdown[name] = int(chunk, 16) % 36 + 65  # deterministic 65-100
    overall = round(sum(breakdown.values()) / len(breakdown), 1)
    return overall, breakdown


class QualityService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client = None
        if self.settings.has_anthropic_key:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    @property
    def is_mock(self) -> bool:
        return self._client is None

    def score_image(self, image_path: Path) -> tuple[float, dict]:
        if self.is_mock:
            return _mock_score(image_path)

        import base64

        image_b64 = base64.standard_b64encode(image_path.read_bytes()).decode()
        image_mime_type = detect_image_mime_type(image_path)
        response = self._client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": image_mime_type, "data": image_b64},
                        },
                        {"type": "text", "text": _VISION_RUBRIC},
                    ],
                }
            ],
        )
        text = extract_text(response)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        breakdown = json.loads(match.group(0)) if match else {}
        breakdown = {k: float(breakdown.get(k, 0)) for k in _CRITERIA}
        overall = round(sum(breakdown.values()) / len(breakdown), 1) if breakdown else 0.0
        return overall, breakdown

    def generate_with_quality_gate(
        self,
        image_service: ImageService,
        design_path: Path,
        pose_path: Path,
        prompt: str,
        out_path: Path,
        variation: int = 1,
        should_continue: Callable[[], bool] | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> QualityResult:
        max_attempts = 1 + self.settings.quality_max_retries
        result: QualityResult | None = None
        keep_running = should_continue or (lambda: True)
        current_prompt = prompt

        for attempt in range(1, max_attempts + 1):
            if not keep_running():
                raise QualityGateCancelled(result)

            generated_path, _ = image_service.generate_image(
                design_path,
                pose_path,
                current_prompt,
                variation,
                out_path,
                attempt=attempt,
                width=width,
                height=height,
            )
            if not keep_running():
                result = QualityResult(
                    attempt=attempt,
                    passed=False,
                    overall=0.0,
                    image_path=generated_path,
                    breakdown={},
                    prompt_used=current_prompt,
                )
                raise QualityGateCancelled(result)

            overall, breakdown = self.score_image(generated_path)
            passed = overall >= self.settings.quality_pass_threshold
            result = QualityResult(
                attempt=attempt,
                passed=passed,
                overall=overall,
                image_path=generated_path,
                breakdown=breakdown,
                prompt_used=current_prompt,
            )
            if not keep_running():
                raise QualityGateCancelled(result)
            if passed:
                break
            current_prompt = prompt + _build_retry_feedback(breakdown, self.settings.quality_pass_threshold)

        assert result is not None
        return result
