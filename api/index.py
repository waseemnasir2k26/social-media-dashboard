from fastapi import FastAPI, HTTPException, Query, Request
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
from openai import OpenAI
import re

# Initialize FastAPI
app = FastAPI(title="Social Media Dashboard API")

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

# ============ Simple Token Storage ============
# In production, use Vercel KV or Postgres
# For now, using environment variables + in-memory cache

tokens_cache: Dict[str, Dict[str, Any]] = {}
posts_db: Dict[int, dict] = {}
post_counter = 0

def get_stored_tokens() -> Dict[str, Any]:
    """Get tokens from cache or environment."""
    global tokens_cache

    # Check cache first
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
        "instagram": {
            "access_token": os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", ""),
            "account_id": os.environ.get("INSTAGRAM_ACCOUNT_ID", ""),
            "connected": bool(os.environ.get("INSTAGRAM_ACCOUNT_ID")),
        },
    }

def save_token(platform: str, token_data: Dict[str, Any]):
    """Save token to cache."""
    global tokens_cache
    tokens_cache[platform] = {**token_data, "connected": True}


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
        "scopes": ["pages_manage_posts", "pages_read_engagement", "instagram_basic", "instagram_content_publish"],
    },
}

# Store OAuth states for CSRF protection
oauth_states: Dict[str, str] = {}
pkce_verifiers: Dict[str, str] = {}


# ============ Models ============

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
    scheduled_time: Optional[str] = None


class UpdatePostRequest(BaseModel):
    content: Optional[str] = None
    image_url: Optional[str] = None
    platforms: Optional[List[str]] = None
    status: Optional[str] = None
    scheduled_time: Optional[str] = None
    auto_post: Optional[bool] = None


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
    if platform not in OAUTH_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")

    config = OAUTH_CONFIG[platform]

    if not config["client_id"]:
        raise HTTPException(
            status_code=400,
            detail=f"{platform} OAuth not configured. Add {platform.upper()}_CLIENT_ID to environment."
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

    config = OAUTH_CONFIG[platform]
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

            elif platform == "facebook":
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
                    save_token("facebook", {
                        "access_token": page.get("access_token"),
                        "page_id": page.get("id"),
                        "page_name": page.get("name"),
                    })

                    # Get Instagram account linked to this page
                    ig_response = await client.get(
                        f"https://graph.facebook.com/v18.0/{page['id']}",
                        params={
                            "fields": "instagram_business_account",
                            "access_token": page.get("access_token"),
                        }
                    )
                    ig_data = ig_response.json()
                    ig_account = ig_data.get("instagram_business_account", {})

                    if ig_account:
                        save_token("instagram", {
                            "access_token": page.get("access_token"),
                            "account_id": ig_account.get("id"),
                        })

            return RedirectResponse(f"{FRONTEND_URL}/settings?connected={platform}")

    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error={str(e)[:100]}")


@app.post("/api/auth/{platform}/disconnect")
async def oauth_disconnect(platform: str):
    """Disconnect a platform."""
    global tokens_cache
    if platform in tokens_cache:
        del tokens_cache[platform]
    return {"success": True, "message": f"{platform} disconnected"}


# ============ OpenAI Service ============

def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    return OpenAI(api_key=api_key)


def get_educational_prompt(platforms: str) -> str:
    return f"""You are a tech founder and AI expert. Write educational content for: {platforms}

Style: Direct, punchy, no fluff. Like Alex Hormozi meets Justin Welsh.

STRUCTURE:
1. HOOK (first line): Under 50 characters. Pattern interrupt.
2. RE-HOOK: One sentence explaining what they'll learn
3. BODY: Use "→" bullets. 5-7 points maximum. Short sentences.
4. TAKEAWAY: One powerful sentence
5. CTA: Question or invite saves/shares
6. HASHTAGS: Include 10-15 relevant hashtags

RULES:
- 80-150 words
- Maximum 2 emojis
- Each line is its own paragraph
- Be SPECIFIC with numbers and examples

Output ONLY valid JSON:
{{"content": "[full post with hashtags]", "image_prompt": "[optional image description]"}}"""


def get_motivation_prompt(platforms: str) -> str:
    return f"""You are a tech founder sharing wisdom for: {platforms}

Style: Short, punchy, quotable. Like Alex Hormozi.

STRUCTURE:
"[Bold statement]

[2-3 sentences expanding with personal touch]

[One-line takeaway]

Save this."

RULES:
- 40-80 words MAXIMUM
- Each line is its own paragraph
- NO corporate speak
- 0-2 emojis only
- 10+ hashtags at the end
- Make it quotable

Output ONLY JSON:
{{"content": "[full post with hashtags]", "image_prompt": "[optional image description]"}}"""


def get_general_prompt(platforms: str) -> str:
    return f"""You are a tech founder creating content for: {platforms}

Create engaging, valuable content that resonates with professionals.

RULES:
- Be authentic and specific
- Include a clear takeaway
- End with engagement prompt
- Include 10-15 relevant hashtags
- 50-150 words

Output ONLY JSON:
{{"content": "[full post with hashtags]", "image_prompt": "[optional image description]"}}"""


def parse_ai_response(raw: str) -> dict:
    try:
        json_str = re.sub(r'^```json\s*', '', raw, flags=re.IGNORECASE)
        json_str = re.sub(r'```$', '', json_str)
        start = json_str.find('{')
        end = json_str.rfind('}')
        if start != -1 and end != -1:
            json_str = json_str[start:end + 1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    return {"content": raw}


# ============ Social Media Posting ============

async def post_to_linkedin(content: str) -> dict:
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


async def post_to_twitter(content: str) -> dict:
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


async def post_to_facebook(content: str) -> dict:
    tokens = get_stored_tokens().get("facebook", {})
    access_token = tokens.get("access_token")
    page_id = tokens.get("page_id")

    if not access_token or not page_id:
        return {"success": False, "error": "Facebook not connected"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.facebook.com/v18.0/{page_id}/feed",
                params={"access_token": access_token, "message": content}
            )
            data = response.json()
            if "id" in data:
                return {"success": True, "post_id": data["id"]}
            return {"success": False, "error": data.get("error", {}).get("message", "Unknown error")}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def post_to_instagram(content: str, image_url: str) -> dict:
    tokens = get_stored_tokens().get("instagram", {})
    access_token = tokens.get("access_token")
    account_id = tokens.get("account_id")

    if not access_token or not account_id:
        return {"success": False, "error": "Instagram not connected"}

    if not image_url:
        return {"success": False, "error": "Instagram requires an image"}

    try:
        async with httpx.AsyncClient() as client:
            container_response = await client.post(
                f"https://graph.facebook.com/v18.0/{account_id}/media",
                params={"access_token": access_token, "image_url": image_url, "caption": content}
            )
            container_data = container_response.json()

            if "id" not in container_data:
                return {"success": False, "error": container_data.get("error", {}).get("message", "Failed")}

            publish_response = await client.post(
                f"https://graph.facebook.com/v18.0/{account_id}/media_publish",
                params={"access_token": access_token, "creation_id": container_data["id"]}
            )
            publish_data = publish_response.json()

            if "id" in publish_data:
                return {"success": True, "post_id": publish_data["id"]}
            return {"success": False, "error": publish_data.get("error", {}).get("message", "Failed")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ API Routes ============

@app.get("/api")
async def root():
    return {"message": "Social Media Dashboard API", "status": "running"}


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
        "instagram": bool(OAUTH_CONFIG["facebook"]["client_id"]),  # Uses Facebook OAuth
    }

    # Check OpenAI configuration
    openai_configured = bool(os.environ.get("OPENAI_API_KEY"))

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
            "instagram": {
                "connected": tokens.get("instagram", {}).get("connected", False),
                "oauth_configured": oauth_configured["instagram"],
            },
        },
        "openai_configured": openai_configured,
    }


@app.post("/api/posts/generate")
async def generate_content(request: GenerateContentRequest):
    client = get_openai_client()
    platform_str = ", ".join(request.platforms)

    if request.content_type == "educational":
        system_prompt = get_educational_prompt(platform_str)
    elif request.content_type == "motivation":
        system_prompt = get_motivation_prompt(platform_str)
    else:
        system_prompt = get_general_prompt(platform_str)

    user_prompt = f"Create a post about: {request.topic}" if request.topic else "Create an engaging post."
    if request.custom_prompt:
        user_prompt = request.custom_prompt

    try:
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1500,
            temperature=0.85
        )

        raw = response.choices[0].message.content.strip()
        parsed = parse_ai_response(raw)

        global post_counter
        post_counter += 1
        post = {
            "id": post_counter,
            "content": parsed.get("content", raw),
            "image_prompt": parsed.get("image_prompt", ""),
            "image_url": None,
            "content_type": request.content_type,
            "topic": request.topic,
            "platforms": request.platforms,
            "status": "pending_approval",
            "auto_post": request.auto_post,
            "scheduled_time": None,
            "posted_ids": {},
            "posted_time": None,
            "error_message": None,
            "word_count": len(parsed.get("content", raw).split()),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        posts_db[post_counter] = post

        return {"success": True, "post": post, "generation_result": parsed}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/posts/generate-image")
async def generate_image(prompt: str = Query(...)):
    client = get_openai_client()

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        return {"success": True, "image_url": response.data[0].url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/posts")
async def create_post(request: CreatePostRequest):
    global post_counter
    post_counter += 1

    post = {
        "id": post_counter,
        "content": request.content,
        "image_url": request.image_url,
        "image_prompt": request.image_prompt,
        "content_type": request.content_type,
        "topic": request.topic,
        "platforms": request.platforms,
        "status": "scheduled" if request.scheduled_time else "draft",
        "auto_post": request.auto_post,
        "scheduled_time": request.scheduled_time,
        "posted_ids": {},
        "posted_time": None,
        "error_message": None,
        "word_count": len(request.content.split()),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    posts_db[post_counter] = post

    return {"success": True, "post": post}


@app.get("/api/posts")
async def list_posts(
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0
):
    posts = list(posts_db.values())

    if status:
        posts = [p for p in posts if p["status"] == status]
    if content_type:
        posts = [p for p in posts if p["content_type"] == content_type]

    posts = sorted(posts, key=lambda x: x["created_at"], reverse=True)
    posts = posts[offset:offset + limit]

    return {"posts": posts, "total": len(posts)}


@app.get("/api/posts/{post_id}")
async def get_post(post_id: int):
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"post": posts_db[post_id]}


@app.patch("/api/posts/{post_id}")
async def update_post(post_id: int, request: UpdatePostRequest):
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="Post not found")

    post = posts_db[post_id]

    if request.content is not None:
        post["content"] = request.content
        post["word_count"] = len(request.content.split())
    if request.image_url is not None:
        post["image_url"] = request.image_url
    if request.platforms is not None:
        post["platforms"] = request.platforms
    if request.status is not None:
        post["status"] = request.status
    if request.scheduled_time is not None:
        post["scheduled_time"] = request.scheduled_time
    if request.auto_post is not None:
        post["auto_post"] = request.auto_post

    post["updated_at"] = datetime.utcnow().isoformat()

    return {"success": True, "post": post}


@app.post("/api/posts/{post_id}/approve")
async def approve_post(post_id: int):
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="Post not found")

    posts_db[post_id]["status"] = "approved"
    posts_db[post_id]["updated_at"] = datetime.utcnow().isoformat()

    return {"success": True, "post": posts_db[post_id]}


@app.post("/api/posts/{post_id}/publish")
async def publish_post(post_id: int):
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="Post not found")

    post = posts_db[post_id]
    content = post["content"]
    platforms = post["platforms"]
    image_url = post.get("image_url")

    results = {}

    for platform in platforms:
        if platform == "linkedin":
            results["linkedin"] = await post_to_linkedin(content)
        elif platform == "twitter":
            results["twitter"] = await post_to_twitter(content)
        elif platform == "facebook":
            results["facebook"] = await post_to_facebook(content)
        elif platform == "instagram":
            results["instagram"] = await post_to_instagram(content, image_url or "")

    all_success = all(r.get("success", False) for r in results.values()) if results else False

    if all_success:
        post["status"] = "posted"
        post["posted_time"] = datetime.utcnow().isoformat()
        post["posted_ids"] = {p: r.get("post_id", "") for p, r in results.items()}
    else:
        errors = [f"{p}: {r.get('error')}" for p, r in results.items() if not r.get("success")]
        post["error_message"] = "; ".join(errors) if errors else "No platforms configured"
        if any(r.get("success") for r in results.values()):
            post["status"] = "posted"
            post["posted_time"] = datetime.utcnow().isoformat()
            post["posted_ids"] = {p: r.get("post_id", "") for p, r in results.items() if r.get("success")}
        else:
            post["status"] = "failed"

    post["updated_at"] = datetime.utcnow().isoformat()

    return {"success": all_success, "post": post, "platform_results": results}


@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int):
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="Post not found")

    del posts_db[post_id]
    return {"success": True, "message": "Post deleted"}


@app.get("/api/platforms/scheduler/jobs")
async def get_scheduler_jobs():
    return {"jobs": [], "total": 0}


# Vercel serverless handler
from mangum import Mangum
handler = Mangum(app, lifespan="off")
