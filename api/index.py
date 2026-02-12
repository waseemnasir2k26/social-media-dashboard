from flask import Flask, jsonify, request, redirect
from flask_cors import CORS
from datetime import datetime
from urllib.parse import urlencode
import os
import httpx
import secrets
import base64
import hashlib

app = Flask(__name__)
CORS(app)

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
tokens_cache = {}
posts_cache = {}
credentials_cache = {}
post_counter = 0
oauth_states = {}
pkce_verifiers = {}

# ============ Supabase Helpers ============
def db_request(method, table, data=None, params=None):
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
        with httpx.Client(timeout=10) as client:
            if method == "GET":
                r = client.get(url, headers=headers, params=params or {})
            elif method == "POST":
                r = client.post(url, headers=headers, json=data)
            elif method == "PATCH":
                r = client.patch(url, headers=headers, json=data, params=params or {})
            elif method == "DELETE":
                r = client.delete(url, headers=headers, params=params or {})
            else:
                return None
            if r.status_code in [200, 201, 204]:
                return r.json() if r.text and r.status_code != 204 else []
    except Exception as e:
        print(f"DB Error: {e}")
    return None

# ============ Basic Routes ============
@app.route('/api')
@app.route('/api/')
def root():
    return jsonify({"status": "running", "message": "Social Media Dashboard API"})

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "supabase": bool(SUPABASE_URL and SUPABASE_KEY)})

# ============ Credentials ============
@app.route('/api/credentials', methods=['GET'])
def get_credentials():
    result = db_request("GET", "oauth_credentials", params={"select": "platform,client_id"})
    if result:
        return jsonify({"credentials": {r["platform"]: {"client_id": r["client_id"], "configured": True} for r in result}})
    return jsonify({"credentials": credentials_cache})

@app.route('/api/credentials', methods=['POST'])
def save_credentials():
    data = request.json
    platform = data.get("platform")
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")

    if not platform or not client_id or not client_secret:
        return jsonify({"error": "Missing fields"}), 400

    db_data = {
        "platform": platform,
        "client_id": client_id,
        "client_secret": client_secret,
        "updated_at": datetime.utcnow().isoformat()
    }

    existing = db_request("GET", "oauth_credentials", params={"platform": f"eq.{platform}", "select": "id"})

    if existing and len(existing) > 0:
        result = db_request("PATCH", "oauth_credentials", db_data, {"platform": f"eq.{platform}"})
    else:
        db_data["created_at"] = datetime.utcnow().isoformat()
        result = db_request("POST", "oauth_credentials", db_data)

    if result is not None:
        return jsonify({"success": True, "message": f"{platform} credentials saved"})

    credentials_cache[platform] = {"client_id": client_id, "configured": True}
    return jsonify({"success": True, "message": f"{platform} saved (memory)"})

# ============ Platform Status ============
@app.route('/api/platforms/status')
def get_platform_status():
    creds = db_request("GET", "oauth_credentials", params={"select": "platform"})
    configured = {r["platform"]: True for r in (creds or [])}

    tokens = db_request("GET", "platform_tokens", params={"select": "platform,access_token,account_name,page_name"})
    connected = {}
    names = {}
    for t in (tokens or []):
        if t.get("access_token"):
            connected[t["platform"]] = True
            names[t["platform"]] = t.get("account_name") or t.get("page_name") or ""

    platforms = ["linkedin", "twitter", "facebook", "instagram_1", "instagram_2", "youtube"]
    return jsonify({
        "platforms": {
            p: {
                "connected": connected.get(p, tokens_cache.get(p, {}).get("connected", False)),
                "oauth_configured": configured.get("facebook" if p.startswith("instagram") else p, False),
                "account_name": names.get(p, ""),
            }
            for p in platforms
        }
    })

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

def get_creds(platform):
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

    result = db_request("GET", "oauth_credentials", params={"platform": f"eq.{platform}", "select": "client_id,client_secret"})
    if result and len(result) > 0:
        return result[0]
    return None

@app.route('/api/auth/<platform>/connect')
def oauth_connect(platform):
    p = "facebook" if platform.startswith("instagram") else platform
    if p not in OAUTH:
        return jsonify({"error": f"Unknown platform: {platform}"}), 400

    creds = get_creds(p)
    if not creds:
        return jsonify({"detail": f"Add {platform} credentials in Settings first"}), 400

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
        challenge = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).decode().rstrip("=")
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"

    if platform == "youtube":
        params["access_type"] = "offline"
        params["prompt"] = "consent"

    return jsonify({"auth_url": f"{OAUTH[p]['auth']}?{urlencode(params)}"})

@app.route('/api/auth/<platform>/callback')
def oauth_callback(platform):
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error or not code or not state or state not in oauth_states:
        return redirect(f"{FRONTEND_URL}/settings?error={error or 'invalid'}")

    del oauth_states[state]
    p = "facebook" if platform.startswith("instagram") else platform
    creds = get_creds(p)
    if not creds:
        return redirect(f"{FRONTEND_URL}/settings?error=no_creds")

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
        with httpx.Client() as client:
            r = client.post(OAUTH[p]["token"], data=data, headers=headers)
            if r.status_code != 200:
                return redirect(f"{FRONTEND_URL}/settings?error=token_failed")

            tokens = r.json()
            token_data = {"platform": platform, "access_token": tokens.get("access_token"), "updated_at": datetime.utcnow().isoformat()}

            if p == "facebook":
                pages_r = client.get("https://graph.facebook.com/v18.0/me/accounts", params={"access_token": tokens["access_token"]})
                pages = pages_r.json().get("data", [])
                if pages:
                    page = pages[0]
                    token_data["access_token"] = page.get("access_token")
                    token_data["page_id"] = page.get("id")
                    token_data["page_name"] = page.get("name")

                    for i, pg in enumerate(pages[:2]):
                        ig_r = client.get(f"https://graph.facebook.com/v18.0/{pg['id']}", params={"fields": "instagram_business_account{id,username}", "access_token": pg["access_token"]})
                        ig = ig_r.json().get("instagram_business_account", {})
                        if ig:
                            ig_data = {"platform": f"instagram_{i+1}", "access_token": pg["access_token"], "account_id": ig.get("id"), "account_name": ig.get("username"), "updated_at": datetime.utcnow().isoformat()}
                            ex = db_request("GET", "platform_tokens", params={"platform": f"eq.instagram_{i+1}", "select": "id"})
                            if ex and len(ex) > 0:
                                db_request("PATCH", "platform_tokens", ig_data, {"platform": f"eq.instagram_{i+1}"})
                            else:
                                ig_data["created_at"] = datetime.utcnow().isoformat()
                                db_request("POST", "platform_tokens", ig_data)
                            tokens_cache[f"instagram_{i+1}"] = {"connected": True}

            ex = db_request("GET", "platform_tokens", params={"platform": f"eq.{platform}", "select": "id"})
            if ex and len(ex) > 0:
                db_request("PATCH", "platform_tokens", token_data, {"platform": f"eq.{platform}"})
            else:
                token_data["created_at"] = datetime.utcnow().isoformat()
                db_request("POST", "platform_tokens", token_data)

            tokens_cache[platform] = {"connected": True}
            return redirect(f"{FRONTEND_URL}/settings?connected={platform}")
    except Exception as e:
        return redirect(f"{FRONTEND_URL}/settings?error={str(e)[:30]}")

@app.route('/api/auth/<platform>/disconnect', methods=['POST'])
def disconnect(platform):
    db_request("DELETE", "platform_tokens", params={"platform": f"eq.{platform}"})
    tokens_cache.pop(platform, None)
    return jsonify({"success": True})

# ============ Posts ============
@app.route('/api/posts', methods=['GET'])
def list_posts():
    status = request.args.get("status")
    result = db_request("GET", "posts", params={"select": "*", "order": "created_at.desc"})
    posts = result if result else list(posts_cache.values())
    if status:
        posts = [p for p in posts if p.get("status") == status]
    return jsonify({"posts": posts, "total": len(posts)})

@app.route('/api/posts', methods=['POST'])
def create_post():
    global post_counter
    data = request.json
    post_data = {
        "content": data.get("content", ""),
        "image_url": data.get("image_url"),
        "video_url": data.get("video_url"),
        "platforms": data.get("platforms", []),
        "status": "draft",
        "word_count": len(data.get("content", "").split())
    }
    result = db_request("POST", "posts", post_data)
    if result and len(result) > 0:
        return jsonify({"success": True, "post": result[0]})
    post_counter += 1
    post = {"id": post_counter, **post_data, "created_at": datetime.utcnow().isoformat()}
    posts_cache[post_counter] = post
    return jsonify({"success": True, "post": post})

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    db_request("DELETE", "posts", params={"id": f"eq.{post_id}"})
    posts_cache.pop(post_id, None)
    return jsonify({"success": True})

@app.route('/api/posts/<int:post_id>/publish', methods=['POST'])
def publish_post(post_id):
    result = db_request("GET", "posts", params={"id": f"eq.{post_id}", "select": "*"})
    post = result[0] if result else posts_cache.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    results = {}
    for platform in post.get("platforms", []):
        tok = db_request("GET", "platform_tokens", params={"platform": f"eq.{platform}", "select": "*"})
        token = tok[0] if tok else tokens_cache.get(platform, {})
        if not token.get("access_token"):
            results[platform] = {"success": False, "error": "Not connected"}
            continue

        try:
            with httpx.Client() as client:
                if platform == "twitter":
                    r = client.post("https://api.twitter.com/2/tweets", headers={"Authorization": f"Bearer {token['access_token']}"}, json={"text": post["content"][:280]})
                    results[platform] = {"success": r.status_code in [200,201], "error": r.text[:50] if r.status_code not in [200,201] else None}
                elif platform == "facebook":
                    r = client.post(f"https://graph.facebook.com/v18.0/{token.get('page_id')}/feed", params={"access_token": token["access_token"], "message": post["content"]})
                    results[platform] = {"success": "id" in r.json(), "error": r.json().get("error", {}).get("message") if "id" not in r.json() else None}
                elif platform == "linkedin":
                    u = client.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {token['access_token']}"})
                    uid = u.json().get("sub")
                    r = client.post("https://api.linkedin.com/v2/ugcPosts", headers={"Authorization": f"Bearer {token['access_token']}", "X-Restli-Protocol-Version": "2.0.0"}, json={"author": f"urn:li:person:{uid}", "lifecycleState": "PUBLISHED", "specificContent": {"com.linkedin.ugc.ShareContent": {"shareCommentary": {"text": post["content"]}, "shareMediaCategory": "NONE"}}, "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}})
                    results[platform] = {"success": r.status_code in [200,201]}
                elif platform.startswith("instagram"):
                    if not post.get("image_url"):
                        results[platform] = {"success": False, "error": "Image required"}
                        continue
                    c = client.post(f"https://graph.facebook.com/v18.0/{token.get('account_id')}/media", params={"access_token": token["access_token"], "image_url": post["image_url"], "caption": post["content"]})
                    if "id" in c.json():
                        p = client.post(f"https://graph.facebook.com/v18.0/{token.get('account_id')}/media_publish", params={"access_token": token["access_token"], "creation_id": c.json()["id"]})
                        results[platform] = {"success": "id" in p.json()}
                    else:
                        results[platform] = {"success": False, "error": c.json().get("error", {}).get("message")}
                else:
                    results[platform] = {"success": False, "error": "Not supported"}
        except Exception as e:
            results[platform] = {"success": False, "error": str(e)[:50]}

    new_status = "posted" if any(r["success"] for r in results.values()) else "failed"
    db_request("PATCH", "posts", {"status": new_status, "posted_time": datetime.utcnow().isoformat()}, {"id": f"eq.{post_id}"})

    return jsonify({"success": all(r["success"] for r in results.values()), "results": results})

@app.route('/api/platforms/scheduler/jobs')
def scheduler_jobs():
    result = db_request("GET", "posts", params={"status": "eq.scheduled"})
    return jsonify({"jobs": result or [], "total": len(result or [])})

if __name__ == '__main__':
    app.run(debug=True)
