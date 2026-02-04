from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Enum
from sqlalchemy.sql import func
from app.models.database import Base
import enum
from datetime import datetime


class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"


class ContentType(str, enum.Enum):
    EDUCATIONAL = "educational"
    MOTIVATION = "motivation"
    PROMOTIONAL = "promotional"
    ENGAGEMENT = "engagement"
    NEWS = "news"
    CUSTOM = "custom"


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)

    # Content
    content = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    image_prompt = Column(Text, nullable=True)

    # Metadata
    content_type = Column(String(50), default=ContentType.CUSTOM.value)
    topic = Column(String(255), nullable=True)
    hook_type = Column(String(50), nullable=True)
    word_count = Column(Integer, default=0)

    # Status & Scheduling
    status = Column(String(50), default=PostStatus.DRAFT.value)
    auto_post = Column(Boolean, default=False)  # True = auto post, False = needs approval
    scheduled_time = Column(DateTime, nullable=True)

    # Platform targeting (JSON array of platforms)
    platforms = Column(JSON, default=["linkedin"])  # ["linkedin", "twitter", "facebook", "instagram"]

    # Posted info (JSON object with platform -> post_id mapping)
    posted_ids = Column(JSON, default={})
    posted_time = Column(DateTime, nullable=True)

    # Errors (if any)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "image_url": self.image_url,
            "image_prompt": self.image_prompt,
            "content_type": self.content_type,
            "topic": self.topic,
            "hook_type": self.hook_type,
            "word_count": self.word_count,
            "status": self.status,
            "auto_post": self.auto_post,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "platforms": self.platforms or [],
            "posted_ids": self.posted_ids or {},
            "posted_time": self.posted_time.isoformat() if self.posted_time else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ScheduleConfig(Base):
    __tablename__ = "schedule_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    content_type = Column(String(50), nullable=False)
    platforms = Column(JSON, default=["linkedin"])
    cron_expression = Column(String(100), nullable=True)  # e.g., "0 7 * * *" for 7 AM daily
    hour = Column(Integer, nullable=True)  # Simple: post at this hour
    is_active = Column(Boolean, default=True)
    auto_generate = Column(Boolean, default=True)  # Auto generate content
    auto_post = Column(Boolean, default=False)  # Auto post without approval
    created_at = Column(DateTime, server_default=func.now())
