# Social Media Dashboard

A full-stack social media content management dashboard with AI-powered content generation. Post to LinkedIn, Twitter/X, Facebook, and Instagram from one place.

## Features

- **AI Content Generation** - Generate educational, motivational, or custom posts using GPT-4o
- **Image Generation** - Create images with DALL-E 3
- **Multi-Platform Posting** - Post to LinkedIn, Twitter/X, Facebook, and Instagram
- **Approval Queue** - Review AI-generated content before publishing
- **Scheduling** - Schedule posts for later
- **Hybrid Automation** - Mix of auto-posting and manual approval

## Tech Stack

- **Backend**: Python + FastAPI (Vercel Serverless Functions)
- **Frontend**: React + TypeScript + Tailwind CSS
- **AI**: OpenAI GPT-4o + DALL-E 3

---

## Deploy to Vercel (Recommended)

### Step 1: Push to GitHub

```bash
cd social-media-dashboard
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/social-media-dashboard.git
git push -u origin main
```

### Step 2: Deploy on Vercel

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click **"Add New Project"**
3. Import your GitHub repository
4. Vercel will auto-detect the config - just click **Deploy**

### Step 3: Add Environment Variables

In Vercel Dashboard → Your Project → Settings → Environment Variables:

| Variable | Value |
|----------|-------|
| `OPENAI_API_KEY` | `sk-your-openai-key` |
| `LINKEDIN_ACCESS_TOKEN` | Your LinkedIn token |
| `TWITTER_API_KEY` | Your Twitter API key |
| `TWITTER_API_SECRET` | Your Twitter API secret |
| `TWITTER_ACCESS_TOKEN` | Your Twitter access token |
| `TWITTER_ACCESS_TOKEN_SECRET` | Your Twitter access token secret |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | Your Facebook page token |
| `FACEBOOK_PAGE_ID` | Your Facebook page ID |
| `INSTAGRAM_ACCOUNT_ID` | Your Instagram account ID |

### Step 4: Redeploy

After adding environment variables, go to Deployments → click "..." → Redeploy

**Done!** Your dashboard is live at `your-project.vercel.app`

---

## Local Development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at: http://localhost:5173

### Backend (for local testing)

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Runs at: http://localhost:8000

---

## Getting API Credentials

### OpenAI (Required)
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add as `OPENAI_API_KEY`

### LinkedIn
1. Go to https://www.linkedin.com/developers/apps
2. Create an app
3. Get OAuth 2.0 access token with `w_member_social` scope
4. Add as `LINKEDIN_ACCESS_TOKEN`

### Twitter/X
1. Go to https://developer.twitter.com/en/portal/dashboard
2. Create a project and app (with OAuth 1.0a)
3. Get API Key, Secret, Access Token, and Access Token Secret
4. Add all four values

### Facebook & Instagram
1. Go to https://developers.facebook.com/
2. Create an app with Facebook Login
3. Get Page Access Token with `pages_manage_posts` permission
4. For Instagram, link your Instagram Business Account to the Page
5. Add `FACEBOOK_PAGE_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`, and `INSTAGRAM_ACCOUNT_ID`

---

## Project Structure

```
social-media-dashboard/
├── api/
│   ├── index.py           # Vercel serverless function (FastAPI)
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/         # Dashboard, CreatePost, Queue, History, Settings
│   │   ├── components/    # Layout, UI components
│   │   └── services/      # API client
│   ├── package.json
│   └── vite.config.ts
├── backend/               # Full backend (for local dev)
│   └── ...
├── vercel.json           # Vercel configuration
└── README.md
```

---

## Usage

1. **Create Post**: Generate AI content or write manually
2. **Review**: Posts go to approval queue
3. **Approve/Schedule**: Approve for immediate posting or schedule
4. **Publish**: Post to selected platforms
5. **Track**: View post history

---

## Important Notes

### Data Persistence
The Vercel serverless version uses in-memory storage (data resets on cold starts). For persistent storage, you can:

1. **Vercel KV** (Redis) - Add `@vercel/kv` package
2. **Vercel Postgres** - Add PostgreSQL database
3. **Supabase** - Free PostgreSQL hosting

### Scheduled Posts
Vercel Cron Jobs can be added for scheduled posting. Add to `vercel.json`:

```json
{
  "crons": [{
    "path": "/api/cron/publish",
    "schedule": "0 * * * *"
  }]
}
```

---

## License

MIT
