#!/usr/bin/env python3
"""Render a compact GitHub language summary SVG."""

from __future__ import annotations

import html
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "github-languages.json"
OUTPUT_PATH = ROOT / "assets" / "github-language-summary.svg"

TEXT = "#f0f6fc"
MUTED = "#8b949e"
PANEL = "#0d1117"
BORDER = "#30363d"
TRACK = "#161b22"
COLORS = [
    "#00add8",
    "#f05138",
    "#7f52ff",
    "#777bb4",
    "#41b883",
    "#58a6ff",
]


def bar_rows(languages: list[dict]) -> str:
    rows = []
    max_bytes = max((item["bytes"] for item in languages), default=1)
    start_y = 88
    bar_width = 360

    for index, item in enumerate(languages[:6]):
        y = start_y + index * 25
        color = COLORS[index % len(COLORS)]
        width = max(4, round(item["bytes"] / max_bytes * bar_width))
        label = html.escape(item["name"])
        percentage = f"{item['percentage']:.1f}%"
        rows.append(
            f'<text x="24" y="{y}" fill="{TEXT}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12" font-weight="600">{label}</text>'
        )
        rows.append(
            f'<rect x="176" y="{y - 10}" width="{bar_width}" height="9" rx="4.5" fill="{TRACK}"/>'
        )
        rows.append(
            f'<rect x="176" y="{y - 10}" width="{width}" height="9" rx="4.5" fill="{color}"/>'
        )
        rows.append(
            f'<text x="564" y="{y}" fill="{MUTED}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11">{percentage}</text>'
        )

    return "\n  ".join(rows)


def render(payload: dict) -> str:
    username = payload["username"]
    languages = payload["languages"]
    top = languages[0]["name"] if languages else "No language data"
    top_percentage = f"{languages[0]['percentage']:.1f}%" if languages else "0.0%"

    width = 760
    height = 245

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">{html.escape(username)} GitHub Language Summary</title>
  <desc id="desc">A local summary of top repository languages by byte count.</desc>
  <rect width="{width}" height="{height}" rx="14" fill="{PANEL}"/>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="13.5" stroke="{BORDER}"/>

  <text x="24" y="38" fill="{TEXT}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="20" font-weight="700">Language Summary</text>

  <text x="564" y="34" fill="#58a6ff" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="22" font-weight="700">{html.escape(top)}</text>
  <text x="564" y="55" fill="{MUTED}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11">top language ({top_percentage})</text>

  {bar_rows(languages)}
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
