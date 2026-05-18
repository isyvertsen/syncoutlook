# Design: Switch Google Calendar auth to a service account

**Date:** 2026-05-18
**Status:** Approved

## Problem

The sync runs as a headless Docker scheduler but authenticates to Google
Calendar with user OAuth (`InstalledAppFlow.run_local_server`). Two failures
result:

1. The refresh token is rejected with `invalid_grant` — the OAuth consent
   screen is in "Testing" status, where Google expires refresh tokens after
   7 days.
2. On refresh failure the code falls back to opening a browser, which crashes
   in the container (`webbrowser.Error: could not locate runnable browser`).

User OAuth is the wrong mechanism for an unattended server process.

## Goal

Authenticate with a Google **service account** so the container needs no
browser, no per-user token, and has no 7-day expiry. Full replacement of the
OAuth path (decided: no fallback).

## Non-goals

- Domain-wide delegation (unavailable on personal Gmail, not needed — the
  target calendar is shared directly with the service account).
- Changing the sync logic or any CRUD behavior.

## Approach

`google-auth>=2.0.0` is already in `requirements.txt`, so
`google.oauth2.service_account` is available — no new dependency.

The target calendar (`GOOGLE_CALENDAR_ID` in `.env`) is a secondary/group
calendar (`…@group.calendar.google.com`), which can be shared directly with
the service account's email. No Workspace admin or delegation required.

## Changes

### Code

- **`google_client.py`** — rewrite `authenticate()`:
  - Remove imports: `InstalledAppFlow`, `Credentials`, `Request`.
  - Add: `from google.oauth2 import service_account`.
  - Load `service_account.Credentials.from_service_account_file(
    config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=config.GOOGLE_SCOPES)`,
    then `build("calendar", "v3", credentials=...)`.
  - Missing file or load failure → log a clear, actionable error and
    return `False`. Never open a browser.
  - CRUD methods unchanged.
- **`config.py`**:
  - Remove `GOOGLE_CREDENTIALS_FILE`, `GOOGLE_TOKEN_FILE`.
  - Add `GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")`.
  - `GOOGLE_SCOPES` unchanged.

### Config / Docker

- **`docker-compose.yml`**: replace the
  `./google_token.json:/app/google_token.json` mount with
  `./service_account.json:/app/service_account.json`.
- **`Dockerfile`**: remove `COPY credentials.json ./` (build would fail once
  the file is gone; the key is provided via volume mount, not baked in).
- **`.gitignore`**: add `service_account.json`.
- **`requirements.txt`**: remove `google-auth-oauthlib` (no longer imported).
- Delete stale local secrets: `google_token.json`, `credentials.json`,
  `client_secret_*.json`.

### External prerequisites (user-only, cannot be automated)

1. GCP Console, project `nkcnutrions` → IAM & Admin → Service Accounts →
   create account → create JSON key → download.
2. Save the key as `service_account.json` in the project root.
3. Ensure the Google Calendar API is enabled for the project.
4. Share the target calendar (Settings → Share with specific people) with the
   service account email (`…@nkcnutrions.iam.gserviceaccount.com`) with
   "Make changes to events". Propagation can take a few minutes.

## Testing

- Unit test (`test_google_client.py`, stdlib `unittest` + `mock`, no new
  dependency):
  - `authenticate()` returns `False` and logs an error when the service
    account file is missing — no exception, no browser.
  - `authenticate()` returns `True` when `from_service_account_file` and
    `build` are mocked to succeed.
- Manual verification (after user completes the GCP steps):
  `.venv/bin/python google_client.py` lists events with no browser; then
  `docker compose restart` and confirm the log shows a clean connect.

## Workflow

Branch `feature/google-service-account-auth`. Never commit/push/merge to
master (manual, by the user). No GitHub issue (scoped out by the user).
