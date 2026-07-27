#!/usr/bin/env python3
"""Render a compact GitHub contribution map SVG."""

from __future__ import annotations

import html
import json
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "github-contributions.json"
OUTPUT_PATH = ROOT / "assets" / "github-contribution-map.svg"

COLORS = {
    0: "#161b22",
    1: "#0e4429",
    2: "#006d32",
    3: "#26a641",
    4: "#39d353",
}
TEXT = "#f0f6fc"
MUTED = "#8b949e"
ACCENT = "#58a6ff"
PANEL = "#0d1117"
BORDER = "#30363d"


def parse_day(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_number(value: int) -> str:
    return f"{value:,}"


def format_display_date(value: date) -> str:
    return f"{value.strftime('%b')} {value.day}, {value.year}"


def streaks(days: list[dict]) -> tuple[int, int, str, str]:
    current = 0
    longest = 0
    longest_start = ""
    longest_end = ""
    running = 0
    running_start = ""

    for item in days:
        if item["count"] > 0:
            if running == 0:
                running_start = item["date"]
            running += 1
            if running > longest:
                longest = running
                longest_start = running_start
                longest_end = item["date"]
        else:
            running = 0
            running_start = ""

    for item in reversed(days):
        if item["count"] > 0:
            current += 1
        else:
            break

    return current, longest, longest_start, longest_end


def month_labels(start: date, end: date) -> list[tuple[int, str]]:
    labels = []
    cursor = date(start.year, start.month, 1)
    if cursor < start:
        cursor = date(start.year + (start.month // 12), (start.month % 12) + 1, 1)

    while cursor <= end:
        week = (cursor - start).days // 7
        labels.append((week, cursor.strftime("%b")))
        cursor = date(cursor.year + (cursor.month // 12), (cursor.month % 12) + 1, 1)

    return labels


def rects(days: list[dict], start: date) -> str:
    size = 10
    gap = 3
    top = 116
    left = 24
    output = []

    for item in days:
        current = parse_day(item["date"])
        offset = (current - start).days
        week = offset // 7
        weekday = current.isoweekday() % 7
        x = left + (week * (size + gap))
        y = top + (weekday * (size + gap))
        color = COLORS.get(item["level"], COLORS[0])
        title = f"{item['date']}: {item['count']} contributions"
        output.append(
            f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2" '
            f'fill="{color}"><title>{html.escape(title)}</title></rect>'
        )

    return "\n".join(output)


def render(payload: dict) -> str:
    username = payload["username"]
    days = payload["days"]
    start = parse_day(days[0]["date"])
    end = parse_day(days[-1]["date"])
    current, longest, longest_start, longest_end = streaks(days)
    active_days = sum(1 for item in days if item["count"] > 0)
    total = int(payload["total"])

    width = 760
    height = 265
    labels = "\n".join(
        f'<text x="{24 + week * 13}" y="105" fill="{MUTED}" font-size="10">{label}</text>'
        for week, label in month_labels(start, end)
    )
    cells = rects(days, start)

    date_range = f"{format_display_date(start)} - {format_display_date(end)}"
    longest_range = (
        f"{format_display_date(parse_day(longest_start))} - {format_display_date(parse_day(longest_end))}"
        if longest_start and longest_end
        else "No active streak yet"
    )

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">{html.escape(username)} GitHub Contribution Map</title>
  <desc id="desc">A compact contribution calendar with total contributions, active days, current streak, and longest streak.</desc>
  <rect width="{width}" height="{height}" rx="14" fill="{PANEL}"/>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="13.5" stroke="{BORDER}"/>

  <text x="24" y="38" fill="{TEXT}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="20" font-weight="700">Contribution Map</text>
  <text x="24" y="61" fill="{MUTED}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12">{html.escape(date_range)}</text>

  <text x="320" y="34" fill="{ACCENT}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="22" font-weight="700">{format_number(total)}</text>
  <text x="320" y="55" fill="{MUTED}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11">contributions</text>

  <text x="450" y="34" fill="{ACCENT}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="22" font-weight="700">{active_days}</text>
  <text x="450" y="55" fill="{MUTED}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11">active days</text>

  <text x="560" y="34" fill="{ACCENT}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="22" font-weight="700">{current}</text>
  <text x="560" y="55" fill="{MUTED}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11">current streak</text>

  <text x="655" y="34" fill="{ACCENT}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="22" font-weight="700">{longest}</text>
  <text x="655" y="55" fill="{MUTED}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11">best streak</text>

  {labels}
  {cells}

  <text x="24" y="236" fill="{MUTED}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11">Longest streak: {html.escape(longest_range)}</text>
  <text x="605" y="236" fill="{MUTED}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="10">Less</text>
  <rect x="635" y="226" width="10" height="10" rx="2" fill="{COLORS[0]}"/>
  <rect x="650" y="226" width="10" height="10" rx="2" fill="{COLORS[1]}"/>
  <rect x="665" y="226" width="10" height="10" rx="2" fill="{COLORS[2]}"/>
  <rect x="680" y="226" width="10" height="10" rx="2" fill="{COLORS[3]}"/>
  <rect x="695" y="226" width="10" height="10" rx="2" fill="{COLORS[4]}"/>
  <text x="712" y="236" fill="{MUTED}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="10">More</text>
</svg>
"""


def write_svg_atomically(path: Path, svg: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(svg)
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else INPUT_PATH
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else OUTPUT_PATH

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    write_svg_atomically(output_path, render(payload))
    print(f"Rendered {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
