# Outlook → Google Calendar Sync

One-way sync from Outlook (ICS feed) to Google Calendar with AI filtering.

## Quick Start

```bash
cp .env.example .env
# Edit .env with your values

# Get Google token (first time only)
uv pip install -r requirements.txt
python google_client.py

# Run
docker compose up -d
```

## Configuration (.env)

```env
# Required
OUTLOOK_ICS_URL=https://outlook.office365.com/owa/calendar/.../calendar.ics
GOOGLE_CALENDAR_ID=primary

# AI Provider: openai (default), azure, near_ai
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Azure alternative
# AI_PROVIDER=azure
# AZURE_OPENAI_API_KEY=...
# AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com
# AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Filter: "ai" or "non_recurring" (default)
FILTER_MODE=non_recurring
```

## Commands

```bash
python sync_calendar.py              # Run sync
python sync_calendar.py --dry-run    # Preview only
python sync_calendar.py --clear-cache # Clear AI cache
```

## AI Prompt

Edit `config.py` → `AI_FILTER_PROMPT` to customize filtering rules.

## Files

| Generated | Purpose |
|-----------|---------|
| `google_token.json` | OAuth token |
| `ai_decisions_cache.json` | AI cache |
| `credentials.json` | Google OAuth (download from Cloud Console) |
