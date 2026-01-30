"""Configuration and settings for calendar sync."""

import os
from dotenv import load_dotenv

load_dotenv()

# Outlook Calendar ICS feed URL
# Get this from Outlook Web: Settings → Calendar → Shared calendars → Publish a calendar
OUTLOOK_ICS_URL = os.getenv("OUTLOOK_ICS_URL")

# Google Calendar settings
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_CREDENTIALS_FILE = "credentials.json"
GOOGLE_TOKEN_FILE = "google_token.json"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]

# NEAR AI settings
NEAR_AI_API_KEY = os.getenv("NEAR_AI_API_KEY")
NEAR_AI_API_URL = "https://cloud-api.near.ai/v1/chat/completions"
NEAR_AI_MODEL = os.getenv("NEAR_AI_MODEL", "openai/gpt-oss-120b")

# Sync settings
SYNC_DAYS_AHEAD = int(os.getenv("SYNC_DAYS_AHEAD", "30"))
SYNC_DAYS_BACK = int(os.getenv("SYNC_DAYS_BACK", "7"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
LOG_FILE = os.getenv("LOG_FILE", "sync.log")

# Filter mode: "ai" for AI-based filtering, "non_recurring" for simple rule
FILTER_MODE = os.getenv("FILTER_MODE", "non_recurring")

# Reminder settings (minutes before event, 0 to disable)
REMINDER_MINUTES = int(os.getenv("REMINDER_MINUTES", "10"))


# AI decision cache
AI_DECISION_CACHE_FILE = "ai_decisions_cache.json"

# AI Filter Prompt - CUSTOMIZE THIS FOR YOUR NEEDS
AI_FILTER_PROMPT = """Du er en kalenderassistent. Basert på følgende avtale, bestem om den
skal synkroniseres til min personlige Google-kalender.

Avtaleinfo:
- Tittel: {title}
- Tidspunkt: {start} - {end}
- Organisator: {organizer}
- Beskrivelse: {body}
- Kategorier: {categories}
- Er heldagsarrangement: {is_all_day}
- Status: {status}

REGLER FOR SYNKRONISERING:
1. Synkroniser viktige eksterne møter med kunder eller partnere
2. Synkroniser konferanser, seminarer og viktige arrangementer
3. Synkroniser personlige avtaler og ferie
4. IKKE synkroniser interne teammøter eller stand-ups
5. IKKE synkroniser rutinemessige statusmøter
6. IKKE synkroniser "fokustid" eller blokkert tid
7. Ved tvil, synkroniser heller enn å utelate

Svar KUN med gyldig JSON på denne formen:
{{"sync": true, "reason": "kort forklaring"}}
eller
{{"sync": false, "reason": "kort forklaring"}}
"""
