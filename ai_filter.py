"""AI-powered event filtering using NEAR AI API."""

import hashlib
import json
import logging
import os
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)


class AIFilter:
    """Filter calendar events using NEAR AI."""

    def __init__(self):
        self.api_key = config.NEAR_AI_API_KEY
        self.api_url = config.NEAR_AI_API_URL
        self.model = config.NEAR_AI_MODEL
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """Load AI decision cache from file."""
        if os.path.exists(config.AI_DECISION_CACHE_FILE):
            try:
                with open(config.AI_DECISION_CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load AI cache: {e}")
        return {}

    def _save_cache(self):
        """Save AI decision cache to file."""
        try:
            with open(config.AI_DECISION_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save AI cache: {e}")

    def _get_event_hash(self, event: dict) -> str:
        """Generate hash for event to use as cache key."""
        key_data = {
            "title": event.get("title", ""),
            "organizer": event.get("organizer", ""),
            "body": event.get("body", "")[:500],
            "categories": event.get("categories", []),
            "is_all_day": event.get("is_all_day", False),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def should_sync(self, event: dict) -> tuple[bool, str]:
        """Determine if an event should be synced using AI.

        Returns:
            tuple of (should_sync: bool, reason: str)
        """
        event_hash = self._get_event_hash(event)

        # Check cache first
        if event_hash in self.cache:
            cached = self.cache[event_hash]
            logger.debug(f"Using cached decision for '{event['title']}': {cached['sync']}")
            return cached["sync"], cached["reason"] + " (cached)"

        # Build prompt with event details
        prompt = config.AI_FILTER_PROMPT.format(
            title=event.get("title", "(ingen tittel)"),
            start=event.get("start", ""),
            end=event.get("end", ""),
            organizer=event.get("organizer", "ukjent"),
            body=event.get("body", "(ingen beskrivelse)")[:1000],
            categories=", ".join(event.get("categories", [])) or "(ingen)",
            is_all_day="Ja" if event.get("is_all_day") else "Nei",
            status=event.get("status", "busy"),
        )

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                },
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            response_text = result["choices"][0]["message"]["content"].strip()
            logger.debug(f"AI response for '{event['title']}': {response_text}")

            # Parse JSON response
            parsed = self._parse_response(response_text)
            should_sync = parsed.get("sync", False)
            reason = parsed.get("reason", "Ingen forklaring gitt")

            # Cache the decision
            self.cache[event_hash] = {"sync": should_sync, "reason": reason}
            self._save_cache()

            logger.info(f"AI decision for '{event['title']}': sync={should_sync} - {reason}")
            return should_sync, reason

        except requests.RequestException as e:
            logger.error(f"NEAR AI API error: {e}")
            return True, f"API-feil, synkroniserer for sikkerhets skyld: {e}"

    def _parse_response(self, response_text: str) -> dict:
        """Parse the AI response JSON."""
        try:
            if "{" in response_text:
                start = response_text.index("{")
                end = response_text.rindex("}") + 1
                json_str = response_text[start:end]
                return json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse AI response: {response_text}, error: {e}")

        return {"sync": True, "reason": "Kunne ikke tolke AI-svar, synkroniserer for sikkerhets skyld"}

    def filter_events(self, events: list[dict]) -> list[tuple[dict, str]]:
        """Filter a list of events, returning those that should be synced.

        Returns:
            List of tuples: (event, reason)
        """
        results = []
        sync_count = 0
        skip_count = 0

        for event in events:
            # Check filter mode
            if config.FILTER_MODE == "non_recurring":
                should_sync, reason = self._filter_non_recurring(event)
            else:
                should_sync, reason = self.should_sync(event)

            if should_sync:
                results.append((event, reason))
                sync_count += 1
            else:
                skip_count += 1
                logger.info(f"Skipping '{event['title']}': {reason}")

        mode_name = "non-recurring filter" if config.FILTER_MODE == "non_recurring" else "AI filtering"
        logger.info(f"{mode_name} complete: {sync_count} to sync, {skip_count} skipped")
        return results

    def _filter_non_recurring(self, event: dict) -> tuple[bool, str]:
        """Simple filter: sync all non-recurring, single-day events."""
        if event.get("is_recurring", False):
            return False, "Gjentakende møte"

        # Check if multi-day event
        start = event.get("start", "")[:10]  # Get date part YYYY-MM-DD
        end = event.get("end", "")[:10]
        if start and end and start != end:
            return False, "Flerdagers hendelse"

        return True, "Ikke-gjentakende møte"

    def clear_cache(self):
        """Clear the AI decision cache."""
        self.cache = {}
        if os.path.exists(config.AI_DECISION_CACHE_FILE):
            os.remove(config.AI_DECISION_CACHE_FILE)
        logger.info("AI decision cache cleared")


def main():
    """Test the AI filter."""
    logging.basicConfig(level=logging.INFO)

    test_events = [
        {
            "title": "Weekly Team Standup",
            "start": "2024-01-15T09:00:00",
            "end": "2024-01-15T09:30:00",
            "organizer": "Team Lead",
            "body": "Weekly sync for the development team",
            "categories": ["Team"],
            "is_all_day": False,
            "status": "busy",
        },
        {
            "title": "Customer Demo - Acme Corp",
            "start": "2024-01-16T14:00:00",
            "end": "2024-01-16T15:00:00",
            "organizer": "Sales Manager",
            "body": "Product demo for potential new customer",
            "categories": ["Customer", "Sales"],
            "is_all_day": False,
            "status": "busy",
        },
    ]

    ai_filter = AIFilter()

    print("\nTesting AI filter:\n")
    for event in test_events:
        should_sync, reason = ai_filter.should_sync(event)
        status = "SYNC" if should_sync else "SKIP"
        print(f"[{status}] {event['title']}")
        print(f"        Reason: {reason}\n")


if __name__ == "__main__":
    main()
