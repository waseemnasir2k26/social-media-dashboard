from fastapi import APIRouter
from app.services import get_social_media_manager, get_scheduler_service

router = APIRouter(prefix="/platforms", tags=["Platforms"])


@router.get("/status", response_model=dict)
async def get_platform_status():
    """Get the configuration status of all social media platforms."""
    manager = get_social_media_manager()
    enabled = manager.get_enabled_platforms()

    return {
        "platforms": enabled,
        "summary": {
            "configured": sum(1 for v in enabled.values() if v),
            "total": len(enabled)
        }
    }


@router.get("/scheduler/jobs", response_model=dict)
async def get_scheduled_jobs():
    """Get all scheduled jobs."""
    scheduler = get_scheduler_service()
    jobs = scheduler.get_scheduled_jobs()

    return {
        "jobs": jobs,
        "total": len(jobs)
    }
