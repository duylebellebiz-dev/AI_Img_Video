"""Publishing is out of scope for Phase 1 (see CLAUDE.md #6). This is only
the interface shape so the schema/API doesn't need to change once real
Facebook/Instagram (Meta Graph API) and Pinterest (Pinterest API v5)
integrations are added in Phase 4 — no social media calls happen here.
"""

from sqlalchemy.orm import Session

from app.models.db_models import ScheduledPost


class PublishingService:
    def publish(self, db: Session, campaign_id: str, platform: str) -> ScheduledPost:
        """No-op stub: writes a 'draft' row instead of calling any social API.

        `campaign_id` is a `BatchJob.id` for now — there's no separate
        Campaign entity yet in Phase 1.
        """
        post = ScheduledPost(
            batch_job_id=campaign_id,
            platform=platform,
            status="draft",
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post
