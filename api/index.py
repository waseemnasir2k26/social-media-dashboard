from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode
import os
import json
import httpx
import secrets
import base64
import hashlib
import asyncio

# Supabase (optional)
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

# Initialize FastAPI
app = FastAPI(title="Social Media Dashboard API - Simple Posting Tool")

# Initialize Supabase (if configured and available)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase: Optional[Any] = None

if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Failed to initialize Supabase: {e}")

# Get base URL for callbacks
BASE_URL = os.environ.get("VERCEL_URL", "")
if BASE_URL and not BASE_URL.startswith("http"):
    BASE_URL = f"https://{BASE_URL}"
if not BASE_URL:
    BASE_URL = "http://localhost:8000"

FRONTEND_URL = os.environ.get("FRONTEND_URL", BASE_URL)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Token & Post Storage ============
# Uses Supabase if configured, otherwise falls back to in-memory

tokens_cache: Dict[str, Dict[str, Any]] = {}
posts_cache: Dict[int, dict] = {}
post_counter = 0

def get_stored_tokens() -> Dict[str, Any]:
    """Get tokens from Supabase, cache, or environment."""
    global tokens_cache

    # Try Supabase first
    if supabase:
        try:
            result = supabase.table("platform_tokens").select("*").execute()
            tokens = {}
            for row in result.data:
                platform = row["platform"]
                tokens[platform] = {
                    "access_token": row.get("access_token", ""),
                    "refresh_token": row.get("refresh_token", ""),
                    "account_id": row.get("account_id", ""),
                    "account_name": row.get("account_name", ""),
                    "page_id": row.get("page_id", ""),
                    "page_name": row.get("page_name", ""),
                    "connected": bool(row.get("access_token")),
                }

            # Fill in missing platforms with defaults
            all_platforms = ["linkedin", "twitter", "facebook", "instagram_1", "instagram_2", "youtube"]
            for p in all_platforms:
                if p not in tokens:
                    tokens[p] = {"connected": False}

            return tokens
        except Exception as e:
            print(f"Supabase error: {e}")

    # Check memory cache
    if tokens_cache:
        return tokens_cache

    # Fall back to environment variables
    return {
        "linkedin": {
            "access_token": os.environ.get("LINKEDIN_ACCESS_TOKEN", ""),
            "connected": bool(os.environ.get("LINKEDIN_ACCESS_TOKEN")),
        },
        "twitter": {
            "access_token": os.environ.get("TWITTER_ACCESS_TOKEN", ""),
            "access_token_secret": os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", ""),
            "connected": bool(os.environ.get("TWITTER_ACCESS_TOKEN")),
        },
        "facebook": {
            "access_token": os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", ""),
            "page_id": os.environ.get("FACEBOOK_PAGE_ID", ""),
            "connected": bool(os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")),
        },
        "instagram_1": {
            "access_token": os.environ.get("INSTAGRAM_1_ACCESS_TOKEN", os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")),
            "account_id": os.environ.get("INSTAGRAM_1_ACCOUNT_ID", os.environ.get("INSTAGRAM_ACCOUNT_ID", "")),
            "account_name": os.environ.get("INSTAGRAM_1_NAME", "Instagram Account 1"),
            "connected": bool(os.environ.get("INSTAGRAM_1_ACCOUNT_ID") or os.environ.get("INSTAGRAM_ACCOUNT_ID")),
        },
        "instagram_2": {
            "access_token": os.environ.get("INSTAGRAM_2_ACCESS_TOKEN", ""),
            "account_id": os.environ.get("INSTAGRAM_2_ACCOUNT_ID", ""),
            "account_name": os.environ.get("INSTAGRAM_2_NAME", "Instagram Account 2"),
            "connected": bool(os.environ.get("INSTAGRAM_2_ACCOUNT_ID")),
        },
        "youtube": {
            "access_token": os.environ.get("YOUTUBE_ACCESS_TOKEN", ""),
            "refresh_token": os.environ.get("YOUTUBE_REFRESH_TOKEN", ""),
            "channel_id": os.environ.get("YOUTUBE_CHANNEL_ID", ""),
            "connected": bool(os.environ.get("YOUTUBE_ACCESS_TOKEN")),
        },
    }

def save_token(platform: str, token_data: Dict[str, Any]):
    """Save token to Supabase or cache."""
    global tokens_cache

    # Save to Supabase if configured
    if supabase:
        try:
            data = {
                "platform": platform,
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "account_id": token_data.get("account_id"),
                "account_name": token_data.get("account_name"),
                "page_id": token_data.get("page_id"),
                "page_name": token_data.get("page_name"),
                "updated_at": datetime.utcnow().isoformat(),
            }
            # Upsert (insert or update)
            supabase.table("platform_tokens").upsert(data, on_conflict="platform").execute()
        except Exception as e:
            print(f"Supabase save error: {e}")

    # Also update cache
    tokens_cache[platform] = {**token_data, "connected": True}

def delete_token(platform: str):
    """Delete token from Supabase and cache."""
    global tokens_cache

    if supabase:
        try:
            supabase.table("platform_tokens").delete().eq("platform", platform).execute()
        except Exception as e:
            print(f"Supabase delete error: {e}")

    if platform in tokens_cache:
        del tokens_cache[platform]


# ============ OAuth Configuration ============

OAUTH_CONFIG = {
    "linkedin": {
        "client_id": os.environ.get("LINKEDIN_CLIENT_ID", ""),
        "client_secret": os.environ.get("LINKEDIN_CLIENT_SECRET", ""),
        "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "scopes": ["openid", "profile", "w_member_social"],
    },
    "twitter": {
        "client_id": os.environ.get("TWITTER_CLIENT_ID", ""),
        "client_secret": os.environ.get("TWITTER_CLIENT_SECRET", ""),
        "auth_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "scopes": ["tweet.read", "tweet.write", "users.read", "offline.access"],
    },
    "facebook": {
        "client_id": os.environ.get("FACEBOOK_APP_ID", ""),
        "client_secret": os.environ.get("FACEBOOK_APP_SECRET", ""),
        "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "scopes": ["pages_manage_posts", "pages_read_engagement", "instagram_basic", "instagram_content_publish", "business_management"],
    },
    "youtube": {
        "client_id": os.environ.get("YOUTUBE_CLIENT_ID", os.environ.get("GOOGLE_CLIENT_ID", "")),
        "client_secret": os.environ.get("YOUTUBE_CLIENT_SECRET", os.environ.get("GOOGLE_CLIENT_SECRET", "")),
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"],
    },
}

# Store OAuth states for CSRF protection
oauth_states: Dict[str, str] = {}
pkce_verifiers: Dict[str, str] = {}


# ============ Models ============

class CreatePostRequest(BaseModel):
    content: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    platforms: List[str] = ["linkedin"]
    scheduled_time: Optional[str] = None


class UpdatePostRequest(BaseModel):
    content: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    platforms: Optional[List[str]] = None
    status: Optional[str] = None
    scheduled_time: Optional[str] = None


# ============ OAuth Helper Functions ============

def generate_pkce_pair():
    """Generate PKCE code verifier and challenge."""
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    return verifier, challenge


# ============ OAuth Routes ============

@app.get("/api/auth/{platform}/connect")
async def oauth_connect(platform: str, request: Request):
    """Initiate OAuth flow for a platform."""
    # Handle instagram variants
    actual_platform = "facebook" if platform.startswith("instagram") else platform

    if actual_platform not in OAUTH_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")

    config = OAUTH_CONFIG[actual_platform]

    if not config["client_id"]:
        raise HTTPException(
            status_code=400,
            detail=f"{platform} OAuth not configured. Add {actual_platform.upper()}_CLIENT_ID to environment."
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = platform

    # Build callback URL
    callback_url = f"{BASE_URL}/api/auth/{platform}/callback"

    # Build authorization URL
    params = {
        "client_id": config["client_id"],
        "redirect_uri": callback_url,
        "response_type": "code",
        "state": state,
        "scope": " ".join(config["scopes"]),
    }

    # Twitter requires PKCE
    if platform == "twitter":
        verifier, challenge = generate_pkce_pair()
        pkce_verifiers[state] = verifier
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"

    # YouTube/Google specific
    if platform == "youtube":
        params["access_type"] = "offline"
        params["prompt"] = "consent"

    auth_url = f"{config['auth_url']}?{urlencode(params)}"

    return {"auth_url": auth_url}


@app.get("/api/auth/{platform}/callback")
async def oauth_callback(platform: str, code: str = None, state: str = None, error: str = None):
    """Handle OAuth callback."""

    # Handle errors
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error={error}")

    if not code or not state:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error=missing_params")

    # Verify state
    if state not in oauth_states or oauth_states[state] != platform:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error=invalid_state")

    del oauth_states[state]

    # Handle instagram variants
    actual_platform = "facebook" if platform.startswith("instagram") else platform
    config = OAUTH_CONFIG[actual_platform]
    callback_url = f"{BASE_URL}/api/auth/{platform}/callback"

    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_data = {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "redirect_uri": callback_url,
                "grant_type": "authorization_code",
            }

            # Twitter requires PKCE verifier
            if platform == "twitter" and state in pkce_verifiers:
                token_data["code_verifier"] = pkce_verifiers[state]
                del pkce_verifiers[state]

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            # Twitter requires Basic auth
            if platform == "twitter":
                credentials = base64.b64encode(
                    f"{config['client_id']}:{config['client_secret']}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {credentials}"
                del token_data["client_secret"]

            response = await client.post(
                config["token_url"],
                data=token_data,
                headers=headers
            )

            if response.status_code != 200:
                return RedirectResponse(f"{FRONTEND_URL}/settings?error=token_exchange_failed&details={response.text[:100]}")

            tokens = response.json()

            # Process based on platform
            if platform == "linkedin":
                save_token("linkedin", {
                    "access_token": tokens.get("access_token"),
                    "expires_in": tokens.get("expires_in"),
                })

            elif platform == "twitter":
                save_token("twitter", {
                    "access_token": tokens.get("access_token"),
                    "refresh_token": tokens.get("refresh_token"),
                })

            elif platform == "youtube":
                save_token("youtube", {
                    "access_token": tokens.get("access_token"),
                    "refresh_token": tokens.get("refresh_token"),
                })

            elif platform == "facebook" or platform.startswith("instagram"):
                # Get long-lived token
                long_token_response = await client.get(
                    "https://graph.facebook.com/v18.0/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": config["client_id"],
                        "client_secret": config["client_secret"],
                        "fb_exchange_token": tokens.get("access_token"),
                    }
                )
                long_token = long_token_response.json().get("access_token", tokens.get("access_token"))

                # Get pages
                pages_response = await client.get(
                    "https://graph.facebook.com/v18.0/me/accounts",
                    params={"access_token": long_token}
                )
                pages = pages_response.json().get("data", [])

                if pages:
                    page = pages[0]  # Use first page

                    if platform == "facebook":
                        save_token("facebook", {
                            "access_token": page.get("access_token"),
                            "page_id": page.get("id"),
                            "page_name": page.get("name"),
                        })

                    # Get Instagram accounts linked to pages
                    ig_accounts = []
                    for p in pages:
                        ig_response = await client.get(
                            f"https://graph.facebook.com/v18.0/{p['id']}",
                            params={
                                "fields": "instagram_business_account{id,username}",
                                "access_token": p.get("access_token"),
                            }
                        )
                        ig_data = ig_response.json()
                        ig_account = ig_data.get("instagram_business_account", {})
                        if ig_account:
                            ig_accounts.append({
                                "account_id": ig_account.get("id"),
                                "username": ig_account.get("username", "Unknown"),
                                "access_token": p.get("access_token"),
                            })

                    # Save Instagram accounts
                    if platform.startswith("instagram") or platform == "facebook":
                        if len(ig_accounts) >= 1:
                            save_token("instagram_1", {
                                "access_token": ig_accounts[0]["access_token"],
                                "account_id": ig_accounts[0]["account_id"],
                                "account_name": ig_accounts[0]["username"],
                            })
                        if len(ig_accounts) >= 2:
                            save_token("instagram_2", {
                                "access_token": ig_accounts[1]["access_token"],
                                "account_id": ig_accounts[1]["account_id"],
                                "account_name": ig_accounts[1]["username"],
                            })

            return RedirectResponse(f"{FRONTEND_URL}/settings?connected={platform}")

    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error={str(e)[:100]}")


@app.post("/api/auth/{platform}/disconnect")
async def oauth_disconnect(platform: str):
    """Disconnect a platform."""
    delete_token(platform)
    return {"success": True, "message": f"{platform} disconnected"}


# ============ Social Media Posting ============

async def post_to_linkedin(content: str, image_url: Optional[str] = None) -> dict:
    tokens = get_stored_tokens().get("linkedin", {})
    access_token = tokens.get("access_token")

    if not access_token:
        return {"success": False, "error": "LinkedIn not connected"}

    try:
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if user_response.status_code != 200:
                return {"success": False, "error": "Token expired. Please reconnect LinkedIn."}

            user_id = user_response.json().get("sub")

            post_data = {
                "author": f"urn:li:person:{user_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content},
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }

            response = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0"
                },
                json=post_data
            )

            if response.status_code in [200, 201]:
                return {"success": True, "post_id": response.headers.get("x-restli-id", "")}
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def post_to_twitter(content: str, image_url: Optional[str] = None) -> dict:
    tokens = get_stored_tokens().get("twitter", {})
    access_token = tokens.get("access_token")

    if not access_token:
        return {"success": False, "error": "Twitter not connected"}

    try:
        if len(content) > 280:
            content = content[:277] + "..."

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.twitter.com/2/tweets",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"text": content}
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return {"success": True, "post_id": data.get("data", {}).get("id", "")}
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def post_to_facebook(content: str, image_url: Optional[str] = None, video_url: Optional[str] = None) -> dict:
    tokens = get_stored_tokens().get("facebook", {})
    access_token = tokens.get("access_token")
    page_id = tokens.get("page_id")

    if not access_token or not page_id:
        return {"success": False, "error": "Facebook not connected"}

    try:
        async with httpx.AsyncClient() as client:
            if video_url:
                # Post video
                response = await client.post(
                    f"https://graph.facebook.com/v18.0/{page_id}/videos",
                    params={
                        "access_token": access_token,
                        "file_url": video_url,
                        "description": content
                    }
                )
            elif image_url:
                # Post with image
                response = await client.post(
                    f"https://graph.facebook.com/v18.0/{page_id}/photos",
                    params={
                        "access_token": access_token,
                        "url": image_url,
                        "message": content
                    }
                )
            else:
                # Text-only post
                response = await client.post(
                    f"https://graph.facebook.com/v18.0/{page_id}/feed",
                    params={
                        "access_token": access_token,
                        "message": content
                    }
                )

            data = response.json()
            if "id" in data:
                return {"success": True, "post_id": data["id"]}
            return {"success": False, "error": data.get("error", {}).get("message", "Unknown error")}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def post_to_instagram(account_key: str, content: str, image_url: str = None, video_url: str = None) -> dict:
    """Post to Instagram. Supports instagram_1 or instagram_2."""
    tokens = get_stored_tokens().get(account_key, {})
    access_token = tokens.get("access_token")
    account_id = tokens.get("account_id")

    if not access_token or not account_id:
        return {"success": False, "error": f"{account_key} not connected"}

    if not image_url and not video_url:
        return {"success": False, "error": "Instagram requires an image or video"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Create media container
            params = {
                "access_token": access_token,
                "caption": content
            }

            if video_url:
                params["video_url"] = video_url
                params["media_type"] = "REELS"
            else:
                params["image_url"] = image_url

            container_response = await client.post(
                f"https://graph.facebook.com/v18.0/{account_id}/media",
                params=params
            )
            container_data = container_response.json()

            if "id" not in container_data:
                return {"success": False, "error": container_data.get("error", {}).get("message", "Failed")}

            container_id = container_data["id"]

            # Step 2: Wait for video processing (if video)
            if video_url:
                for _ in range(30):  # Wait up to 5 minutes
                    status_response = await client.get(
                        f"https://graph.facebook.com/v18.0/{container_id}",
                        params={"access_token": access_token, "fields": "status_code"}
                    )
                    status = status_response.json().get("status_code")
                    if status == "FINISHED":
                        break
                    elif status == "ERROR":
                        return {"success": False, "error": "Video processing failed"}
                    await asyncio.sleep(10)

            # Step 3: Publish the container
            publish_response = await client.post(
                f"https://graph.facebook.com/v18.0/{account_id}/media_publish",
                params={"access_token": access_token, "creation_id": container_id}
            )
            publish_data = publish_response.json()

            if "id" in publish_data:
                return {"success": True, "post_id": publish_data["id"]}
            return {"success": False, "error": publish_data.get("error", {}).get("message", "Failed")}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def post_to_youtube(content: str, video_url: str, title: str = None) -> dict:
    """Post video to YouTube."""
    tokens = get_stored_tokens().get("youtube", {})
    access_token = tokens.get("access_token")

    if not access_token:
        return {"success": False, "error": "YouTube not connected"}

    if not video_url:
        return {"success": False, "error": "YouTube requires a video URL"}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # For YouTube, we need to download the video first and upload
            # This is a simplified version - full implementation would need resumable uploads

            video_title = title or content[:100] if content else "Video"

            # YouTube Data API video insert
            metadata = {
                "snippet": {
                    "title": video_title,
                    "description": content,
                    "categoryId": "22"  # People & Blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                }
            }

            # Note: Full YouTube upload requires multipart upload
            # For now, return guidance
            return {
                "success": False,
                "error": "YouTube upload requires video file upload. Use YouTube Studio for now.",
                "note": "Full YouTube API integration coming soon"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ API Routes ============

@app.get("/api")
async def root():
    return {"message": "Social Media Dashboard API - Simple Posting Tool", "status": "running"}


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/platforms/status")
async def get_platform_status():
    tokens = get_stored_tokens()

    # Check OAuth configuration
    oauth_configured = {
        "linkedin": bool(OAUTH_CONFIG["linkedin"]["client_id"]),
        "twitter": bool(OAUTH_CONFIG["twitter"]["client_id"]),
        "facebook": bool(OAUTH_CONFIG["facebook"]["client_id"]),
        "instagram_1": bool(OAUTH_CONFIG["facebook"]["client_id"]),
        "instagram_2": bool(OAUTH_CONFIG["facebook"]["client_id"]),
        "youtube": bool(OAUTH_CONFIG["youtube"]["client_id"]),
    }

    return {
        "platforms": {
            "linkedin": {
                "connected": tokens.get("linkedin", {}).get("connected", False),
                "oauth_configured": oauth_configured["linkedin"],
            },
            "twitter": {
                "connected": tokens.get("twitter", {}).get("connected", False),
                "oauth_configured": oauth_configured["twitter"],
            },
            "facebook": {
                "connected": tokens.get("facebook", {}).get("connected", False),
                "oauth_configured": oauth_configured["facebook"],
                "page_name": tokens.get("facebook", {}).get("page_name", ""),
            },
            "instagram_1": {
                "connected": tokens.get("instagram_1", {}).get("connected", False),
                "oauth_configured": oauth_configured["instagram_1"],
                "account_name": tokens.get("instagram_1", {}).get("account_name", "Instagram 1"),
            },
            "instagram_2": {
                "connected": tokens.get("instagram_2", {}).get("connected", False),
                "oauth_configured": oauth_configured["instagram_2"],
                "account_name": tokens.get("instagram_2", {}).get("account_name", "Instagram 2"),
            },
            "youtube": {
                "connected": tokens.get("youtube", {}).get("connected", False),
                "oauth_configured": oauth_configured["youtube"],
            },
        },
    }


@app.post("/api/posts")
async def create_post(request: CreatePostRequest):
    global post_counter

    post_data = {
        "content": request.content,
        "image_url": request.image_url,
        "video_url": request.video_url,
        "platforms": request.platforms,
        "status": "scheduled" if request.scheduled_time else "draft",
        "scheduled_time": request.scheduled_time,
        "posted_ids": {},
        "word_count": len(request.content.split()),
    }

    # Save to Supabase if configured
    if supabase:
        try:
            result = supabase.table("posts").insert(post_data).execute()
            post = result.data[0]
            return {"success": True, "post": post}
        except Exception as e:
            print(f"Supabase insert error: {e}")

    # Fallback to memory
    post_counter += 1
    post = {
        "id": post_counter,
        **post_data,
        "posted_time": None,
        "error_message": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    posts_cache[post_counter] = post

    return {"success": True, "post": post}


@app.get("/api/posts")
async def list_posts(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0
):
    # Try Supabase first
    if supabase:
        try:
            query = supabase.table("posts").select("*").order("created_at", desc=True)
            if status:
                query = query.eq("status", status)
            query = query.range(offset, offset + limit - 1)
            result = query.execute()
            return {"posts": result.data, "total": len(result.data)}
        except Exception as e:
            print(f"Supabase list error: {e}")

    # Fallback to memory
    posts = list(posts_cache.values())

    if status:
        posts = [p for p in posts if p["status"] == status]

    posts = sorted(posts, key=lambda x: x["created_at"], reverse=True)
    posts = posts[offset:offset + limit]

    return {"posts": posts, "total": len(posts)}


@app.get("/api/posts/{post_id}")
async def get_post(post_id: int):
    # Try Supabase first
    if supabase:
        try:
            result = supabase.table("posts").select("*").eq("id", post_id).execute()
            if result.data:
                return {"post": result.data[0]}
            raise HTTPException(status_code=404, detail="Post not found")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Supabase get error: {e}")

    # Fallback to memory
    if post_id not in posts_cache:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"post": posts_cache[post_id]}


@app.patch("/api/posts/{post_id}")
async def update_post(post_id: int, request: UpdatePostRequest):
    update_data = {}
    if request.content is not None:
        update_data["content"] = request.content
        update_data["word_count"] = len(request.content.split())
    if request.image_url is not None:
        update_data["image_url"] = request.image_url
    if request.video_url is not None:
        update_data["video_url"] = request.video_url
    if request.platforms is not None:
        update_data["platforms"] = request.platforms
    if request.status is not None:
        update_data["status"] = request.status
    if request.scheduled_time is not None:
        update_data["scheduled_time"] = request.scheduled_time

    update_data["updated_at"] = datetime.utcnow().isoformat()

    # Try Supabase first
    if supabase:
        try:
            result = supabase.table("posts").update(update_data).eq("id", post_id).execute()
            if result.data:
                return {"success": True, "post": result.data[0]}
            raise HTTPException(status_code=404, detail="Post not found")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Supabase update error: {e}")

    # Fallback to memory
    if post_id not in posts_cache:
        raise HTTPException(status_code=404, detail="Post not found")

    post = posts_cache[post_id]
    post.update(update_data)

    return {"success": True, "post": post}


@app.post("/api/posts/{post_id}/publish")
async def publish_post(post_id: int):
    # Get post from Supabase or memory
    post = None
    if supabase:
        try:
            result = supabase.table("posts").select("*").eq("id", post_id).execute()
            if result.data:
                post = result.data[0]
        except Exception as e:
            print(f"Supabase get error: {e}")

    if not post and post_id in posts_cache:
        post = posts_cache[post_id]

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    content = post["content"]
    platforms = post["platforms"]
    image_url = post.get("image_url")
    video_url = post.get("video_url")

    results = {}

    for platform in platforms:
        if platform == "linkedin":
            results["linkedin"] = await post_to_linkedin(content, image_url)
        elif platform == "twitter":
            results["twitter"] = await post_to_twitter(content, image_url)
        elif platform == "facebook":
            results["facebook"] = await post_to_facebook(content, image_url, video_url)
        elif platform == "instagram_1":
            results["instagram_1"] = await post_to_instagram("instagram_1", content, image_url, video_url)
        elif platform == "instagram_2":
            results["instagram_2"] = await post_to_instagram("instagram_2", content, image_url, video_url)
        elif platform == "youtube":
            results["youtube"] = await post_to_youtube(content, video_url)

    all_success = all(r.get("success", False) for r in results.values()) if results else False

    update_data = {"updated_at": datetime.utcnow().isoformat()}

    if all_success:
        update_data["status"] = "posted"
        update_data["posted_time"] = datetime.utcnow().isoformat()
        update_data["posted_ids"] = {p: r.get("post_id", "") for p, r in results.items()}
    else:
        errors = [f"{p}: {r.get('error')}" for p, r in results.items() if not r.get("success")]
        update_data["error_message"] = "; ".join(errors) if errors else "No platforms configured"
        if any(r.get("success") for r in results.values()):
            update_data["status"] = "posted"
            update_data["posted_time"] = datetime.utcnow().isoformat()
            update_data["posted_ids"] = {p: r.get("post_id", "") for p, r in results.items() if r.get("success")}
        else:
            update_data["status"] = "failed"

    # Update in Supabase or memory
    if supabase:
        try:
            result = supabase.table("posts").update(update_data).eq("id", post_id).execute()
            if result.data:
                post = result.data[0]
        except Exception as e:
            print(f"Supabase update error: {e}")
            post.update(update_data)
    else:
        post.update(update_data)

    return {"success": all_success, "post": post, "platform_results": results}


@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int):
    # Try Supabase first
    if supabase:
        try:
            result = supabase.table("posts").delete().eq("id", post_id).execute()
            return {"success": True, "message": "Post deleted"}
        except Exception as e:
            print(f"Supabase delete error: {e}")

    # Fallback to memory
    if post_id not in posts_cache:
        raise HTTPException(status_code=404, detail="Post not found")

    del posts_cache[post_id]
    return {"success": True, "message": "Post deleted"}


@app.get("/api/platforms/scheduler/jobs")
async def get_scheduler_jobs():
    # Try Supabase first
    if supabase:
        try:
            result = supabase.table("posts").select("*").eq("status", "scheduled").execute()
            return {"jobs": result.data, "total": len(result.data)}
        except Exception as e:
            print(f"Supabase scheduler error: {e}")

    # Fallback to memory
    scheduled = [p for p in posts_cache.values() if p["status"] == "scheduled"]
    return {"jobs": scheduled, "total": len(scheduled)}


# Vercel serverless handler
from mangum import Mangum
handler = Mangum(app, lifespan="off")
