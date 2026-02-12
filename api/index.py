from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urlencode
import os
import httpx
import secrets
import base64
import hashlib
import logging
import traceback

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Initialize FastAPI
app = FastAPI(title="Social Media Dashboard API")

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": traceback.format_exc()}
    )

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Base URL for OAuth callbacks
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

# In-memory storage
tokens_cache: Dict[str, Dict[str, Any]] = {}
posts_cache: Dict[int, dict] = {}
credentials_cache: Dict[str, dict] = {}
post_counter = 0

# ============ Supabase Helper ============

async def db_get(table: str, params: dict = None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning(f"db_get({table}): Supabase not configured")
        return None
    try:
        logger.debug(f"db_get({table}): params={params}")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                params=params or {}
            )
            logger.debug(f"db_get({table}): status={resp.status_code}")
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"db_get({table}): error={resp.text}")
    except Exception as e:
        logger.error(f"db_get({table}): exception={str(e)}")
    return None

async def db_post(table: str, data: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning(f"db_post({table}): Supabase not configured")
        return None
    try:
        logger.debug(f"db_post({table}): data keys={list(data.keys())}")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=data
            )
            logger.debug(f"db_post({table}): status={resp.status_code}")
            if resp.status_code in [200, 201]:
                return resp.json()
            logger.error(f"db_post({table}): error={resp.text}")
    except Exception as e:
        logger.error(f"db_post({table}): exception={str(e)}")
    return None

async def db_patch(table: str, data: dict, params: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=data,
                params=params
            )
            if resp.status_code == 200:
                return resp.json()
    except:
        pass
    return None

async def db_delete(table: str, params: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                params=params
            )
            if resp.status_code in [200, 204]:
                return True
    except:
        pass
    return None

# ============ Models ============

class CreatePostRequest(BaseModel):
    content: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    platforms: List[str] = []
    scheduled_time: Optional[str] = None

class SaveCredentialsRequest(BaseModel):
    platform: str
    client_id: str
    client_secret: str

# ============ Basic Routes ============

@app.get("/api")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Social Media Dashboard API", "status": "running"}

@app.get("/api/health")
async def health():
    logger.info(f"Health check - SUPABASE_URL: {bool(SUPABASE_URL)}, SUPABASE_KEY: {bool(SUPABASE_KEY)}")
    return {"status": "healthy", "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY)}

@app.get("/api/debug")
async def debug():
    """Debug endpoint to check configuration"""
    return {
        "supabase_url": SUPABASE_URL[:30] + "..." if SUPABASE_URL else "NOT SET",
        "supabase_key": SUPABASE_KEY[:10] + "..." if SUPABASE_KEY else "NOT SET",
        "base_url": BASE_URL,
        "env_vars": {
            "VERCEL_URL": os.environ.get("VERCEL_URL", "NOT SET"),
            "SUPABASE_URL": "SET" if SUPABASE_URL else "NOT SET",
            "SUPABASE_KEY": "SET" if SUPABASE_KEY else "NOT SET",
        }
    }

# ============ Credentials ============

@app.get("/api/credentials")
async def get_credentials():
    logger.info("GET /api/credentials called")
    result = await db_get("oauth_credentials", {"select": "platform,client_id"})
    logger.info(f"Credentials result: {result}")
    if result:
        return {"credentials": {r["platform"]: {"client_id": r["client_id"], "configured": True} for r in result}}
    return {"credentials": credentials_cache}

@app.post("/api/credentials")
async def save_credentials(request: SaveCredentialsRequest):
    logger.info(f"POST /api/credentials: platform={request.platform}")

    data = {
        "platform": request.platform,
        "client_id": request.client_id,
        "client_secret": request.client_secret,
        "updated_at": datetime.utcnow().isoformat()
    }

    # Check if exists
    logger.debug("Checking if credentials exist...")
    existing = await db_get("oauth_credentials", {"platform": f"eq.{request.platform}", "select": "id"})
    logger.debug(f"Existing: {existing}")

    if existing and len(existing) > 0:
        logger.info("Updating existing credentials")
        result = await db_patch("oauth_credentials", data, {"platform": f"eq.{request.platform}"})
    else:
        logger.info("Creating new credentials")
        data["created_at"] = datetime.utcnow().isoformat()
        result = await db_post("oauth_credentials", data)

    logger.info(f"Save result: {result}")

    if result:
        return {"success": True, "message": f"{request.platform} credentials saved"}

    # Fallback to memory
    logger.warning("Falling back to memory storage")
    credentials_cache[request.platform] = {"client_id": request.client_id, "configured": True}
    return {"success": True, "message": f"{request.platform} credentials saved (in memory)"}

# ============ Platform Status ============

@app.get("/api/platforms/status")
async def get_platform_status():
    # Get credentials from DB or cache
    creds = await db_get("oauth_credentials", {"select": "platform,client_id"})
    configured = {}
    if creds:
        configured = {r["platform"]: True for r in creds}

    # Get tokens from DB or cache
    tokens = await db_get("platform_tokens", {"select": "platform,access_token,account_name,page_name"})
    connected = {}
    names = {}
    if tokens:
        for t in tokens:
            if t.get("access_token"):
                connected[t["platform"]] = True
                names[t["platform"]] = t.get("account_name") or t.get("page_name") or ""

    platforms = ["linkedin", "twitter", "facebook", "instagram_1", "instagram_2", "youtube"]

    return {
        "platforms": {
            p: {
                "connected": connected.get(p, tokens_cache.get(p, {}).get("connected", False)),
                "oauth_configured": configured.get("facebook" if p.startswith("instagram") else p, False),
                "account_name": names.get(p, ""),
            }
            for p in platforms
        }
    }

# ============ OAuth ============

OAUTH_CONFIG = {
    "linkedin": {
        "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "scopes": ["openid", "profile", "w_member_social"],
    },
    "twitter": {
        "auth_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "scopes": ["tweet.read", "tweet.write", "users.read", "offline.access"],
    },
    "facebook": {
        "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "scopes": ["pages_manage_posts", "pages_read_engagement", "instagram_basic", "instagram_content_publish", "business_management"],
    },
    "youtube": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"],
    },
}

oauth_states: Dict[str, str] = {}
pkce_verifiers: Dict[str, str] = {}

async def get_oauth_creds(platform: str):
    # Check env vars first
    env_map = {
        "facebook": ("FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"),
        "twitter": ("TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET"),
        "youtube": ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"),
        "linkedin": ("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"),
    }
    if platform in env_map:
        cid = os.environ.get(env_map[platform][0], "")
        secret = os.environ.get(env_map[platform][1], "")
        if cid and secret:
            return {"client_id": cid, "client_secret": secret}

    # Check Supabase
    result = await db_get("oauth_credentials", {"platform": f"eq.{platform}", "select": "client_id,client_secret"})
    if result and len(result) > 0:
        return result[0]

    return None

@app.get("/api/auth/{platform}/connect")
async def oauth_connect(platform: str):
    actual_platform = "facebook" if platform.startswith("instagram") else platform

    if actual_platform not in OAUTH_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")

    creds = await get_oauth_creds(actual_platform)
    if not creds:
        raise HTTPException(status_code=400, detail=f"No credentials for {platform}. Add them in Settings first.")

    config = OAUTH_CONFIG[actual_platform]
    state = secrets.token_urlsafe(32)
    oauth_states[state] = platform

    callback_url = f"{BASE_URL}/api/auth/{platform}/callback"

    params = {
        "client_id": creds["client_id"],
        "redirect_uri": callback_url,
        "response_type": "code",
        "state": state,
        "scope": " ".join(config["scopes"]),
    }

    if platform == "twitter":
        verifier = secrets.token_urlsafe(32)
        pkce_verifiers[state] = verifier
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"

    if platform == "youtube":
        params["access_type"] = "offline"
        params["prompt"] = "consent"

    return {"auth_url": f"{config['auth_url']}?{urlencode(params)}"}

@app.get("/api/auth/{platform}/callback")
async def oauth_callback(platform: str, code: str = None, state: str = None, error: str = None):
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error={error}")

    if not code or not state or state not in oauth_states:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error=invalid_state")

    del oauth_states[state]
    actual_platform = "facebook" if platform.startswith("instagram") else platform

    creds = await get_oauth_creds(actual_platform)
    if not creds:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error=no_credentials")

    config = OAUTH_CONFIG[actual_platform]
    callback_url = f"{BASE_URL}/api/auth/{platform}/callback"

    token_data = {
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "code": code,
        "redirect_uri": callback_url,
        "grant_type": "authorization_code",
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    if platform == "twitter" and state in pkce_verifiers:
        token_data["code_verifier"] = pkce_verifiers[state]
        del pkce_verifiers[state]
        auth = base64.b64encode(f"{creds['client_id']}:{creds['client_secret']}".encode()).decode()
        headers["Authorization"] = f"Basic {auth}"
        del token_data["client_secret"]

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(config["token_url"], data=token_data, headers=headers)
            if resp.status_code != 200:
                return RedirectResponse(f"{FRONTEND_URL}/settings?error=token_failed")

            tokens = resp.json()
            access_token = tokens.get("access_token")

            # Save token
            token_record = {
                "platform": platform,
                "access_token": access_token,
                "refresh_token": tokens.get("refresh_token", ""),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # For Facebook, get page token
            if platform == "facebook" or platform.startswith("instagram"):
                # Get long-lived token
                lt_resp = await client.get(
                    "https://graph.facebook.com/v18.0/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": creds["client_id"],
                        "client_secret": creds["client_secret"],
                        "fb_exchange_token": access_token,
                    }
                )
                if lt_resp.status_code == 200:
                    access_token = lt_resp.json().get("access_token", access_token)

                # Get pages
                pages_resp = await client.get(
                    "https://graph.facebook.com/v18.0/me/accounts",
                    params={"access_token": access_token}
                )
                pages = pages_resp.json().get("data", [])

                if pages:
                    page = pages[0]
                    if platform == "facebook":
                        token_record["access_token"] = page.get("access_token")
                        token_record["page_id"] = page.get("id")
                        token_record["page_name"] = page.get("name")

                    # Get Instagram accounts
                    ig_accounts = []
                    for p in pages:
                        ig_resp = await client.get(
                            f"https://graph.facebook.com/v18.0/{p['id']}",
                            params={
                                "fields": "instagram_business_account{id,username}",
                                "access_token": p.get("access_token"),
                            }
                        )
                        ig_data = ig_resp.json().get("instagram_business_account", {})
                        if ig_data:
                            ig_accounts.append({
                                "id": ig_data.get("id"),
                                "username": ig_data.get("username"),
                                "token": p.get("access_token"),
                            })

                    # Save Instagram accounts
                    for i, ig in enumerate(ig_accounts[:2]):
                        ig_platform = f"instagram_{i+1}"
                        ig_record = {
                            "platform": ig_platform,
                            "access_token": ig["token"],
                            "account_id": ig["id"],
                            "account_name": ig["username"],
                            "updated_at": datetime.utcnow().isoformat(),
                        }
                        existing = await db_get("platform_tokens", {"platform": f"eq.{ig_platform}", "select": "id"})
                        if existing and len(existing) > 0:
                            await db_patch("platform_tokens", ig_record, {"platform": f"eq.{ig_platform}"})
                        else:
                            ig_record["created_at"] = datetime.utcnow().isoformat()
                            await db_post("platform_tokens", ig_record)
                        tokens_cache[ig_platform] = {"connected": True, **ig_record}

            # Save main token
            existing = await db_get("platform_tokens", {"platform": f"eq.{platform}", "select": "id"})
            if existing and len(existing) > 0:
                await db_patch("platform_tokens", token_record, {"platform": f"eq.{platform}"})
            else:
                token_record["created_at"] = datetime.utcnow().isoformat()
                await db_post("platform_tokens", token_record)

            tokens_cache[platform] = {"connected": True, **token_record}

            return RedirectResponse(f"{FRONTEND_URL}/settings?connected={platform}")

    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error={str(e)[:50]}")

@app.post("/api/auth/{platform}/disconnect")
async def oauth_disconnect(platform: str):
    await db_delete("platform_tokens", {"platform": f"eq.{platform}"})
    if platform in tokens_cache:
        del tokens_cache[platform]
    return {"success": True}

# ============ Posts ============

@app.post("/api/posts")
async def create_post(request: CreatePostRequest):
    global post_counter

    data = {
        "content": request.content,
        "image_url": request.image_url,
        "video_url": request.video_url,
        "platforms": request.platforms,
        "status": "draft",
        "word_count": len(request.content.split()),
    }

    result = await db_post("posts", data)
    if result and len(result) > 0:
        return {"success": True, "post": result[0]}

    post_counter += 1
    post = {"id": post_counter, **data, "created_at": datetime.utcnow().isoformat()}
    posts_cache[post_counter] = post
    return {"success": True, "post": post}

@app.get("/api/posts")
async def list_posts(status: Optional[str] = None, limit: int = 50):
    result = await db_get("posts", {"select": "*", "order": "created_at.desc", "limit": str(limit)})
    if result is not None:
        posts = result
        if status:
            posts = [p for p in posts if p.get("status") == status]
        return {"posts": posts, "total": len(posts)}

    posts = list(posts_cache.values())
    if status:
        posts = [p for p in posts if p.get("status") == status]
    return {"posts": posts, "total": len(posts)}

@app.get("/api/posts/{post_id}")
async def get_post(post_id: int):
    result = await db_get("posts", {"id": f"eq.{post_id}", "select": "*"})
    if result and len(result) > 0:
        return {"post": result[0]}
    if post_id in posts_cache:
        return {"post": posts_cache[post_id]}
    raise HTTPException(status_code=404, detail="Post not found")

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int):
    await db_delete("posts", {"id": f"eq.{post_id}"})
    if post_id in posts_cache:
        del posts_cache[post_id]
    return {"success": True}

@app.post("/api/posts/{post_id}/publish")
async def publish_post(post_id: int):
    # Get post
    result = await db_get("posts", {"id": f"eq.{post_id}", "select": "*"})
    post = result[0] if result and len(result) > 0 else posts_cache.get(post_id)

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    content = post["content"]
    platforms = post.get("platforms", [])
    results = {}

    for platform in platforms:
        # Get token
        token_result = await db_get("platform_tokens", {"platform": f"eq.{platform}", "select": "*"})
        token = token_result[0] if token_result and len(token_result) > 0 else tokens_cache.get(platform, {})

        if not token.get("access_token"):
            results[platform] = {"success": False, "error": "Not connected"}
            continue

        try:
            async with httpx.AsyncClient() as client:
                if platform == "twitter":
                    resp = await client.post(
                        "https://api.twitter.com/2/tweets",
                        headers={"Authorization": f"Bearer {token['access_token']}", "Content-Type": "application/json"},
                        json={"text": content[:280]}
                    )
                    if resp.status_code in [200, 201]:
                        results[platform] = {"success": True, "post_id": resp.json().get("data", {}).get("id")}
                    else:
                        results[platform] = {"success": False, "error": resp.text[:100]}

                elif platform == "linkedin":
                    user_resp = await client.get(
                        "https://api.linkedin.com/v2/userinfo",
                        headers={"Authorization": f"Bearer {token['access_token']}"}
                    )
                    if user_resp.status_code != 200:
                        results[platform] = {"success": False, "error": "Token expired"}
                        continue

                    user_id = user_resp.json().get("sub")
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
                    resp = await client.post(
                        "https://api.linkedin.com/v2/ugcPosts",
                        headers={
                            "Authorization": f"Bearer {token['access_token']}",
                            "Content-Type": "application/json",
                            "X-Restli-Protocol-Version": "2.0.0"
                        },
                        json=post_data
                    )
                    if resp.status_code in [200, 201]:
                        results[platform] = {"success": True, "post_id": resp.headers.get("x-restli-id", "")}
                    else:
                        results[platform] = {"success": False, "error": resp.text[:100]}

                elif platform == "facebook":
                    page_id = token.get("page_id", "")
                    resp = await client.post(
                        f"https://graph.facebook.com/v18.0/{page_id}/feed",
                        params={"access_token": token["access_token"], "message": content}
                    )
                    data = resp.json()
                    if "id" in data:
                        results[platform] = {"success": True, "post_id": data["id"]}
                    else:
                        results[platform] = {"success": False, "error": data.get("error", {}).get("message", "Failed")}

                elif platform.startswith("instagram"):
                    image_url = post.get("image_url")
                    if not image_url:
                        results[platform] = {"success": False, "error": "Instagram requires an image"}
                        continue

                    account_id = token.get("account_id", "")
                    # Create container
                    container_resp = await client.post(
                        f"https://graph.facebook.com/v18.0/{account_id}/media",
                        params={"access_token": token["access_token"], "image_url": image_url, "caption": content}
                    )
                    container = container_resp.json()
                    if "id" not in container:
                        results[platform] = {"success": False, "error": container.get("error", {}).get("message", "Failed")}
                        continue

                    # Publish
                    publish_resp = await client.post(
                        f"https://graph.facebook.com/v18.0/{account_id}/media_publish",
                        params={"access_token": token["access_token"], "creation_id": container["id"]}
                    )
                    publish_data = publish_resp.json()
                    if "id" in publish_data:
                        results[platform] = {"success": True, "post_id": publish_data["id"]}
                    else:
                        results[platform] = {"success": False, "error": publish_data.get("error", {}).get("message", "Failed")}

                else:
                    results[platform] = {"success": False, "error": "Platform not supported yet"}

        except Exception as e:
            results[platform] = {"success": False, "error": str(e)[:100]}

    # Update post status
    all_success = all(r.get("success") for r in results.values()) if results else False
    new_status = "posted" if all_success else ("failed" if not any(r.get("success") for r in results.values()) else "posted")

    update_data = {
        "status": new_status,
        "posted_ids": {p: r.get("post_id", "") for p, r in results.items() if r.get("success")},
        "posted_time": datetime.utcnow().isoformat() if any(r.get("success") for r in results.values()) else None,
        "error_message": "; ".join([f"{p}: {r['error']}" for p, r in results.items() if not r.get("success")]) or None,
    }

    await db_patch("posts", update_data, {"id": f"eq.{post_id}"})
    if post_id in posts_cache:
        posts_cache[post_id].update(update_data)

    return {"success": all_success, "post": {**post, **update_data}, "platform_results": results}

@app.get("/api/platforms/scheduler/jobs")
async def get_scheduler_jobs():
    result = await db_get("posts", {"status": "eq.scheduled", "select": "*"})
    if result:
        return {"jobs": result, "total": len(result)}
    return {"jobs": [], "total": 0}

# Vercel handler
from mangum import Mangum
handler = Mangum(app, lifespan="off")
