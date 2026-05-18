"""Configuration and settings for calendar sync."""

import os
from dotenv import load_dotenv

load_dotenv()

# Outlook Calendar ICS feed URL
# Get this from Outlook Web: Settings → Calendar → Shared calendars → Publish a calendar
OUTLOOK_ICS_URL = os.getenv("OUTLOOK_ICS_URL")

# Google Calendar settings
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json"
)
# Service account key JSON passed directly via env (recommended for Coolify /
# container deploys so no key file is ever copied into the image or repo).
# Takes precedence over the file above.
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]

# =============================================================================
# AI Provider Configuration
# =============================================================================
# Supported providers: "openai", "azure", "near_ai"
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")

# --- OpenAI Settings ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- Azure OpenAI Settings ---
# Azure uses: https://{resource}.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version={version}
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  # e.g., https://myresource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")  # Your deployment name
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
# Azure AD / Entra ID authentication (optional, alternative to API key)
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

# --- NEAR AI Settings (legacy) ---
NEAR_AI_API_KEY = os.getenv("NEAR_AI_API_KEY")
NEAR_AI_API_URL = os.getenv("NEAR_AI_API_URL", "https://cloud-api.near.ai/v1/chat/completions")
NEAR_AI_MODEL = os.getenv("NEAR_AI_MODEL", "openai/gpt-oss-120b")

# =============================================================================
# Sync Settings
# =============================================================================
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

# =============================================================================
# AI Filter Prompt - CUSTOMIZE THIS FOR YOUR NEEDS
# =============================================================================
# This prompt determines which events get synced. Edit the rules to match your preferences.
# Available placeholders: {title}, {start}, {end}, {organizer}, {body}, {categories}, {is_all_day}, {status}

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
{{"sync": true, "reason": "brief explanation"}}
or
{{"sync": false, "reason": "brief explanation"}}
"""


def get_ai_config() -> dict:
    """Get the active AI provider configuration.

    Returns:
        dict with keys: provider, api_key, api_url, model, headers
    """
    provider = AI_PROVIDER.lower()

    if provider == "azure":
        if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT]):
            raise ValueError("Azure OpenAI requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT")

        api_url = (
            f"{AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai/deployments/"
            f"{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
        )

        # Azure uses api-key header instead of Bearer token
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_API_KEY or "",
        }

        return {
            "provider": "azure",
            "api_key": AZURE_OPENAI_API_KEY,
            "api_url": api_url,
            "model": AZURE_OPENAI_DEPLOYMENT,  # Azure uses deployment name as model
            "headers": headers,
        }

    elif provider == "near_ai":
        if not NEAR_AI_API_KEY:
            raise ValueError("NEAR AI requires NEAR_AI_API_KEY")

        return {
            "provider": "near_ai",
            "api_key": NEAR_AI_API_KEY,
            "api_url": NEAR_AI_API_URL,
            "model": NEAR_AI_MODEL,
            "headers": {
                "Authorization": f"Bearer {NEAR_AI_API_KEY}",
                "Content-Type": "application/json",
            },
        }

    else:  # Default: OpenAI
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI requires OPENAI_API_KEY")

        return {
            "provider": "openai",
            "api_key": OPENAI_API_KEY,
            "api_url": OPENAI_API_URL,
            "model": OPENAI_MODEL,
            "headers": {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
        }
