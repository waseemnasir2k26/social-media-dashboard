import httpx
import tweepy
from typing import Optional, Dict, Any
from app.config import get_settings
import json

settings = get_settings()


class TwitterService:
    """Twitter/X API Service using Tweepy."""

    def __init__(self):
        self.enabled = all([
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_token_secret
        ])

        if self.enabled:
            self.client = tweepy.Client(
                consumer_key=settings.twitter_api_key,
                consumer_secret=settings.twitter_api_secret,
                access_token=settings.twitter_access_token,
                access_token_secret=settings.twitter_access_token_secret
            )
            # For media uploads
            auth = tweepy.OAuth1UserHandler(
                settings.twitter_api_key,
                settings.twitter_api_secret,
                settings.twitter_access_token,
                settings.twitter_access_token_secret
            )
            self.api = tweepy.API(auth)

    async def post(self, content: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": False, "error": "Twitter not configured"}

        try:
            # Truncate content for Twitter's 280 char limit
            if len(content) > 280:
                content = content[:277] + "..."

            media_ids = None
            if image_path:
                media = self.api.media_upload(image_path)
                media_ids = [media.media_id]

            response = self.client.create_tweet(
                text=content,
                media_ids=media_ids
            )

            return {
                "success": True,
                "post_id": str(response.data["id"]),
                "platform": "twitter"
            }

        except Exception as e:
            return {"success": False, "error": str(e), "platform": "twitter"}


class LinkedInService:
    """LinkedIn API Service."""

    def __init__(self):
        self.enabled = bool(settings.linkedin_access_token)
        self.access_token = settings.linkedin_access_token
        self.base_url = "https://api.linkedin.com/v2"

    async def get_user_id(self) -> Optional[str]:
        """Get the authenticated user's LinkedIn ID."""
        if not self.enabled:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/userinfo",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            if response.status_code == 200:
                return response.json().get("sub")
        return None

    async def post(self, content: str, image_url: Optional[str] = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": False, "error": "LinkedIn not configured"}

        try:
            user_id = await self.get_user_id()
            if not user_id:
                return {"success": False, "error": "Could not get LinkedIn user ID"}

            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0"
                }

                post_data = {
                    "author": f"urn:li:person:{user_id}",
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {
                                "text": content
                            },
                            "shareMediaCategory": "NONE"
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    }
                }

                # If image URL provided, we'd need to upload it first
                # LinkedIn requires a complex image upload process

                response = await client.post(
                    f"{self.base_url}/ugcPosts",
                    headers=headers,
                    json=post_data
                )

                if response.status_code in [200, 201]:
                    return {
                        "success": True,
                        "post_id": response.headers.get("x-restli-id", ""),
                        "platform": "linkedin"
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "platform": "linkedin"
                    }

        except Exception as e:
            return {"success": False, "error": str(e), "platform": "linkedin"}


class FacebookService:
    """Facebook Page API Service."""

    def __init__(self):
        self.enabled = all([
            settings.facebook_page_access_token,
            settings.facebook_page_id
        ])
        self.access_token = settings.facebook_page_access_token
        self.page_id = settings.facebook_page_id
        self.base_url = "https://graph.facebook.com/v18.0"

    async def post(self, content: str, image_url: Optional[str] = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": False, "error": "Facebook not configured"}

        try:
            async with httpx.AsyncClient() as client:
                if image_url:
                    # Post with image
                    response = await client.post(
                        f"{self.base_url}/{self.page_id}/photos",
                        params={
                            "access_token": self.access_token,
                            "url": image_url,
                            "message": content
                        }
                    )
                else:
                    # Text-only post
                    response = await client.post(
                        f"{self.base_url}/{self.page_id}/feed",
                        params={
                            "access_token": self.access_token,
                            "message": content
                        }
                    )

                data = response.json()

                if "id" in data:
                    return {
                        "success": True,
                        "post_id": data["id"],
                        "platform": "facebook"
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("error", {}).get("message", "Unknown error"),
                        "platform": "facebook"
                    }

        except Exception as e:
            return {"success": False, "error": str(e), "platform": "facebook"}


class InstagramService:
    """Instagram API Service (via Facebook Graph API)."""

    def __init__(self):
        self.enabled = all([
            settings.facebook_page_access_token,
            settings.instagram_account_id
        ])
        self.access_token = settings.facebook_page_access_token
        self.ig_user_id = settings.instagram_account_id
        self.base_url = "https://graph.facebook.com/v18.0"

    async def post(self, content: str, image_url: str) -> Dict[str, Any]:
        """
        Instagram requires an image URL for all posts.
        The image must be publicly accessible.
        """
        if not self.enabled:
            return {"success": False, "error": "Instagram not configured"}

        if not image_url:
            return {"success": False, "error": "Instagram requires an image URL", "platform": "instagram"}

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Create media container
                container_response = await client.post(
                    f"{self.base_url}/{self.ig_user_id}/media",
                    params={
                        "access_token": self.access_token,
                        "image_url": image_url,
                        "caption": content
                    }
                )

                container_data = container_response.json()

                if "id" not in container_data:
                    return {
                        "success": False,
                        "error": container_data.get("error", {}).get("message", "Failed to create media container"),
                        "platform": "instagram"
                    }

                container_id = container_data["id"]

                # Step 2: Publish the container
                publish_response = await client.post(
                    f"{self.base_url}/{self.ig_user_id}/media_publish",
                    params={
                        "access_token": self.access_token,
                        "creation_id": container_id
                    }
                )

                publish_data = publish_response.json()

                if "id" in publish_data:
                    return {
                        "success": True,
                        "post_id": publish_data["id"],
                        "platform": "instagram"
                    }
                else:
                    return {
                        "success": False,
                        "error": publish_data.get("error", {}).get("message", "Failed to publish"),
                        "platform": "instagram"
                    }

        except Exception as e:
            return {"success": False, "error": str(e), "platform": "instagram"}


class SocialMediaManager:
    """Unified manager for all social media platforms."""

    def __init__(self):
        self.twitter = TwitterService()
        self.linkedin = LinkedInService()
        self.facebook = FacebookService()
        self.instagram = InstagramService()

    def get_enabled_platforms(self) -> Dict[str, bool]:
        """Return which platforms are configured."""
        return {
            "twitter": self.twitter.enabled,
            "linkedin": self.linkedin.enabled,
            "facebook": self.facebook.enabled,
            "instagram": self.instagram.enabled
        }

    async def post_to_platforms(
        self,
        content: str,
        platforms: list[str],
        image_url: Optional[str] = None,
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post content to multiple platforms."""
        results = {}

        for platform in platforms:
            if platform == "twitter" and self.twitter.enabled:
                results["twitter"] = await self.twitter.post(content, image_path)

            elif platform == "linkedin" and self.linkedin.enabled:
                results["linkedin"] = await self.linkedin.post(content, image_url)

            elif platform == "facebook" and self.facebook.enabled:
                results["facebook"] = await self.facebook.post(content, image_url)

            elif platform == "instagram" and self.instagram.enabled:
                if image_url:
                    results["instagram"] = await self.instagram.post(content, image_url)
                else:
                    results["instagram"] = {
                        "success": False,
                        "error": "Instagram requires an image",
                        "platform": "instagram"
                    }
            else:
                results[platform] = {
                    "success": False,
                    "error": f"{platform} not configured or not recognized",
                    "platform": platform
                }

        return results


# Singleton instance
_social_media_manager: Optional[SocialMediaManager] = None


def get_social_media_manager() -> SocialMediaManager:
    global _social_media_manager
    if _social_media_manager is None:
        _social_media_manager = SocialMediaManager()
    return _social_media_manager
