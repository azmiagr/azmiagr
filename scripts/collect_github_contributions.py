#!/usr/bin/env python3
"""Collect public GitHub contribution calendar data for a profile README."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "github-contributions.json"
DEFAULT_USER = "azmiagr"


def parse_total(text: str) -> int:
    match = re.search(r"([\d,]+)\s+contributions?", text)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def parse_count(cell: BeautifulSoup, tooltip_text: str = "") -> int:
    count_text = cell.get("data-count")
    if count_text and count_text.isdigit():
        return int(count_text)

    readable = " ".join(
        value
        for value in [
            cell.get("aria-label"),
            cell.get_text(" ", strip=True),
            tooltip_text,
        ]
        if value
    )
    match = re.search(r"([\d,]+)\s+contributions?", readable)
    if match:
        return int(match.group(1).replace(",", ""))
    return 0


def collect_public_contributions(username: str) -> dict:
    url = f"https://github.com/users/{username}/contributions"
    headers = {
        "Accept": "text/html",
        "User-Agent": "azmiagr-profile-insights/1.0",
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    days = []
    tooltips = {
        tooltip.get("for"): tooltip.get_text(" ", strip=True)
        for tooltip in soup.select("tool-tip[for]")
        if tooltip.get("for")
    }

    for cell in soup.select("[data-date][data-level]"):
        day = cell.get("data-date")
        level_text = cell.get("data-level") or "0"
        if not day:
            continue
        days.append(
            {
                "date": day,
                "count": parse_count(cell, tooltips.get(cell.get("id"), "")),
                "level": int(level_text),
            }
        )

    if not days:
        raise RuntimeError("No contribution days found in GitHub response.")

    days.sort(key=lambda item: item["date"])
    total_heading = soup.select_one("#js-contribution-activity-description")
    total = parse_total(total_heading.get_text(" ", strip=True)) if total_heading else sum(
        item["count"] for item in days
    )

    return {
        "username": username,
        "source": url,
        "range": {
            "from": days[0]["date"],
            "to": days[-1]["date"],
        },
        "total": total,
        "days": days,
    }


def write_json_atomically(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(encoded)
        temporary = Path(handle.name)

    temporary.replace(path)


def main() -> int:
    username = os.environ.get("GH_PROFILE_USER", DEFAULT_USER).strip() or DEFAULT_USER
    payload = collect_public_contributions(username)
    payload["updated_on"] = datetime.now(timezone.utc).date().isoformat()
    write_json_atomically(OUTPUT_PATH, payload)
    print(
        f"Saved {len(payload['days'])} days for {username} "
        f"({payload['range']['from']} to {payload['range']['to']})."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
