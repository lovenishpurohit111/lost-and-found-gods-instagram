#!/usr/bin/env python3
"""Render one source-cited daily shloka card for Instagram."""

from __future__ import annotations

import argparse
import json
import os
import re
import requests
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "daily_shlokas.json"
CORPUS = ROOT / "gita_verses.json"
OUT = ROOT / "media" / "daily-shlokas"
START_DATE = date.fromisoformat(os.getenv("SHLOKA_START_DATE", "2026-11-04"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_API = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
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
    text_source = entry.get("text_source", "Heritage, IIT Kanpur's Gita Supersite")
    caption = (
        f"A verse to carry with you today.\n\n{entry['meaning']}\n\n"
        f"{entry['book']} {entry['ref']}\n"
        f"{text_source}\n"
        f"Reference: {entry['source_url']}\n\n"
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


def generate_interpretation(source_verse: dict) -> dict:
    """Ask Gemini for a concise paraphrase; Sanskrit and verse reference stay source-controlled."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("The Gemini Actions secret is missing; refusing to invent or repeat a verse.")

    prompt = (
        "Write a careful, plain-language explanation for this Bhagavad Gita verse. "
        "Use only the supplied Sanskrit and transliteration; do not invent context or claim a single "
        "sectarian interpretation is universal. Meaning: one or two short sentences accurately paraphrasing "
        "the verse, not a quotation or life-coaching slogan. Reflection: one grounded, gentle sentence that "
        "connects the verse to everyday life without preaching. Do not include the verse, reference, hashtags, "
        "or introductory wording. If you cannot confidently interpret the Sanskrit, set confidence to low.\n\n"
        f"Reference: Bhagavad Gita {source_verse['ref']}\n"
        f"Sanskrit: {source_verse['verse']}\n"
        f"IAST: {source_verse['iast']}"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": "You are a careful editor of devotional educational content. Accuracy and humility matter more than eloquence."}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 250,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "meaning": {"type": "STRING"},
                    "reflection": {"type": "STRING"},
                    "confidence": {"type": "STRING", "enum": ["high", "medium", "low"]},
                },
                "required": ["meaning", "reflection", "confidence"],
            },
        },
    }
    response = requests.post(
        GEMINI_API,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    if not response.ok:
        # Do not print request headers or key values; only return provider status and sanitized detail.
        try:
            error = response.json().get("error", {})
            message = re.sub(r"https?://\S+", "[link]", str(error.get("message", "")))
        except ValueError:
            message = ""
        raise RuntimeError(f"Gemini generation failed (HTTP {response.status_code}): {message or 'no detail returned'}")

    try:
        parts = response.json()["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts).strip()
        result = json.loads(text)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError("Gemini returned no valid structured interpretation; no post was prepared.") from exc

    meaning = " ".join(str(result.get("meaning", "")).split())
    reflection = " ".join(str(result.get("reflection", "")).split())
    confidence = result.get("confidence")
    if confidence not in {"high", "medium"}:
        raise RuntimeError(f"Gemini marked Bhagavad Gita {source_verse['ref']} as uncertain; no post was prepared.")
    if not meaning or len(meaning) > 300 or len(meaning.split()) > 42:
        raise RuntimeError("Gemini's meaning was empty or too long; no post was prepared.")
    if not reflection or len(reflection) > 180 or len(reflection.split()) > 24:
        raise RuntimeError("Gemini's reflection was empty or too long; no post was prepared.")
    if "http://" in meaning.lower() or "https://" in meaning.lower() or "#" in meaning:
        raise RuntimeError("Gemini added a link or hashtag to the meaning; no post was prepared.")
    return {"meaning": meaning, "reflection": reflection}


def ensure_queue_entry(entries: list[dict], sequence_index: int) -> None:
    """Extend the cached queue up to the requested day using source-controlled verses."""
    if sequence_index < len(entries):
        return
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    used = {entry["ref"] for entry in entries}
    candidates = [verse for verse in corpus if verse["ref"] not in used]
    while sequence_index >= len(entries):
        if not candidates:
            raise SystemExit("All 700 Bhagavad Gita verses are already queued; add another verified source before continuing.")
        source_verse = candidates.pop(0)
        interpretation = generate_interpretation(source_verse)
        chapter, verse_number = source_verse["ref"].split(".")
        entry = {
            **source_verse,
            **interpretation,
            "source_url": (
                "https://www.gitasupersite.iitk.ac.in/srimad?"
                f"field_chapter_value={chapter}&field_nsutra_value={verse_number}&language=dv"
            ),
            "book": "Mahabharata · Bhishma Parva · Bhagavad Gita",
            "text_source": "Sanskrit and IAST: gita/gita open corpus (Unlicense), pinned source revision c6fce39595445768876ddbb8d1268a9c935e1d2b.",
            "interpretation_model": GEMINI_MODEL,
        }
        entries.append(entry)
        temp_path = DATA.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp_path.replace(DATA)
        print(f"Added source-controlled Bhagavad Gita {source_verse['ref']} interpretation to the local queue.")


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
    ensure_queue_entry(entries, offset)
    make_card(entries[offset], offset + 1, today)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
