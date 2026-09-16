# Changelog

All notable changes to this project are documented in this file.

## [2026.09] - 2026-09-16

- Maintenance review of social-media-dashboard — a free, self-hosted multi-platform social posting tool (Facebook Page, Instagram, X/Twitter, YouTube, LinkedIn) positioned as a Buffer alternative.
- Status: Python + FastAPI backend (`backend/app`, plus a Vercel serverless entry at `api/index.py`) with a React + TypeScript + Tailwind frontend built by Vite in `frontend/`. Ships `vercel.json`, Windows `start-backend.bat` / `start-frontend.bat` helpers and an `n8n-linkedin-workflow.json` companion workflow. MIT licensed per the README.
- Reviewed September 2026: documentation refreshed and the repo versioned as v2026.09. No application code changes.
- Known gaps: the serverless deployment uses in-memory storage, so post history resets on cold starts (README flags Vercel KV/Postgres or Supabase as the fix); there is no root `package.json`, so no version field was bumped this release and `frontend/package.json` remains at 1.0.0; no LICENSE file despite the MIT claim; no CHANGELOG before this release; no tests or CI.
