from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.models import Post, PostStatus, get_db
from app.services import get_openai_service, get_social_media_manager, get_scheduler_service

router = APIRouter(prefix="/posts", tags=["Posts"])


# Pydantic models for request/response
class GenerateContentRequest(BaseModel):
    content_type: str = "educational"
    topic: Optional[str] = None
    platforms: List[str] = ["linkedin"]
    custom_prompt: Optional[str] = None
    auto_post: bool = False


class CreatePostRequest(BaseModel):
    content: str
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    content_type: str = "custom"
    topic: Optional[str] = None
    platforms: List[str] = ["linkedin"]
    auto_post: bool = False
    scheduled_time: Optional[datetime] = None


class UpdatePostRequest(BaseModel):
    content: Optional[str] = None
    image_url: Optional[str] = None
    platforms: Optional[List[str]] = None
    status: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    auto_post: Optional[bool] = None


class PostResponse(BaseModel):
    id: int
    content: str
    image_url: Optional[str]
    image_prompt: Optional[str]
    content_type: str
    topic: Optional[str]
    status: str
    auto_post: bool
    scheduled_time: Optional[datetime]
    platforms: List[str]
    posted_ids: dict
    posted_time: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/generate", response_model=dict)
async def generate_content(
    request: GenerateContentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate content using AI."""
    openai_service = get_openai_service()

    result = await openai_service.generate_content(
        content_type=request.content_type,
        topic=request.topic,
        platforms=request.platforms,
        custom_prompt=request.custom_prompt
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Content generation failed"))

    # Create post in database
    post = Post(
        content=result["content"],
        image_prompt=result.get("image_prompt", ""),
        content_type=request.content_type,
        topic=request.topic or result.get("topic", ""),
        platforms=request.platforms,
        auto_post=request.auto_post,
        status=PostStatus.PENDING_APPROVAL.value if not request.auto_post else PostStatus.APPROVED.value,
        word_count=len(result["content"].split())
    )

    db.add(post)
    await db.commit()
    await db.refresh(post)

    return {
        "success": True,
        "post": post.to_dict(),
        "generation_result": result
    }


@router.post("/generate-image", response_model=dict)
async def generate_image(prompt: str):
    """Generate an image using DALL-E."""
    openai_service = get_openai_service()
    result = await openai_service.generate_image(prompt)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Image generation failed"))

    return result


@router.post("/", response_model=dict)
async def create_post(
    request: CreatePostRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new post manually."""
    post = Post(
        content=request.content,
        image_url=request.image_url,
        image_prompt=request.image_prompt,
        content_type=request.content_type,
        topic=request.topic,
        platforms=request.platforms,
        auto_post=request.auto_post,
        scheduled_time=request.scheduled_time,
        status=PostStatus.SCHEDULED.value if request.scheduled_time else PostStatus.DRAFT.value,
        word_count=len(request.content.split())
    )

    db.add(post)
    await db.commit()
    await db.refresh(post)

    # Schedule if needed
    if request.scheduled_time:
        scheduler = get_scheduler_service()
        scheduler.schedule_post(post.id, request.scheduled_time)

    return {"success": True, "post": post.to_dict()}


@router.get("/", response_model=dict)
async def list_posts(
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all posts with optional filtering."""
    query = select(Post).order_by(desc(Post.created_at))

    if status:
        query = query.where(Post.status == status)
    if content_type:
        query = query.where(Post.content_type == content_type)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    posts = result.scalars().all()

    return {
        "posts": [p.to_dict() for p in posts],
        "total": len(posts),
        "offset": offset,
        "limit": limit
    }


@router.get("/{post_id}", response_model=dict)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single post by ID."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return {"post": post.to_dict()}


@router.patch("/{post_id}", response_model=dict)
async def update_post(
    post_id: int,
    request: UpdatePostRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if request.content is not None:
        post.content = request.content
        post.word_count = len(request.content.split())
    if request.image_url is not None:
        post.image_url = request.image_url
    if request.platforms is not None:
        post.platforms = request.platforms
    if request.status is not None:
        post.status = request.status
    if request.scheduled_time is not None:
        post.scheduled_time = request.scheduled_time
        # Update scheduler
        scheduler = get_scheduler_service()
        scheduler.schedule_post(post.id, request.scheduled_time)
    if request.auto_post is not None:
        post.auto_post = request.auto_post

    await db.commit()
    await db.refresh(post)

    return {"success": True, "post": post.to_dict()}


@router.post("/{post_id}/approve", response_model=dict)
async def approve_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Approve a post for publishing."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = PostStatus.APPROVED.value
    await db.commit()

    return {"success": True, "post": post.to_dict()}


@router.post("/{post_id}/publish", response_model=dict)
async def publish_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Immediately publish a post to all configured platforms."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.status == PostStatus.POSTED.value:
        raise HTTPException(status_code=400, detail="Post already published")

    social_manager = get_social_media_manager()

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
    else:
        errors = [f"{p}: {r.get('error', 'Unknown')}" for p, r in results.items() if not r.get("success")]
        post.error_message = "; ".join(errors)

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

    await db.commit()
    await db.refresh(post)

    return {
        "success": all_success,
        "post": post.to_dict(),
        "platform_results": results
    }


@router.delete("/{post_id}", response_model=dict)
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await db.delete(post)
    await db.commit()

    return {"success": True, "message": "Post deleted"}
