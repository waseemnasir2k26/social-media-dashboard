# Changelog

All notable changes to this project are documented in this file.

## [2026.10] - 2026-10-12

- social-media-dashboard is a public, self-hosted multi-platform posting tool (Facebook Page, Instagram, X, YouTube, LinkedIn): FastAPI backend plus React/TypeScript/Vite frontend, with an n8n LinkedIn workflow export.
- State: last feature work was March 2026; a Hire Me block was added 2026-04-07. No application code changed this month.
- Reviewed October 2026: README, tree and history read; README external links (Calendly, Fiverr, platform developer consoles, cross-linked repos) return 200. The Hire Me links were updated to the current Fiverr, Upwork and Calendly URLs, and a MIT LICENSE was added because the README states MIT.
- Known gaps: the Vercel serverless deployment uses in-memory storage so history resets on cold starts (the README suggests KV/Postgres/Supabase); no root package.json, so no version to bump; no tests or CI.

## [2026.09] - 2026-09-16

- Maintenance review of social-media-dashboard — a free, self-hosted multi-platform social posting tool (Facebook Page, Instagram, X/Twitter, YouTube, LinkedIn) positioned as a Buffer alternative.
- Status: Python + FastAPI backend (`backend/app`, plus a Vercel serverless entry at `api/index.py`) with a React + TypeScript + Tailwind frontend built by Vite in `frontend/`. Ships `vercel.json`, Windows `start-backend.bat` / `start-frontend.bat` helpers and an `n8n-linkedin-workflow.json` companion workflow. MIT licensed per the README.
- Reviewed September 2026: documentation refreshed and the repo versioned as v2026.09. No application code changes.
- Known gaps: the serverless deployment uses in-memory storage, so post history resets on cold starts (README flags Vercel KV/Postgres or Supabase as the fix); there is no root `package.json`, so no version field was bumped this release and `frontend/package.json` remains at 1.0.0; no LICENSE file despite the MIT claim; no CHANGELOG before this release; no tests or CI.
