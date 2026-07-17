from types import SimpleNamespace

import pytest

from app.config import Settings
from app.services import usage_service


@pytest.fixture
def db_session():
    from app.database import Base, SessionLocal, engine
    from app.models.db_models import ApiUsageRecord

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        session.query(ApiUsageRecord).delete()
        session.commit()
        yield session
    finally:
        session.close()


def _settings(**overrides) -> Settings:
    defaults = {
        "anthropic_input_price_per_million_usd": 3.0,
        "anthropic_output_price_per_million_usd": 15.0,
        "gemini_image_price_per_image_usd": 0.03,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_record_anthropic_usage_computes_cost_from_configured_pricing(db_session):
    settings = _settings()
    fake_response = SimpleNamespace(usage=SimpleNamespace(input_tokens=1_000_000, output_tokens=1_000_000))

    usage_service.record_anthropic_usage("build_prompt", "claude-sonnet-5", fake_response, settings)

    from app.models.db_models import ApiUsageRecord

    record = db_session.query(ApiUsageRecord).one()
    assert record.provider == "anthropic"
    assert record.operation == "build_prompt"
    assert record.input_tokens == 1_000_000
    assert record.output_tokens == 1_000_000
    assert record.estimated_cost_usd == pytest.approx(3.0 + 15.0)


def test_record_gemini_usage_computes_cost_per_image(db_session):
    settings = _settings()
    fake_response = SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=50, candidates_token_count=0))

    usage_service.record_gemini_usage("generate_image", "gemini-2.5-flash-image", fake_response, 1, settings)

    from app.models.db_models import ApiUsageRecord

    record = db_session.query(ApiUsageRecord).one()
    assert record.provider == "gemini"
    assert record.image_count == 1
    assert record.estimated_cost_usd == pytest.approx(0.03)


def test_record_usage_never_raises_even_when_reading_usage_fields_fails(db_session):
    class _BrokenUsage:
        @property
        def input_tokens(self):
            raise RuntimeError("boom")

    class _BrokenResponse:
        usage = _BrokenUsage()

    # Must be swallowed and logged, not propagated — usage recording must
    # never break the actual generation pipeline.
    usage_service.record_anthropic_usage("build_prompt", "claude-sonnet-5", _BrokenResponse(), _settings())

    from app.models.db_models import ApiUsageRecord

    assert db_session.query(ApiUsageRecord).count() == 0


def test_get_monthly_summary_aggregates_across_providers(db_session):
    settings = _settings()
    usage_service.record_anthropic_usage(
        "build_prompt",
        "claude-sonnet-5",
        SimpleNamespace(usage=SimpleNamespace(input_tokens=1_000_000, output_tokens=0)),
        settings,
    )
    usage_service.record_gemini_usage(
        "generate_image",
        "gemini-2.5-flash-image",
        SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=0)),
        2,
        settings,
    )

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    summary = usage_service.get_monthly_summary(db_session, now.year, now.month)

    assert summary["total_requests"] == 2
    assert summary["anthropic_cost_usd"] == pytest.approx(3.0)
    assert summary["gemini_cost_usd"] == pytest.approx(0.06)
    assert summary["total_cost_usd"] == pytest.approx(3.06)
