#!/usr/bin/env python3
"""Render one source-cited daily shloka card for Instagram."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "daily_shlokas.json"
OUT = ROOT / "media" / "daily-shlokas"
START_DATE = date.fromisoformat(os.getenv("SHLOKA_START_DATE", "2026-11-04"))
WIDTH, HEIGHT = 1080, 1350
BG = (247, 242, 230)
INK = (46, 38, 31)
MUTED = (111, 94, 78)
SAFFRON = (188, 91, 39)
HAIRLINE = (210, 193, 169)
SERIF = ROOT / "assets" / "fonts" / "NotoSerif.ttf"
DEVANAGARI = ROOT / "assets" / "fonts" / "NotoSerifDevanagari.ttf"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, use_font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=use_font)[2] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def wrap_sanskrit(draw: ImageDraw.ImageDraw, text: str, use_font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    halves = [part.strip() for part in re.split(r"([।॥])", text) if part.strip()]
    # Keep danda punctuation with the preceding half-verse.
    lines: list[str] = []
    for part in halves:
        if part in {"।", "॥"} and lines:
            lines[-1] += part
            continue
        if draw.textbbox((0, 0), part, font=use_font)[2] <= width:
            lines.append(part)
            continue
        # Split only on word boundaries where the source has them.
        lines.extend(wrap_text(draw, part, use_font, width))
    return lines


def draw_centered_lines(draw, lines, use_font, y, fill, line_gap=15, stroke_width=0, stroke_fill=None):
    for line in lines:
        draw.text(
            (WIDTH // 2, y), line, font=use_font, fill=fill, anchor="mt",
            stroke_width=stroke_width, stroke_fill=stroke_fill,
        )
        box = draw.textbbox((WIDTH // 2, y), line, font=use_font, anchor="mt", stroke_width=stroke_width)
        y = box[3] + line_gap
    return y


def make_card(entry: dict, sequence_number: int, post_date: date) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    # Quiet hand-inked frame and a faint circular motif keep the card warm, not ornate.
    draw.rounded_rectangle((36, 36, WIDTH - 36, HEIGHT - 36), radius=26, outline=HAIRLINE, width=2)
    draw.ellipse((WIDTH - 340, 32, WIDTH + 100, 470), outline=(235, 225, 208), width=3)
    draw.ellipse((WIDTH - 285, 88, WIDTH + 42, 415), outline=(239, 230, 216), width=2)
    draw.ellipse((-190, HEIGHT - 310, 230, HEIGHT + 110), outline=(235, 225, 208), width=3)
    draw.line((92, 124, 205, 124), fill=SAFFRON, width=5)

    small = font(SERIF, 28)
    label = font(SERIF, 33)
    title = font(SERIF, 58)
    sanskrit_font = font(DEVANAGARI, 55)
    iast_font = font(SERIF, 27)
    meaning_font = font(SERIF, 37)
    foot = font(SERIF, 24)

    draw.text((92, 82), "DAILY SHLOKA", font=small, fill=SAFFRON)
    draw.text((WIDTH - 92, 83), f"{post_date:%d %b %Y}", font=small, fill=MUTED, anchor="rt")

    verse_lines = wrap_sanskrit(draw, entry["verse"], sanskrit_font, 850)
    while max(draw.textbbox((0, 0), line, font=sanskrit_font)[2] for line in verse_lines) > 850 and sanskrit_font.size > 43:
        sanskrit_font = font(DEVANAGARI, sanskrit_font.size - 2)
        verse_lines = wrap_sanskrit(draw, entry["verse"], sanskrit_font, 850)
    y = 184
    y = draw_centered_lines(draw, verse_lines, sanskrit_font, y, INK, line_gap=15)

    iast_lines = wrap_text(draw, entry["iast"], iast_font, 870)
    y += 13
    y = draw_centered_lines(draw, iast_lines, iast_font, y, MUTED, line_gap=8)
    y += 15
    draw.line((188, y, WIDTH - 188, y), fill=HAIRLINE, width=2)
    y += 34

    draw.text((WIDTH // 2, y), "MEANING · PLAIN LANGUAGE", font=label, fill=SAFFRON, anchor="mt")
    y += 60
    meaning_lines = wrap_text(draw, entry["meaning"], meaning_font, 850)
    y = draw_centered_lines(draw, meaning_lines, meaning_font, y, INK, line_gap=13)
    y += 20
    draw.line((188, y, WIDTH - 188, y), fill=HAIRLINE, width=2)
    y += 26

    reflect_label = font(SERIF, 23)
    reflection_font = font(SERIF, 29)
    draw.text((WIDTH // 2, y), "A THOUGHT TO CARRY", font=reflect_label, fill=SAFFRON, anchor="mt")
    y += 43
    reflection_lines = wrap_text(draw, entry["reflection"], reflection_font, 850)
    y = draw_centered_lines(draw, reflection_lines, reflection_font, y, INK, line_gap=8)
    if y > HEIGHT - 170:
        raise ValueError(f"Text layout is too tall for Gita {entry['ref']} (content ends at y={y}).")

    source = f"MAHABHARATA  ·  BHISHMA PARVA  ·  BHAGAVAD GITA {entry['ref']}"
    draw.text((WIDTH // 2, HEIGHT - 104), source, font=foot, fill=MUTED, anchor="mt")
    draw.text((WIDTH // 2, HEIGHT - 68), "Plain-language paraphrase · Verse source linked in caption", font=foot, fill=MUTED, anchor="mt")

    folder = OUT / post_date.isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "shloka.jpg"
    image.save(output, quality=94, subsampling=0, optimize=True)
    caption = (
        f"A verse to carry with you today.\n\n{entry['meaning']}\n\n"
        f"{entry['book']} {entry['ref']}\n"
        "Source text: Heritage, IIT Kanpur's Gita Supersite.\n\n"
        "Meaning is a plain-language paraphrase.\n\n"
        "#DailyShloka #BhagavadGita #Mahabharata #Sanskrit #Wisdom"
    )
    (folder / "caption.txt").write_text(caption + "\n", encoding="utf-8")
    (folder / "sequence.json").write_text(
        json.dumps({"date": post_date.isoformat(), "sequence": sequence_number, "verse": entry["ref"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Rendered sequence {sequence_number}/{len(json.loads(DATA.read_text(encoding='utf-8')))}: Gita {entry['ref']} -> {output}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="India-local post date, YYYY-MM-DD")
    parser.add_argument("--preview-first", action="store_true", help="Use the first verse when previewing before the queue start")
    args = parser.parse_args()

    today = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo("Asia/Kolkata")).date()
    entries = json.loads(DATA.read_text(encoding="utf-8"))
    offset = (today - START_DATE).days
    if offset < 0 and args.preview_first:
        offset = 0
    if offset < 0:
        raise SystemExit(f"The series starts {START_DATE.isoformat()}; refusing to publish an earlier date.")
    if offset >= len(entries):
        raise SystemExit(f"The {len(entries)}-verse queue is finished; add and verify more entries before publishing again.")
    make_card(entries[offset], offset + 1, today)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
