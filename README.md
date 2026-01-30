# Outlook → Google Calendar Sync med AI-filtrering

Synkroniserer Outlook-kalender (Microsoft 365) til Google Calendar, med NEAR AI for å filtrere hvilke avtaler som skal inkluderes.

## Funksjoner

- Henter kalenderhendelser fra Outlook via publisert ICS-feed (ingen app-registrering nødvendig!)
- Bruker NEAR AI til å bestemme hvilke hendelser som skal synkroniseres
- Synkroniserer godkjente hendelser til Google Calendar
- Håndterer oppdateringer og slettinger automatisk
- Cacher AI-beslutninger for å spare API-kall
- Støtter dry-run modus for testing

## Oppsett

### 1. Installer avhengigheter

```bash
pip install -r requirements.txt
```

### 2. Publiser Outlook-kalender som ICS

1. Gå til [outlook.office.com](https://outlook.office.com)
2. Klikk på kalender-ikonet (📅)
3. Klikk på tannhjulet (⚙️) → **View all Outlook settings**
4. Gå til **Calendar** → **Shared calendars**
5. Under **Publish a calendar**, velg din kalender
6. Velg **"Can view all details"**
7. Klikk **Publish**
8. Kopier **ICS**-lenken

### 3. Konfigurer Google Calendar API

1. Gå til [Google Cloud Console](https://console.cloud.google.com)
2. Opprett et nytt prosjekt (eller velg et eksisterende)
3. Gå til "APIs & Services" → "Library"
4. Søk etter "Google Calendar API" og aktiver den
5. Gå til "APIs & Services" → "Credentials"
6. Klikk "Create Credentials" → "OAuth client ID"
7. Velg "Desktop app" som applikasjonstype
8. Last ned JSON-filen og lagre den som `credentials.json` i prosjektmappen

### 4. Få NEAR AI API-nøkkel

1. Gå til [NEAR AI](https://app.near.ai)
2. Opprett en API-nøkkel

### 5. Konfigurer miljøvariabler

Kopier `.env.example` til `.env` og fyll inn verdiene:

```bash
cp .env.example .env
```

Rediger `.env`:

```
OUTLOOK_ICS_URL=https://outlook.office365.com/owa/calendar/.../calendar.ics
NEAR_AI_API_KEY=din-near-ai-api-nøkkel
NEAR_AI_MODEL=openai/gpt-oss-120b
GOOGLE_CALENDAR_ID=primary
SYNC_DAYS_AHEAD=30
SYNC_DAYS_BACK=7
```

## Bruk

### Test uten å gjøre endringer (dry-run)

```bash
python sync_calendar.py --dry-run
```

### Kjør full synkronisering

```bash
python sync_calendar.py
```

### Med verbose logging

```bash
python sync_calendar.py --verbose
```

### Tøm AI-cache

```bash
python sync_calendar.py --clear-cache
```

## Tilpass AI-filtrering

Rediger `AI_FILTER_PROMPT` i `config.py` for å tilpasse reglene for hvilke hendelser som skal synkroniseres.

Eksempel på tilpasning:

```python
AI_FILTER_PROMPT = """
...
REGLER FOR SYNKRONISERING:
1. Synkroniser alle møter med eksterne deltakere
2. Synkroniser ferie og fridager
3. IKKE synkroniser daglige stand-ups
4. IKKE synkroniser interne planleggingsmøter
...
"""
```

## Automatisk kjøring (Windows Task Scheduler)

1. Åpne Task Scheduler
2. Klikk "Create Basic Task"
3. Gi den et navn (f.eks. "Calendar Sync")
4. Velg trigger (f.eks. "Daily" eller "When I log on")
5. Velg "Start a program"
6. Program: `python` (eller full path til python.exe)
7. Arguments: `C:\path\to\sync_calendar.py`
8. Start in: `C:\path\to\syncoutlook`

## Filer

| Fil | Beskrivelse |
|-----|-------------|
| `sync_calendar.py` | Hovedskript for synkronisering |
| `outlook_client.py` | Outlook ICS-feed klient |
| `google_client.py` | Google Calendar API-klient |
| `ai_filter.py` | Claude AI-filtrering |
| `config.py` | Konfigurasjon og innstillinger |
| `requirements.txt` | Python-avhengigheter |

## Genererte filer (ignoreres i git)

- `google_token.json` - Google token cache
- `ai_decisions_cache.json` - AI-beslutninger cache
- `sync.log` - Loggfil
- `.env` - Miljøvariabler
- `credentials.json` - Google credentials

## Feilsøking

### "OUTLOOK_ICS_URL not configured"
- Sjekk at du har lagt ICS-URLen i `.env`-filen

### "ICS feed returned status 404"
- Kalenderen er kanskje ikke lenger publisert
- Gå til Outlook-innstillinger og publiser på nytt

### "Google credentials file not found"
- Last ned `credentials.json` fra Google Cloud Console
- Plasser filen i prosjektmappen

### "NEAR AI API error"
- Sjekk at `NEAR_AI_API_KEY` er gyldig
- Sjekk at du har tilgjengelig kvote

### Token-problemer med Google
- Slett `google_token.json` for å tvinge ny autentisering
