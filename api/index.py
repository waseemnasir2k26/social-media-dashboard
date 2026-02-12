from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urlencode
from mangum import Mangum
import os
import httpx
import secrets
import base64
import hashlib

# ============ App Setup ============
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Config ============
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

BASE_URL = os.environ.get("VERCEL_URL", "")
if BASE_URL and not BASE_URL.startswith("http"):
    BASE_URL = f"https://{BASE_URL}"
if not BASE_URL:
    BASE_URL = "http://localhost:8000"

FRONTEND_URL = BASE_URL

# ============ In-Memory Storage ============
tokens_cache: Dict[str, Any] = {}
posts_cache: Dict[int, dict] = {}
credentials_cache: Dict[str, dict] = {}
post_counter = 0

# ============ Supabase Helpers ============
async def db_request(method: str, table: str, data: dict = None, params: dict = None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if method == "GET":
                r = await client.get(url, headers=headers, params=params or {})
            elif method == "POST":
                r = await client.post(url, headers=headers, json=data)
            elif method == "PATCH":
                r = await client.patch(url, headers=headers, json=data, params=params or {})
            elif method == "DELETE":
                r = await client.delete(url, headers=headers, params=params or {})
            else:
                return None
            if r.status_code in [200, 201, 204]:
                return r.json() if r.text and r.status_code != 204 else []
    except:
        pass
    return None

# ============ Models ============
class CreatePostRequest(BaseModel):
    content: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    platforms: List[str] = []

class SaveCredentialsRequest(BaseModel):
    platform: str
    client_id: str
    client_secret: str

# ============ Basic Routes ============
@app.get("/api")
async def root():
    return {"status": "running", "message": "Social Media Dashboard API"}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "supabase": bool(SUPABASE_URL and SUPABASE_KEY)}

# ============ Credentials ============
@app.get("/api/credentials")
async def get_credentials():
    result = await db_request("GET", "oauth_credentials", params={"select": "platform,client_id"})
    if result:
        return {"credentials": {r["platform"]: {"client_id": r["client_id"], "configured": True} for r in result}}
    return {"credentials": credentials_cache}

@app.post("/api/credentials")
async def save_credentials(req: SaveCredentialsRequest):
    data = {
        "platform": req.platform,
        "client_id": req.client_id,
        "client_secret": req.client_secret,
        "updated_at": datetime.utcnow().isoformat()
    }

    existing = await db_request("GET", "oauth_credentials", params={"platform": f"eq.{req.platform}", "select": "id"})

    if existing and len(existing) > 0:
        result = await db_request("PATCH", "oauth_credentials", data, {"platform": f"eq.{req.platform}"})
    else:
        data["created_at"] = datetime.utcnow().isoformat()
        result = await db_request("POST", "oauth_credentials", data)

    if result:
        return {"success": True, "message": f"{req.platform} credentials saved"}

    credentials_cache[req.platform] = {"client_id": req.client_id, "configured": True}
    return {"success": True, "message": f"{req.platform} saved (memory)"}

# ============ Platform Status ============
@app.get("/api/platforms/status")
async def get_platform_status():
    creds = await db_request("GET", "oauth_credentials", params={"select": "platform"})
    configured = {r["platform"]: True for r in (creds or [])}

    tokens = await db_request("GET", "platform_tokens", params={"select": "platform,access_token,account_name,page_name"})
    connected = {}
    names = {}
    for t in (tokens or []):
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

# ============ OAuth Config ============
OAUTH = {
    "linkedin": {
        "auth": "https://www.linkedin.com/oauth/v2/authorization",
        "token": "https://www.linkedin.com/oauth/v2/accessToken",
        "scopes": "openid profile w_member_social",
    },
    "twitter": {
        "auth": "https://twitter.com/i/oauth2/authorize",
        "token": "https://api.twitter.com/2/oauth2/token",
        "scopes": "tweet.read tweet.write users.read offline.access",
    },
    "facebook": {
        "auth": "https://www.facebook.com/v18.0/dialog/oauth",
        "token": "https://graph.facebook.com/v18.0/oauth/access_token",
        "scopes": "pages_manage_posts pages_read_engagement instagram_basic instagram_content_publish business_management",
    },
    "youtube": {
        "auth": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "scopes": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube",
    },
}

oauth_states: Dict[str, str] = {}
pkce_verifiers: Dict[str, str] = {}

async def get_creds(platform: str):
    env = {
        "facebook": ("FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"),
        "twitter": ("TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET"),
        "youtube": ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"),
        "linkedin": ("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"),
    }
    if platform in env:
        cid, sec = os.environ.get(env[platform][0]), os.environ.get(env[platform][1])
        if cid and sec:
            return {"client_id": cid, "client_secret": sec}

    result = await db_request("GET", "oauth_credentials", params={"platform": f"eq.{platform}", "select": "client_id,client_secret"})
    if result and len(result) > 0:
        return result[0]
    return None

@app.get("/api/auth/{platform}/connect")
async def oauth_connect(platform: str):
    p = "facebook" if platform.startswith("instagram") else platform
    if p not in OAUTH:
        raise HTTPException(400, f"Unknown: {platform}")

    creds = await get_creds(p)
    if not creds:
        raise HTTPException(400, f"Add {platform} credentials in Settings first")

    state = secrets.token_urlsafe(16)
    oauth_states[state] = platform

    params = {
        "client_id": creds["client_id"],
        "redirect_uri": f"{BASE_URL}/api/auth/{platform}/callback",
        "response_type": "code",
        "state": state,
        "scope": OAUTH[p]["scopes"],
    }

    if platform == "twitter":
        v = secrets.token_urlsafe(32)
        pkce_verifiers[state] = v
        params["code_challenge"] = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).decode().rstrip("=")
        params["code_challenge_method"] = "S256"

    if platform == "youtube":
        params["access_type"] = "offline"
        params["prompt"] = "consent"

    return {"auth_url": f"{OAUTH[p]['auth']}?{urlencode(params)}"}

@app.get("/api/auth/{platform}/callback")
async def oauth_callback(platform: str, code: str = None, state: str = None, error: str = None):
    if error or not code or not state or state not in oauth_states:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error={error or 'invalid'}")

    del oauth_states[state]
    p = "facebook" if platform.startswith("instagram") else platform
    creds = await get_creds(p)
    if not creds:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error=no_creds")

    data = {
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "code": code,
        "redirect_uri": f"{BASE_URL}/api/auth/{platform}/callback",
        "grant_type": "authorization_code",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    if platform == "twitter" and state in pkce_verifiers:
        data["code_verifier"] = pkce_verifiers.pop(state)
        auth_str = f"{creds['client_id']}:{creds['client_secret']}"
        headers["Authorization"] = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
        del data["client_secret"]

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(OAUTH[p]["token"], data=data, headers=headers)
            if r.status_code != 200:
                return RedirectResponse(f"{FRONTEND_URL}/settings?error=token_failed")

            tokens = r.json()
            token_data = {"platform": platform, "access_token": tokens.get("access_token"), "updated_at": datetime.utcnow().isoformat()}

            if p == "facebook":
                # Get page token
                pages_r = await client.get(f"https://graph.facebook.com/v18.0/me/accounts", params={"access_token": tokens["access_token"]})
                pages = pages_r.json().get("data", [])
                if pages:
                    page = pages[0]
                    token_data["access_token"] = page.get("access_token")
                    token_data["page_id"] = page.get("id")
                    token_data["page_name"] = page.get("name")

                    # Get Instagram accounts
                    for i, pg in enumerate(pages[:2]):
                        ig_r = await client.get(f"https://graph.facebook.com/v18.0/{pg['id']}", params={"fields": "instagram_business_account{id,username}", "access_token": pg["access_token"]})
                        ig = ig_r.json().get("instagram_business_account", {})
                        if ig:
                            ig_data = {"platform": f"instagram_{i+1}", "access_token": pg["access_token"], "account_id": ig.get("id"), "account_name": ig.get("username"), "updated_at": datetime.utcnow().isoformat()}
                            ex = await db_request("GET", "platform_tokens", params={"platform": f"eq.instagram_{i+1}", "select": "id"})
                            if ex and len(ex) > 0:
                                await db_request("PATCH", "platform_tokens", ig_data, {"platform": f"eq.instagram_{i+1}"})
                            else:
                                ig_data["created_at"] = datetime.utcnow().isoformat()
                                await db_request("POST", "platform_tokens", ig_data)
                            tokens_cache[f"instagram_{i+1}"] = {"connected": True}

            # Save token
            ex = await db_request("GET", "platform_tokens", params={"platform": f"eq.{platform}", "select": "id"})
            if ex and len(ex) > 0:
                await db_request("PATCH", "platform_tokens", token_data, {"platform": f"eq.{platform}"})
            else:
                token_data["created_at"] = datetime.utcnow().isoformat()
                await db_request("POST", "platform_tokens", token_data)

            tokens_cache[platform] = {"connected": True}
            return RedirectResponse(f"{FRONTEND_URL}/settings?connected={platform}")
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error={str(e)[:30]}")

@app.post("/api/auth/{platform}/disconnect")
async def disconnect(platform: str):
    await db_request("DELETE", "platform_tokens", params={"platform": f"eq.{platform}"})
    tokens_cache.pop(platform, None)
    return {"success": True}

# ============ Posts ============
@app.get("/api/posts")
async def list_posts(status: Optional[str] = None):
    result = await db_request("GET", "posts", params={"select": "*", "order": "created_at.desc"})
    posts = result if result else list(posts_cache.values())
    if status:
        posts = [p for p in posts if p.get("status") == status]
    return {"posts": posts, "total": len(posts)}

@app.post("/api/posts")
async def create_post(req: CreatePostRequest):
    global post_counter
    data = {"content": req.content, "image_url": req.image_url, "video_url": req.video_url, "platforms": req.platforms, "status": "draft", "word_count": len(req.content.split())}
    result = await db_request("POST", "posts", data)
    if result and len(result) > 0:
        return {"success": True, "post": result[0]}
    post_counter += 1
    post = {"id": post_counter, **data, "created_at": datetime.utcnow().isoformat()}
    posts_cache[post_counter] = post
    return {"success": True, "post": post}

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int):
    await db_request("DELETE", "posts", params={"id": f"eq.{post_id}"})
    posts_cache.pop(post_id, None)
    return {"success": True}

@app.post("/api/posts/{post_id}/publish")
async def publish_post(post_id: int):
    result = await db_request("GET", "posts", params={"id": f"eq.{post_id}", "select": "*"})
    post = result[0] if result else posts_cache.get(post_id)
    if not post:
        raise HTTPException(404, "Post not found")

    results = {}
    for platform in post.get("platforms", []):
        tok = await db_request("GET", "platform_tokens", params={"platform": f"eq.{platform}", "select": "*"})
        token = tok[0] if tok else tokens_cache.get(platform, {})
        if not token.get("access_token"):
            results[platform] = {"success": False, "error": "Not connected"}
            continue

        try:
            async with httpx.AsyncClient() as client:
                if platform == "twitter":
                    r = await client.post("https://api.twitter.com/2/tweets", headers={"Authorization": f"Bearer {token['access_token']}"}, json={"text": post["content"][:280]})
                    results[platform] = {"success": r.status_code in [200,201], "error": r.text[:50] if r.status_code not in [200,201] else None}
                elif platform == "facebook":
                    r = await client.post(f"https://graph.facebook.com/v18.0/{token.get('page_id')}/feed", params={"access_token": token["access_token"], "message": post["content"]})
                    results[platform] = {"success": "id" in r.json(), "error": r.json().get("error", {}).get("message") if "id" not in r.json() else None}
                elif platform == "linkedin":
                    u = await client.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {token['access_token']}"})
                    uid = u.json().get("sub")
                    r = await client.post("https://api.linkedin.com/v2/ugcPosts", headers={"Authorization": f"Bearer {token['access_token']}", "X-Restli-Protocol-Version": "2.0.0"}, json={"author": f"urn:li:person:{uid}", "lifecycleState": "PUBLISHED", "specificContent": {"com.linkedin.ugc.ShareContent": {"shareCommentary": {"text": post["content"]}, "shareMediaCategory": "NONE"}}, "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}})
                    results[platform] = {"success": r.status_code in [200,201]}
                elif platform.startswith("instagram"):
                    if not post.get("image_url"):
                        results[platform] = {"success": False, "error": "Image required"}
                        continue
                    c = await client.post(f"https://graph.facebook.com/v18.0/{token.get('account_id')}/media", params={"access_token": token["access_token"], "image_url": post["image_url"], "caption": post["content"]})
                    if "id" in c.json():
                        p = await client.post(f"https://graph.facebook.com/v18.0/{token.get('account_id')}/media_publish", params={"access_token": token["access_token"], "creation_id": c.json()["id"]})
                        results[platform] = {"success": "id" in p.json()}
                    else:
                        results[platform] = {"success": False, "error": c.json().get("error", {}).get("message")}
                else:
                    results[platform] = {"success": False, "error": "Not supported"}
        except Exception as e:
            results[platform] = {"success": False, "error": str(e)[:50]}

    new_status = "posted" if any(r["success"] for r in results.values()) else "failed"
    await db_request("PATCH", "posts", {"status": new_status, "posted_time": datetime.utcnow().isoformat()}, {"id": f"eq.{post_id}"})

    return {"success": all(r["success"] for r in results.values()), "results": results}

@app.get("/api/platforms/scheduler/jobs")
async def scheduler_jobs():
    result = await db_request("GET", "posts", params={"status": "eq.scheduled"})
    return {"jobs": result or [], "total": len(result or [])}

# ============ Handler ============
handler = Mangum(app, lifespan="off")
