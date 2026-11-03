#!/usr/bin/env python3
"""Validate credentials or publish today's daily shloka card via Instagram API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parent
OWNER = "lovenishpurohit111"
REPOSITORY = "lost-and-found-gods-instagram"
BRANCH = "main"
API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v25.0")
API_BASE = f"https://graph.instagram.com/{API_VERSION}/"
USERNAME = "lost_and_found_gods"


def call_api(method, path: str, **kwargs) -> dict:
    response = method(urljoin(API_BASE, path), timeout=60, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if not response.ok or "error" in payload:
        error = payload.get("error", {})
        message = error.get("message", response.reason)
        code = error.get("code")
        suffix = f" (Meta error {code})" if code else ""
        raise RuntimeError(f"Instagram API request failed{suffix}: {message}")
    return payload


def api_get(path: str, params: dict) -> dict:
    return call_api(requests.get, path, params=params)


def api_post(path: str, data: dict) -> dict:
    return call_api(requests.post, path, data=data)


def credentials() -> tuple[str, str]:
    account_id = os.getenv("INSTAGRAM_USER_ID", "").strip()
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
    if not account_id or not token:
        raise RuntimeError("Instagram publishing secrets are missing from this repository's Actions settings.")
    return account_id, token


def preflight(account_id: str, token: str) -> None:
    account = api_get(account_id, {"fields": "id,username", "access_token": token})
    if str(account.get("id", "")) != account_id:
        raise RuntimeError("Instagram returned a different account ID than the configured account.")
    if account.get("username", "").lower() != USERNAME:
        raise RuntimeError("The configured Instagram token does not resolve to @lost_and_found_gods.")
    print(f"Instagram credential check passed for @{USERNAME}.")


def wait_until_ready(container_id: str, token: str) -> None:
    for _ in range(40):
        status = api_get(container_id, {"fields": "status_code,status", "access_token": token})
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"Instagram could not process the image: {status.get('status', 'no detail returned')}")
        time.sleep(3)
    raise RuntimeError("Timed out while Instagram processed the image.")


def publish(post_date: date, account_id: str, token: str) -> None:
    folder = ROOT / "media" / "daily-shlokas" / post_date.isoformat()
    image = folder / "shloka.jpg"
    caption_path = folder / "caption.txt"
    receipt_path = ROOT / "published" / f"{post_date.isoformat()}.json"
    if receipt_path.exists():
        print(f"A publication receipt already exists for {post_date}; skipping to avoid a duplicate.")
        return
    if not image.exists() or not caption_path.exists():
        raise RuntimeError(f"Daily card files are missing for {post_date}.")

    image_url = (
        f"https://raw.githubusercontent.com/{OWNER}/{REPOSITORY}/{BRANCH}/"
        f"media/daily-shlokas/{post_date.isoformat()}/shloka.jpg"
    )
    head = requests.head(image_url, allow_redirects=True, timeout=30)
    if head.status_code != 200:
        raise RuntimeError(f"The public image URL is not ready yet (HTTP {head.status_code}).")

    caption = caption_path.read_text(encoding="utf-8").strip()
    container = api_post(
        f"{account_id}/media",
        {"image_url": image_url, "caption": caption, "access_token": token},
    )
    container_id = container.get("id")
    if not container_id:
        raise RuntimeError("Instagram did not return a media container ID.")
    wait_until_ready(container_id, token)
    result = api_post(
        f"{account_id}/media_publish",
        {"creation_id": container_id, "access_token": token},
    )
    media_id = result.get("id")
    if not media_id:
        raise RuntimeError("The publish request returned no Instagram media ID.")
    permalink = ""
    try:
        permalink = api_get(media_id, {"fields": "permalink", "access_token": token}).get("permalink", "")
    except RuntimeError as exc:
        print(f"The post is published; permalink lookup failed: {exc}")

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(
            {"date": post_date.isoformat(), "media_id": media_id, "permalink": permalink},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Published the daily shloka for {post_date}.")
    if permalink:
        print(f"Post URL: {permalink}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="India-local post date, YYYY-MM-DD")
    parser.add_argument("--preflight", action="store_true", help="Verify account credentials without publishing")
    args = parser.parse_args()
    post_date = date.fromisoformat(args.date)
    account_id, token = credentials()
    preflight(account_id, token)
    if not args.preflight:
        publish(post_date, account_id, token)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Daily shloka publishing failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
