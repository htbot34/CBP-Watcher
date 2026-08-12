#!/usr/bin/env python3
"""
Global Entry appointment watcher.

Polls the CBP TTP scheduler API for interview openings at the enrollment
centers you list, and pushes a phone notification via ntfy.sh the moment
one appears.

SETUP
1. Edit LOCATIONS with the city names you're willing to travel to.
2. Email alerts: set the SMTP_USER / SMTP_PASS / EMAIL_TO environment
   variables (see README). SMTP_USER/PASS is a Gmail address + App
   Password, used to send the alert to EMAIL_TO.
3. (Optional, free, zero-setup bonus) Push alerts via ntfy.sh: set
   NTFY_TOPIC below to something random/unguessable — anyone who knows
   your topic name can see your alerts. Leave it blank to skip this.
4. Run it:
     - Locally, left running:      python global_entry_watcher.py
     - Locally, one check + exit:  python global_entry_watcher.py --once
     - In the cloud (no computer needed): see the included GitHub Actions
       workflow, ge_watcher.yml.
"""

import json
import os
import smtplib
import sys
import time
import urllib.request
from email.mime.text import MIMEText

# ---- CONFIG ----
LOCATIONS = ["Boise"]  # add more, e.g. ["Boise", "Salt Lake City", "Spokane"]
CHECK_INTERVAL_MINUTES = 15  # only used when left running locally
STATE_FILE = "ge_watcher_state.json"

# Email (primary alert channel) — read from environment, never hardcoded.
SMTP_USER = os.environ.get("SMTP_USER")  # the Gmail address that sends the alert
SMTP_PASS = os.environ.get("SMTP_PASS")  # a Gmail App Password, not your login password
EMAIL_TO = os.environ.get("EMAIL_TO", "henrylachtur@gmail.com")

# Optional bonus push channel — leave blank to disable.
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")

# The full enrollment-center directory. Note: do NOT use /slots/asLocations here —
# it only returns centers that currently have open slots, so a center with no
# availability drops out of the list entirely and can never be resolved.
LOCATIONS_URL = (
    "https://ttp.cbp.dhs.gov/schedulerapi/locations/"
    "?temporary=false&inviteOnly=false&operational=true&serviceName=Global%20Entry"
)
SLOTS_URL = (
    "https://ttp.cbp.dhs.gov/schedulerapi/slots"
    "?orderBy=soonest&limit=1&locationId={}&minimum=1"
)


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def resolve_location_ids(city_names):
    """Match your city names against CBP's live location list."""
    all_locations = fetch_json(LOCATIONS_URL)
    print(f"Fetched {len(all_locations)} enrollment centers from CBP.")
    resolved = {}
    for city in city_names:
        for loc in all_locations:
            # Fields can come back null, so coerce before comparing.
            name = loc.get("name") or ""
            loc_city = loc.get("city") or ""
            loc_state = loc.get("state") or "?"
            if city.lower() in name.lower() or city.lower() in loc_city.lower():
                resolved[loc["id"]] = f"{name} ({loc_city}, {loc_state})"
    print(f"Matched {len(resolved)} center(s) for {city_names}: {sorted(resolved.values())}")
    return resolved


def check_slot(location_id):
    try:
        data = fetch_json(SLOTS_URL.format(location_id))
    except Exception as e:
        print(f"  error checking {location_id}: {e}")
        return None
    return data[0] if data else None


def send_ntfy(title, message):
    if not NTFY_TOPIC:
        return
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    req = urllib.request.Request(
        url,
        data=message.encode(),
        method="POST",
        headers={"Title": title, "Priority": "urgent", "Tags": "rotating_light"},
    )
    urllib.request.urlopen(req, timeout=10)


def send_email(title, message):
    if not (SMTP_USER and SMTP_PASS):
        print("  (SMTP_USER/SMTP_PASS not set — skipping email)")
        return
    msg = MIMEText(message)
    msg["Subject"] = title
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def notify(title, message):
    send_email(title, message)
    send_ntfy(title, message)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def run_once():
    locations = resolve_location_ids(LOCATIONS)
    if not locations:
        print("No matching locations found — check your LOCATIONS list.")
        return

    state = load_state()
    for loc_id, name in locations.items():
        slot = check_slot(loc_id)
        key = str(loc_id)
        if slot:
            if state.get(key) != slot["startTimestamp"]:
                msg = f'{name}: {slot["startTimestamp"]}'
                print("OPENING FOUND:", msg)
                notify("Global Entry slot open!", msg)
                state[key] = slot["startTimestamp"]
            else:
                print(f"{name}: still open, already alerted.")
        else:
            print(f"{name}: nothing available.")
            state.pop(key, None)
    save_state(state)


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_once()
    else:
        while True:
            run_once()
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
