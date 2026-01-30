# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Outlook → Google Calendar sync tool with AI-powered filtering. Fetches events from Outlook via published ICS feed, uses NEAR AI to decide which events to sync, then creates/updates/deletes events in Google Calendar.

**Package manager:** Use `uv` for all Python package operations.

## Commands

```bash
# Install dependencies (use uv)
uv pip install -r requirements.txt

# Run sync (dry-run first)
python sync_calendar.py --dry-run

# Full sync
python sync_calendar.py

# Verbose logging
python sync_calendar.py --verbose

# Clear AI decision cache
python sync_calendar.py --clear-cache

# Test individual components
python outlook_client.py    # Test ICS feed fetch
python google_client.py     # Test Google Calendar connection
python ai_filter.py         # Test AI filtering with sample events
```

## Architecture

```
sync_calendar.py      Entry point, orchestrates the sync flow
    ├── outlook_client.py   Fetches events from Outlook ICS feed
    ├── google_client.py    CRUD operations on Google Calendar
    ├── ai_filter.py        NEAR AI integration for event filtering
    └── config.py           All settings loaded from .env
```

**Data flow:** Outlook ICS → Parse events → AI filter (cached) → Google Calendar API

**Key mechanisms:**
- Events are linked via `outlookEventId` stored in Google Calendar's `extendedProperties`
- AI decisions are cached by event hash (title + organizer + body + categories) in `ai_decisions_cache.json`
- ICS feed requires no authentication (published URL from Outlook settings)

## Configuration

All settings in `.env` (copy from `.env.example`):
- `OUTLOOK_ICS_URL` - Published calendar ICS URL
- `NEAR_AI_API_KEY` - API key for NEAR AI
- `GOOGLE_CALENDAR_ID` - Target calendar (default: "primary")

AI filtering rules are in `config.py` → `AI_FILTER_PROMPT`. Edit this to customize sync behavior.

## Required Files

- `credentials.json` - Google OAuth credentials (download from Google Cloud Console)
- `.env` - Environment variables
