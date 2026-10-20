#!/usr/bin/env python3
"""Publish The Last Train Home carousel through Meta's Instagram API."""

import os
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parent
OWNER = "lovenishpurohit111"
REPOSITORY = "lost-and-found-gods-instagram"
BRANCH = "main"
CAROUSEL_DIRECTORY = "media/the-last-train-home"
API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v25.0")
API_BASE = f"https://graph.instagram.com/{API_VERSION}/"


def request_json(method: str, path: str, **kwargs) -> dict:
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
        raise RuntimeError(f"Meta API request failed{suffix}: {message}")
    return payload


def api_post(path: str, data: dict) -> dict:
    return request_json(requests.post, path, data=data)


def api_get(path: str, params: dict) -> dict:
    return request_json(requests.get, path, params=params)


def wait_until_ready(container_id: str, token: str, label: str) -> None:
    for _ in range(40):
        status = api_get(container_id, {"fields": "status_code,status", "access_token": token})
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"Meta failed to process {label}: {status.get('status', 'no detail returned')}")
        time.sleep(3)
    raise RuntimeError(f"Timed out waiting for Meta to process {label}.")


def main() -> int:
    instagram_user_id = os.getenv("INSTAGRAM_USER_ID", "").strip()
    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
    if not instagram_user_id or not access_token:
        raise RuntimeError("Required Instagram publishing secrets are not configured.")

    caption = (ROOT / "caption-last-train-home.txt").read_text(encoding="utf-8").strip()
    slides = sorted((ROOT / CAROUSEL_DIRECTORY).glob("slide_*.jpg"))
    if not 2 <= len(slides) <= 10:
        raise RuntimeError(f"Expected 2–10 carousel slides; found {len(slides)}.")

    child_ids = []
    for slide in slides:
        image_url = f"https://raw.githubusercontent.com/{OWNER}/{REPOSITORY}/{BRANCH}/{CAROUSEL_DIRECTORY}/{slide.name}"
        item = api_post(
            f"{instagram_user_id}/media",
            {"image_url": image_url, "is_carousel_item": "true", "access_token": access_token},
        )
        child_id = item.get("id")
        if not child_id:
            raise RuntimeError(f"Meta did not return a media container for {slide.name}.")
        child_ids.append(child_id)
        print(f"Created carousel item container for {slide.name}.")

    parent = api_post(
        f"{instagram_user_id}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": access_token,
        },
    )
    carousel_id = parent.get("id")
    if not carousel_id:
        raise RuntimeError("Meta did not return the carousel container ID.")
    print("Waiting for Meta to finish processing the carousel.")
    wait_until_ready(carousel_id, access_token, "the carousel")

    published = api_post(
        f"{instagram_user_id}/media_publish",
        {"creation_id": carousel_id, "access_token": access_token},
    )
    media_id = published.get("id")
    if not media_id:
        raise RuntimeError("The publish request returned no Instagram media ID.")
    print(f"Published carousel. Instagram media ID: {media_id}")
    try:
        result = api_get(media_id, {"fields": "permalink", "access_token": access_token})
        if result.get("permalink"):
            print(f"Post URL: {result['permalink']}")
    except RuntimeError as exc:
        print(f"Post published; permalink lookup was unavailable: {exc}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Publish failed: {exc}", file=sys.stderr)
        sys.exit(1)
