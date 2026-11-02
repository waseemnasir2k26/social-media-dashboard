# Social Media Dashboard

A self-hosted posting tool: write one post, send it to several social accounts, keep a history. FastAPI backend, React and TypeScript frontend, deployable on Vercel.

## What it does

- Posts to X, LinkedIn, Facebook Page, Instagram and YouTube through each platform's API
- Optional OpenAI helper for drafting post copy
- Post history and a settings page for platform connections
- `n8n-linkedin-workflow.json`: an importable n8n workflow for LinkedIn

## Run it locally

Backend:

```bash
cd backend
python -m venv venv && venv\Scripts\activate    # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # add your own platform keys
```

Frontend:

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

`start-backend.bat` and `start-frontend.bat` do the same on Windows. For Vercel, set the platform credentials as environment variables; `vercel.json` and `api/index.py` route the backend.

## Credentials

You need your own developer apps and tokens for each platform (Meta, X, Google, LinkedIn). The keys go in environment variables, never in the repo.

## Status and limits

Posting only. There is no analytics or engagement reporting, despite the older repo description. Platform approval rules (Instagram publishing, LinkedIn products) apply to you. Verify each platform against your own accounts before relying on it.

MIT.

For you if: you post to a handful of your own accounts and want a free, hackable alternative to a scheduler.

---

Need this wired into your business? SkynetLabs builds voice agents, n8n back offices and sites that convert → https://skynetjoe.com
Contact: waseem@skynetjoe.com
