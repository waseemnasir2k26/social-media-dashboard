# Social Media Dashboard - Simple Posting Tool

A free, simple social media dashboard to post content across multiple platforms at once. Like Buffer, but free and self-hosted on Vercel.

## Supported Platforms

- **Facebook Page** (1 page)
- **Instagram** (2 accounts)
- **Twitter/X** (1 account)
- **YouTube** (1 channel)
- **LinkedIn** (1 profile)

## Features

- **Multi-Platform Posting** - Post to 6 platforms with one click
- **Simple Dashboard** - Clean, easy-to-use interface
- **Image & Video Support** - Share media across platforms
- **Post History** - Track all your posts and their status
- **OAuth Integration** - Secure connection to all platforms
- **100% Free** - Self-hosted on Vercel's free tier

## Tech Stack

- **Backend**: Python + FastAPI (Vercel Serverless Functions)
- **Frontend**: React + TypeScript + Tailwind CSS
- **Hosting**: Vercel (Free)

---

## Quick Start

### 1. Deploy to Vercel

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/social-media-dashboard.git
cd social-media-dashboard

# Push to your GitHub
git remote set-url origin https://github.com/YOUR_USERNAME/social-media-dashboard.git
git push -u origin main
```

Then:
1. Go to [vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Click **Deploy**

### 2. Add Environment Variables

In Vercel Dashboard → Your Project → Settings → Environment Variables:

```bash
# Facebook & Instagram (Meta)
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret

# Twitter/X
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret

# YouTube (Google)
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret

# LinkedIn
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
```

### 3. Redeploy

After adding environment variables, redeploy your app.

---

## Getting API Credentials

### Facebook & Instagram (Meta)

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create a new app (Type: Business)
3. Add **Facebook Login** product
4. Add callback URL: `https://your-app.vercel.app/api/auth/facebook/callback`
5. Request permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_content_publish`
   - `business_management`
6. Link your Instagram Business accounts to your Facebook Pages

**Note**: Both Instagram accounts will be detected automatically when you connect Facebook.

### Twitter/X

1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Create a project and app
3. Enable OAuth 2.0 with "Read and write" permissions
4. Add callback URL: `https://your-app.vercel.app/api/auth/twitter/callback`

### YouTube (Google)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project
3. Enable **YouTube Data API v3**
4. Create OAuth 2.0 credentials
5. Add callback URL: `https://your-app.vercel.app/api/auth/youtube/callback`

### LinkedIn

1. Go to [linkedin.com/developers](https://www.linkedin.com/developers/apps)
2. Create a new app
3. Request products:
   - "Share on LinkedIn"
   - "Sign In with LinkedIn using OpenID Connect"
4. Add callback URL: `https://your-app.vercel.app/api/auth/linkedin/callback`

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

## Project Structure

```
social-media-dashboard/
├── api/
│   ├── index.py           # Vercel serverless function (FastAPI)
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/         # Dashboard, CreatePost, History, Settings
│   │   ├── components/    # Layout, UI components
│   │   └── services/      # API client
│   ├── package.json
│   └── vite.config.ts
├── vercel.json            # Vercel configuration
└── README.md
```

---

## Usage

1. **Connect Accounts**: Go to Settings and connect your social media accounts
2. **Create Post**: Write your content, add media (optional)
3. **Select Platforms**: Choose which platforms to post to
4. **Publish**: Click "Publish Now" or save as draft

---

## Notes

### Data Persistence

The Vercel serverless version uses in-memory storage (data resets on cold starts). For persistent storage, consider:

- **Vercel KV** (Redis) - Add `@vercel/kv` package
- **Vercel Postgres** - PostgreSQL database
- **Supabase** - Free PostgreSQL hosting

### Instagram Requirements

- Requires a Facebook Page linked to an Instagram Business account
- Image/Video URL must be publicly accessible
- Videos must be in MP4 format

### Platform Limits

| Platform | Character Limit |
|----------|-----------------|
| Twitter | 280 characters |
| LinkedIn | 3,000 characters |
| Facebook | 63,206 characters |
| Instagram | 2,200 characters |
| YouTube | Varies by field |

---

## License

MIT

---

<!-- SEO-HIRE-ME-BLOCK -->

## Hire Me

> **Need a custom social media or marketing dashboard?**

I'm **Waseem Nasir** — founder of [Skynet Labs / SkynetJoe](https://www.skynetjoe.com), an AI Automation Agency. OAuth-based multi-platform dashboards (LinkedIn, Twitter, Instagram, TikTok, YouTube).

**50+ live projects across:** Healthcare · Legal · Real Estate · E-Commerce · Logistics · HVAC · SaaS · Consulting

### Hire me
- 📅 **[Book a free strategy call](https://calendly.com/skynetlabs/schedule-a-free-consultation)**
- 💼 **[Hire on Fiverr](https://fiverr.com/agencies/skynetjoellc)**
- 🌐 **[skynetjoe.com](https://www.skynetjoe.com)**
- 📧 **info@skynetjoe.com**
- 💬 **[WhatsApp](https://wa.me/923001001957)**

### Related projects on my GitHub
- [n8n-social-automation](https://github.com/waseemnasir2k26/n8n-social-automation)
- [ai-motivational-posts](https://github.com/waseemnasir2k26/ai-motivational-posts)
- [aeo-content-engine](https://github.com/waseemnasir2k26/aeo-content-engine)
- [→ See all 50+ projects](https://github.com/waseemnasir2k26)

### Tags
`AI automation` · `n8n` · `GoHighLevel` · `Claude Code` · `Next.js` · `React` · `Python` · `freelance` · `hire me` · `agency`
