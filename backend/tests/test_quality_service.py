from pathlib import Path

from app.config import Settings
from app.services.image_service import ImageService
from app.services.quality_service import QualityService, _build_retry_feedback


def _settings(**overrides) -> Settings:
    return Settings(anthropic_api_key="", gemini_api_key="", **overrides)


def test_mock_scoring_is_deterministic_for_same_bytes(tmp_path, tiny_png_bytes):
    path = tmp_path / "img.png"
    path.write_bytes(tiny_png_bytes)

    quality = QualityService(_settings())
    overall1, breakdown1 = quality.score_image(path)
    overall2, breakdown2 = quality.score_image(path)

    assert overall1 == overall2
    assert breakdown1 == breakdown2
    assert 0 <= overall1 <= 100


def test_passes_immediately_when_score_meets_low_threshold(tmp_path, tiny_png_bytes):
    design = tmp_path / "d.png"
    pose = tmp_path / "p.png"
    design.write_bytes(tiny_png_bytes)
    pose.write_bytes(tiny_png_bytes)
    out = tmp_path / "out.png"

    settings = _settings(quality_pass_threshold=0, quality_max_retries=3)
    quality = QualityService(settings)
    image_service = ImageService(settings)

    result = quality.generate_with_quality_gate(image_service, design, pose, "prompt", out, variation=1)

    assert result.passed is True
    assert result.attempt == 1


def test_stops_after_max_retries_when_threshold_unreachable(tmp_path, tiny_png_bytes):
    design = tmp_path / "d.png"
    pose = tmp_path / "p.png"
    design.write_bytes(tiny_png_bytes)
    pose.write_bytes(tiny_png_bytes)
    out = tmp_path / "out.png"

    # threshold of 101 can never be met (scores are capped at 100) -> must
    # exhaust all attempts without an infinite loop.
    settings = _settings(quality_pass_threshold=101, quality_max_retries=3)
    quality = QualityService(settings)
    image_service = ImageService(settings)

    result = quality.generate_with_quality_gate(image_service, design, pose, "prompt", out, variation=1)

    assert result.passed is False
    assert result.attempt == 1 + settings.quality_max_retries  # 1 initial + 3 retries


def test_retries_produce_different_mock_images(tmp_path, tiny_png_bytes):
    """Regression guard: earlier version reused identical mock bytes on every
    retry attempt, so a failing image could never become a passing one."""
    design = tmp_path / "d.png"
    pose = tmp_path / "p.png"
    design.write_bytes(tiny_png_bytes)
    pose.write_bytes(tiny_png_bytes)
    out1 = tmp_path / "attempt1.png"
    out2 = tmp_path / "attempt2.png"

    settings = _settings()
    image_service = ImageService(settings)
    image_service.generate_image(design, pose, "prompt", variation=1, out_path=out1, attempt=1)
    image_service.generate_image(design, pose, "prompt", variation=1, out_path=out2, attempt=2)

    assert out1.read_bytes() != out2.read_bytes()


def test_build_retry_feedback_is_empty_when_nothing_is_weak():
    breakdown = {"anatomy": 90, "nail_accuracy": 90, "lighting": 90, "background": 90, "realism": 90, "marketing_quality": 90}
    assert _build_retry_feedback(breakdown, threshold=80) == ""


def test_build_retry_feedback_names_only_the_weak_criteria():
    breakdown = {"anatomy": 60, "nail_accuracy": 90, "lighting": 90, "background": 90, "realism": 90, "marketing_quality": 90}
    feedback = _build_retry_feedback(breakdown, threshold=80)
    assert "hand and finger anatomy" in feedback
    assert "nail design must match" not in feedback  # nail_accuracy scored fine, shouldn't be mentioned


def test_generate_with_quality_gate_appends_feedback_to_retry_prompt(tmp_path, tiny_png_bytes, monkeypatch):
    """The core cost-saving behavior: a failed attempt's weak criteria must be
    fed into the next attempt's prompt instead of blindly repeating it."""
    design = tmp_path / "d.png"
    pose = tmp_path / "p.png"
    design.write_bytes(tiny_png_bytes)
    pose.write_bytes(tiny_png_bytes)
    out = tmp_path / "out.png"

    settings = _settings(quality_pass_threshold=80, quality_max_retries=3)
    quality = QualityService(settings)
    image_service = ImageService(settings)

    # Fail attempt 1 on lighting only, then pass on attempt 2.
    responses = iter(
        [
            (50.0, {"anatomy": 90, "nail_accuracy": 90, "lighting": 10, "background": 90, "realism": 90, "marketing_quality": 90}),
            (95.0, {"anatomy": 95, "nail_accuracy": 95, "lighting": 95, "background": 95, "realism": 95, "marketing_quality": 95}),
        ]
    )
    monkeypatch.setattr(quality, "score_image", lambda path: next(responses))

    result = quality.generate_with_quality_gate(image_service, design, pose, "base prompt", out, variation=1)

    assert result.attempt == 2
    assert result.passed is True
    assert result.prompt_used.startswith("base prompt")
    assert "soft studio lighting" in result.prompt_used
    assert "hand and finger anatomy" not in result.prompt_used  # anatomy passed on attempt 1, no feedback needed
