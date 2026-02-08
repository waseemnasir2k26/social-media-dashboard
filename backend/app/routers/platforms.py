from fastapi import APIRouter
from app.services import get_social_media_manager, get_scheduler_service
from app.config import get_settings

router = APIRouter(prefix="/platforms", tags=["Platforms"])

settings = get_settings()


@router.get("/status", response_model=dict)
async def get_platform_status():
    """Get the configuration status of all social media platforms."""
    manager = get_social_media_manager()
    enabled = manager.get_enabled_platforms()

    # Check OAuth configuration (client ID available)
    oauth_configured = {
        "linkedin": bool(settings.linkedin_client_id),
        "twitter": bool(settings.twitter_api_key),
        "facebook": bool(settings.facebook_app_id),
        "instagram": bool(settings.facebook_app_id),  # Uses Facebook OAuth
    }

    # Format response to match frontend expectations
    platforms = {
        "linkedin": {
            "connected": enabled.get("linkedin", False),
            "oauth_configured": oauth_configured["linkedin"],
        },
        "twitter": {
            "connected": enabled.get("twitter", False),
            "oauth_configured": oauth_configured["twitter"],
        },
        "facebook": {
            "connected": enabled.get("facebook", False),
            "oauth_configured": oauth_configured["facebook"],
        },
        "instagram": {
            "connected": enabled.get("instagram", False),
            "oauth_configured": oauth_configured["instagram"],
        },
    }

    return {
        "platforms": platforms,
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
