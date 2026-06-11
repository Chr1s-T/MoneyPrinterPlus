"""Pexels API client for searching and downloading video materials.

References:
  - Pexels API docs: https://www.pexels.com/api/documentation/
  - MoneyPrinterTurbo: app/services/material.py
"""

import hashlib
import os
import threading
from typing import List
from urllib.parse import urlencode

import requests


# ── Data class ──────────────────────────────────────────────────────


class MaterialInfo:
    """Represents a video material found on Pexels."""

    def __init__(self, provider: str, url: str, duration: int):
        self.provider = provider
        self.url = url
        self.duration = duration


# ── API key management ──────────────────────────────────────────────

_api_key_counter = 0
_api_key_lock = threading.Lock()


def get_api_key(api_keys: List[str]) -> str:
    """Round-robin through API keys."""
    if not api_keys:
        raise ValueError("No Pexels API keys configured")
    global _api_key_counter
    with _api_key_lock:
        _api_key_counter += 1
        return api_keys[_api_key_counter % len(api_keys)]


# ── Video resolution ────────────────────────────────────────────────


# 9:16 portrait resolutions (width × height)
PORTRAIT_RESOLUTIONS = [
    (1080, 1920),   # 1080P
    (720, 1280),    # 720P
    (576, 1024),    # SD
    (480, 854),     # 480P
]


def _best_resolution_for(w: int, h: int):
    """Find the closest supported portrait resolution for scaling."""
    # Pexels returns various sizes; we prefer the highest that matches
    for tw, th in PORTRAIT_RESOLUTIONS:
        if w >= tw and h >= th:
            return tw, th
    # Fallback: use whatever we got if it's at least 480p
    if w >= 480 and h >= 854:
        return w, h
    return None


# ── Search ──────────────────────────────────────────────────────────


def search_videos(
    search_term: str,
    api_key: str,
    minimum_duration: int = 5,
    per_page: int = 20,
    proxies: dict | None = None,
) -> List[MaterialInfo]:
    """Search Pexels for portrait (9:16) videos matching a keyword.

    Returns a list of MaterialInfo with the best matching resolution.
    """
    headers = {
        "Authorization": api_key,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        ),
    }
    params = {
        "query": search_term,
        "per_page": per_page,
        "orientation": "portrait",
    }
    query_url = f"https://api.pexels.com/videos/search?{urlencode(params)}"

    try:
        resp = requests.get(
            query_url,
            headers=headers,
            proxies=proxies,
            timeout=(30, 60),
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[pexels] search failed for '{search_term}': {e}")
        return []

    results: List[MaterialInfo] = []
    for video in data.get("videos", []):
        duration = video.get("duration", 0)
        if duration < minimum_duration:
            continue

        # Find the best quality video file matching 9:16 portrait
        best_item = None
        best_res = 0
        for vf in video.get("video_files", []):
            w = vf.get("width", 0) or 0
            h = vf.get("height", 0) or 0
            res = _best_resolution_for(w, h)
            if res is None:
                continue
            # Higher total pixels = better quality
            pixels = res[0] * res[1]
            if pixels > best_res:
                best_res = pixels
                best_item = MaterialInfo(
                    provider="pexels",
                    url=vf["link"],
                    duration=duration,
                )

        if best_item:
            results.append(best_item)

    return results


# ── Download ────────────────────────────────────────────────────────


def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _validate_video_file(filepath: str) -> bool:
    """Quick validation: file exists, non-empty, and is a valid MP4."""
    if not os.path.isfile(filepath) or os.path.getsize(filepath) == 0:
        return False
    # Simple header check for MP4
    with open(filepath, "rb") as f:
        header = f.read(12)
    # MP4 files start with ftyp box
    return header[4:8] == b"ftyp"


def download_video(
    video_url: str,
    save_dir: str,
    proxies: dict | None = None,
    timeout: int = 240,
) -> str | None:
    """Download a single video from Pexels, with caching.

    Args:
        video_url: The direct video file URL.
        save_dir: Directory to save to.
        proxies: Optional proxy config.

    Returns:
        Local file path, or None on failure.
    """
    os.makedirs(save_dir, exist_ok=True)

    # Cache: use MD5 of URL to avoid re-downloads
    url_hash = md5(video_url.split("?")[0])
    video_path = os.path.join(save_dir, f"vid-{url_hash}.mp4")

    # Check cache
    if _validate_video_file(video_path):
        return video_path

    # Download
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        ),
    }
    try:
        resp = requests.get(
            video_url,
            headers=headers,
            proxies=proxies,
            timeout=(60, timeout),
        )
        resp.raise_for_status()

        # Write to a temp file first, then atomically rename
        tmp_path = video_path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(resp.content)

        if not _validate_video_file(tmp_path):
            os.remove(tmp_path)
            print(f"[pexels] downloaded file is invalid: {video_url}")
            return None

        os.rename(tmp_path, video_path)
        return video_path

    except Exception as e:
        print(f"[pexels] download failed: {video_url[:80]}... => {e}")
        # Clean up temp file
        tmp = video_path + ".tmp"
        if os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        return None


def download_videos(
    search_terms: List[str],
    api_key: str,
    save_dir: str,
    max_clip_duration: int = 5,
    audio_duration: float | None = None,
    min_videos: int = 5,
    proxies: dict | None = None,
) -> List[str]:
    """Search and download portrait videos for multiple keywords.

    Args:
        search_terms: English keywords for Pexels search.
        api_key: Pexels API key.
        save_dir: Where to save downloaded videos.
        max_clip_duration: Minimum duration each clip must have.
        audio_duration: Target total duration in seconds. If None,
                        download at least `min_videos` clips.
        min_videos: Minimum number of clips to collect.
        proxies: Optional proxy config.

    Returns:
        List of local file paths to downloaded videos.
    """
    # Collect unique results from all search terms
    all_items: List[MaterialInfo] = []
    seen_urls: set = set()

    for term in search_terms:
        items = search_videos(
            search_term=term,
            api_key=api_key,
            minimum_duration=max_clip_duration,
            proxies=proxies,
        )
        print(f"[pexels] '{term}' → {len(items)} results")
        for item in items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                all_items.append(item)

    print(f"[pexels] total unique candidates: {len(all_items)}")

    # Download until we have enough
    downloaded: List[str] = []
    total_duration = 0.0

    for item in all_items:
        if audio_duration and total_duration >= audio_duration:
            break
        if len(downloaded) >= min_videos and not audio_duration:
            break

        path = download_video(item.url, save_dir, proxies=proxies)
        if path:
            downloaded.append(path)
            seconds = min(max_clip_duration, item.duration)
            total_duration += seconds
            print(f"[pexels] downloaded ({len(downloaded)}): {os.path.basename(path)} "
                  f"({seconds}s, total: {total_duration:.0f}s)")

    print(f"[pexels] done: {len(downloaded)} videos downloaded to {save_dir}")
    return downloaded
