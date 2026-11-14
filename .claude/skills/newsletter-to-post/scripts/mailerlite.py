#!/usr/bin/env python3
"""Restricted MailerLite API client.

The API key is unscoped (it can modify subscribers and campaigns), so this
module enforces restricted use in code. It sends only:
  - GET requests to the campaign paths in READ_ONLY_PATHS, and
  - one write: POST /api/campaigns, which creates a *draft* campaign.
Creating a campaign never sends it; sending needs /api/campaigns/<id>/schedule,
which this module refuses. Do not add other methods or paths without the
user's explicit agreement.

The key is read from the macOS Keychain item "mailerlite-api" and is never
printed, logged or written anywhere.
"""
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://connect.mailerlite.com"
KEYCHAIN_SERVICE = "mailerlite-api"
READ_ONLY_PATHS = [
    re.compile(r"^/api/campaigns$"),          # list campaigns
    re.compile(r"^/api/campaigns/\d+$"),      # get one campaign
]


DRAFT_CREATE_PATH = "/api/campaigns"


def _api_key():
    result = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"ERROR: couldn't read Keychain item '{KEYCHAIN_SERVICE}' (exit {result.returncode})")
    return result.stdout.strip()


def get(path, params=None):
    """GET a read-only campaign endpoint and return parsed JSON."""
    if not any(p.match(path) for p in READ_ONLY_PATHS):
        sys.exit(f"ERROR: refusing to call {path}: not on the read-only allowlist")
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, method="GET", headers={
        "Authorization": "Bearer " + _api_key(),
        "Accept": "application/json",
        "User-Agent": "automatedaf-newsletter-to-post",
    })
    assert req.get_method() == "GET"
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: GET {path} returned HTTP {e.code}: {e.read()[:300].decode(errors='replace')}")


def create_draft_campaign(payload):
    """POST /api/campaigns to create a draft campaign, and return parsed JSON.

    This is the module's only write. It never schedules or sends."""
    if set(payload) - {"name", "type", "emails", "groups", "segments", "settings", "language_id"}:
        sys.exit("ERROR: refusing to create a campaign with unexpected fields")
    if payload.get("type") != "regular" or "delivery" in payload or "schedule" in payload:
        sys.exit("ERROR: refusing: only plain regular draft campaigns may be created")
    req = urllib.request.Request(BASE + DRAFT_CREATE_PATH, method="POST",
                                 data=json.dumps(payload).encode(), headers={
        "Authorization": "Bearer " + _api_key(),
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "automatedaf-post-to-newsletter",
    })
    assert req.get_method() == "POST" and req.full_url == BASE + "/api/campaigns"
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: POST {DRAFT_CREATE_PATH} returned HTTP {e.code}: {e.read()[:600].decode(errors='replace')}")
