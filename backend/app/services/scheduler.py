from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from typing import Optional, Callable
import logging

from app.models import Post, PostStatus
from app.models.database import async_session
from app.services.social_media import get_social_media_manager
from sqlalchemy import select, and_

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._started = False

    def start(self):
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info("Scheduler started")

            # Add job to check for scheduled posts every minute
            self.scheduler.add_job(
                self.check_scheduled_posts,
                CronTrigger(minute="*"),
                id="check_scheduled_posts",
                replace_existing=True
            )

    def stop(self):
        if self._started:
            self.scheduler.shutdown()
            self._started = False
            logger.info("Scheduler stopped")

    async def check_scheduled_posts(self):
        """Check for posts that need to be published."""
        logger.info("Checking for scheduled posts...")

        async with async_session() as session:
            now = datetime.utcnow()

            # Find posts that are approved/scheduled and due
            query = select(Post).where(
                and_(
                    Post.status.in_([PostStatus.APPROVED.value, PostStatus.SCHEDULED.value]),
                    Post.scheduled_time <= now,
                    Post.scheduled_time.isnot(None)
                )
            )

            result = await session.execute(query)
            posts = result.scalars().all()

            social_manager = get_social_media_manager()

            for post in posts:
                logger.info(f"Publishing post {post.id} to {post.platforms}")

                try:
                    results = await social_manager.post_to_platforms(
                        content=post.content,
                        platforms=post.platforms or ["linkedin"],
                        image_url=post.image_url
                    )

                    # Update post status
                    all_success = all(r.get("success", False) for r in results.values())

                    if all_success:
                        post.status = PostStatus.POSTED.value
                        post.posted_time = datetime.utcnow()
                        post.posted_ids = {
                            platform: result.get("post_id", "")
                            for platform, result in results.items()
                        }
                        logger.info(f"Post {post.id} published successfully")
                    else:
                        # Partial or full failure
                        errors = [
                            f"{p}: {r.get('error', 'Unknown')}"
                            for p, r in results.items()
                            if not r.get("success")
                        ]
                        post.error_message = "; ".join(errors)

                        # If at least one succeeded, mark as posted with errors
                        if any(r.get("success") for r in results.values()):
                            post.status = PostStatus.POSTED.value
                            post.posted_time = datetime.utcnow()
                            post.posted_ids = {
                                platform: result.get("post_id", "")
                                for platform, result in results.items()
                                if result.get("success")
                            }
                        else:
                            post.status = PostStatus.FAILED.value

                        logger.warning(f"Post {post.id} had errors: {post.error_message}")

                    await session.commit()

                except Exception as e:
                    logger.error(f"Error publishing post {post.id}: {e}")
                    post.status = PostStatus.FAILED.value
                    post.error_message = str(e)
                    await session.commit()

    def schedule_post(self, post_id: int, scheduled_time: datetime):
        """Schedule a specific post for publishing."""
        job_id = f"post_{post_id}"

        # Remove existing job if any
        existing_job = self.scheduler.get_job(job_id)
        if existing_job:
            self.scheduler.remove_job(job_id)

        # Don't schedule if time is in the past
        if scheduled_time <= datetime.utcnow():
            logger.warning(f"Cannot schedule post {post_id} - time is in the past")
            return False

        self.scheduler.add_job(
            self._publish_single_post,
            DateTrigger(run_date=scheduled_time),
            args=[post_id],
            id=job_id,
            replace_existing=True
        )

        logger.info(f"Scheduled post {post_id} for {scheduled_time}")
        return True

    async def _publish_single_post(self, post_id: int):
        """Publish a single post by ID."""
        async with async_session() as session:
            result = await session.execute(select(Post).where(Post.id == post_id))
            post = result.scalar_one_or_none()

            if not post:
                logger.error(f"Post {post_id} not found")
                return

            if post.status == PostStatus.POSTED.value:
                logger.info(f"Post {post_id} already published")
                return

            social_manager = get_social_media_manager()

            results = await social_manager.post_to_platforms(
                content=post.content,
                platforms=post.platforms or ["linkedin"],
                image_url=post.image_url
            )

            all_success = all(r.get("success", False) for r in results.values())

            if all_success:
                post.status = PostStatus.POSTED.value
                post.posted_time = datetime.utcnow()
                post.posted_ids = {
                    platform: result.get("post_id", "")
                    for platform, result in results.items()
                }
            else:
                errors = [
                    f"{p}: {r.get('error', 'Unknown')}"
                    for p, r in results.items()
                    if not r.get("success")
                ]
                post.error_message = "; ".join(errors)
                post.status = PostStatus.FAILED.value

            await session.commit()

    def get_scheduled_jobs(self):
        """Get list of scheduled jobs."""
        return [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in self.scheduler.get_jobs()
        ]


# Singleton instance
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service
