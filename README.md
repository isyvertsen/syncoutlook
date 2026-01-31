# Outlook → Google Calendar Sync

One-way calendar sync from Microsoft Outlook to Google Calendar with AI-powered event filtering.

## Features

- **One-way sync** from Outlook (via published ICS feed) to Google Calendar
- **AI-powered filtering** to decide which events to sync (supports OpenAI, Azure OpenAI, NEAR AI)
- **Smart deduplication** using event IDs to avoid duplicates
- **Caching** of AI decisions to reduce API costs
- **Docker deployment** for easy self-hosting
- **Scheduler** for automatic hourly sync

## Quick Start with Docker

### 1. Prerequisites

- Docker and Docker Compose installed
- Outlook calendar published as ICS feed
- Google Cloud project with Calendar API enabled
- API key for your chosen AI provider (OpenAI, Azure, or NEAR AI)

### 2. Setup

```bash
# Clone the repository
git clone <repository-url>
cd syncoutlook

# Copy environment template
cp .env.example .env

# Edit .env with your configuration (see Configuration section below)
```

### 3. Google Calendar Authentication

Before running Docker, you need to authenticate with Google Calendar locally:

```bash
# Install dependencies
uv pip install -r requirements.txt

# Run once to complete OAuth flow (opens browser)
python google_client.py

# This creates google_token.json which Docker will use
```

### 4. Run with Docker

```bash
# Build and start the container
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Configuration

All configuration is done via environment variables in `.env`:

### Required Settings

| Variable | Description |
|----------|-------------|
| `OUTLOOK_ICS_URL` | Your published Outlook calendar ICS URL |
| `GOOGLE_CALENDAR_ID` | Target Google Calendar ID (use `primary` for main calendar) |

### AI Provider Settings

Choose one of three AI providers by setting `AI_PROVIDER`:

#### Option 1: OpenAI (Recommended)

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=gpt-4o-mini
```

#### Option 2: Azure OpenAI

```env
AI_PROVIDER=azure
AZURE_OPENAI_API_KEY=your-azure-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Optional: Use Azure AD / Entra ID instead of API key
# AZURE_TENANT_ID=your-tenant-id
# AZURE_CLIENT_ID=your-client-id
# AZURE_CLIENT_SECRET=your-client-secret
```

#### Option 3: NEAR AI

```env
AI_PROVIDER=near_ai
NEAR_AI_API_KEY=your-near-ai-api-key
NEAR_AI_MODEL=openai/gpt-oss-120b
```

### Filter Mode

```env
# "ai" = Use AI to decide which events to sync
# "non_recurring" = Simple rule: sync all single-day events
FILTER_MODE=non_recurring
```

### Sync Settings

```env
SYNC_DAYS_AHEAD=30        # Days ahead to sync
SYNC_DAYS_BACK=7          # Days back to sync
REMINDER_MINUTES=10       # Reminder before events (0 to disable)
SYNC_INTERVAL=15          # Minutes between syncs (scheduler)
DRY_RUN=false             # Set to true for testing
```

## AI Filter Prompt

The AI prompt that determines which events get synced is defined in `config.py`. You can customize the rules to match your preferences:

```python
AI_FILTER_PROMPT = """You are a calendar assistant. Based on the following calendar event,
determine whether it should be synced to my personal Google Calendar.

Event details:
- Title: {title}
- Time: {start} - {end}
- Organizer: {organizer}
- Description: {body}
- Categories: {categories}
- Is all-day event: {is_all_day}
- Status: {status}

SYNC RULES:
1. SYNC important external meetings with customers or partners
2. SYNC conferences, seminars, and important events
3. SYNC personal appointments and vacation/time-off
4. DO NOT SYNC internal team meetings or stand-ups
5. DO NOT SYNC routine status meetings
6. DO NOT SYNC "focus time" or blocked time slots
7. When in doubt, prefer to sync rather than skip

Respond ONLY with valid JSON in this format:
{"sync": true, "reason": "brief explanation"}
or
{"sync": false, "reason": "brief explanation"}
"""
```

### Customizing the Prompt

Edit `config.py` and modify the `AI_FILTER_PROMPT` variable. The available placeholders are:

| Placeholder | Description |
|-------------|-------------|
| `{title}` | Event title |
| `{start}` | Start time (ISO format) |
| `{end}` | End time (ISO format) |
| `{organizer}` | Event organizer |
| `{body}` | Event description (truncated to 1000 chars) |
| `{categories}` | Event categories |
| `{is_all_day}` | "Yes" or "No" |
| `{status}` | Event status (busy, free, tentative, etc.) |

## Manual Usage

### Run Sync Manually

```bash
# Dry run (preview changes without applying)
python sync_calendar.py --dry-run

# Full sync
python sync_calendar.py

# Verbose logging
python sync_calendar.py --verbose

# Clear AI decision cache
python sync_calendar.py --clear-cache

# Force sync (ignore last sync time)
python sync_calendar.py --force
```

### Test Components

```bash
# Test Outlook ICS feed
python outlook_client.py

# Test Google Calendar connection
python google_client.py

# Test AI filtering
python ai_filter.py
```

## Getting Outlook ICS URL

1. Go to [Outlook Web](https://outlook.office365.com)
2. Click **Settings** (gear icon) → **View all Outlook settings**
3. Go to **Calendar** → **Shared calendars**
4. Under "Publish a calendar", select your calendar
5. Choose "Can view all details" for permissions
6. Click **Publish** and copy the ICS link

## Setting Up Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable the **Google Calendar API**
4. Go to **Credentials** → **Create Credentials** → **OAuth client ID**
5. Choose "Desktop app" as application type
6. Download the credentials and save as `credentials.json` in project root

## Architecture

```
sync_calendar.py      Main orchestrator
    ├── outlook_client.py   Fetches events from Outlook ICS feed
    ├── google_client.py    CRUD operations on Google Calendar
    ├── ai_filter.py        AI filtering (OpenAI/Azure/NEAR AI)
    └── config.py           All settings and AI prompt

scheduler.py          Hourly sync scheduler for Docker

Data flow:
Outlook ICS → Parse events → AI filter (cached) → Google Calendar API
```

## Files

| File | Description |
|------|-------------|
| `credentials.json` | Google OAuth credentials (from Cloud Console) |
| `google_token.json` | Google OAuth token (auto-generated) |
| `ai_decisions_cache.json` | Cached AI decisions (auto-generated) |
| `.env` | Environment configuration |
| `sync.log` | Sync log file |

## Troubleshooting

### "No events found in Outlook calendar"

- Verify the ICS URL is correct and accessible
- Check if the calendar is published with correct permissions
- Some corporate calendars block external access

### "Google Calendar API error"

- Ensure `credentials.json` exists in project root
- Delete `google_token.json` and re-authenticate
- Verify Calendar API is enabled in Google Cloud Console

### "AI API error"

- Check your API key is valid
- Verify the correct provider is set in `AI_PROVIDER`
- For Azure: check endpoint URL and deployment name
- Try running with `--verbose` for detailed error messages

### Events not syncing as expected

- Check `FILTER_MODE` setting
- Clear AI cache: `python sync_calendar.py --clear-cache`
- Review the AI prompt in `config.py`
- Enable verbose logging to see AI decisions

## License

MIT
