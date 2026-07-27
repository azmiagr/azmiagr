#!/usr/bin/env python3
"""Collect public repository language data for a profile README."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "github-languages.json"
DEFAULT_USER = "azmiagr"
API_ROOT = "https://api.github.com"


def github_headers() -> dict[str, str]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "azmiagr-profile-insights/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_json(session: requests.Session, url: str) -> tuple[object, requests.Response]:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json(), response


def collect_repositories(session: requests.Session, username: str) -> list[dict]:
    repositories = []
    page = 1

    while True:
        url = (
            f"{API_ROOT}/users/{username}/repos"
            f"?type=owner&sort=updated&direction=desc&per_page=100&page={page}"
        )
        payload, response = get_json(session, url)
        if not isinstance(payload, list):
            raise RuntimeError("Unexpected repository response from GitHub API.")

        repositories.extend(
            repo
            for repo in payload
            if not repo.get("fork") and not repo.get("archived")
        )

        if 'rel="next"' not in response.headers.get("Link", ""):
            break
        page += 1

    return repositories


def collect_languages(username: str) -> dict:
    session = requests.Session()
    session.headers.update(github_headers())

    repositories = collect_repositories(session, username)
    languages: dict[str, dict[str, int]] = {}

    for repo in repositories:
        repo_name = repo["name"]
        payload, _ = get_json(session, f"{API_ROOT}/repos/{username}/{repo_name}/languages")
        if not isinstance(payload, dict):
            continue

        for language, byte_count in payload.items():
            item = languages.setdefault(language, {"bytes": 0, "repos": 0})
            item["bytes"] += int(byte_count)
            item["repos"] += 1

    total_bytes = sum(item["bytes"] for item in languages.values())
    ranked = sorted(
        (
            {
                "name": name,
                "bytes": item["bytes"],
                "repos": item["repos"],
                "percentage": round((item["bytes"] / total_bytes * 100), 2)
                if total_bytes
                else 0,
            }
            for name, item in languages.items()
        ),
        key=lambda item: item["bytes"],
        reverse=True,
    )

    return {
        "username": username,
        "source": f"{API_ROOT}/users/{username}/repos",
        "repository_count": len(repositories),
        "total_bytes": total_bytes,
        "languages": ranked,
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
    payload = collect_languages(username)
    payload["updated_on"] = datetime.now(timezone.utc).date().isoformat()
    write_json_atomically(OUTPUT_PATH, payload)
    print(
        f"Saved {len(payload['languages'])} languages across "
        f"{payload['repository_count']} repositories for {username}."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
