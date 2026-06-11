"""BGM library management — scan, categorize, download background music.

Sources:
  - Local MP3 files from a library directory
  - Pixabay Music API (free, royalty-free): https://pixabay.com/api/music/
"""

import glob
import os
import random
from typing import Dict, List, Optional

import requests

# ── Pixabay Music API ──────────────────────────────────────────────

PIXABAY_MUSIC_URL = "https://pixabay.com/api/music/"

# Mood-to-tag mapping: what Pixabay tags map to each mood
MOOD_TAGS: Dict[str, List[str]] = {
    "calm": ["calm", "ambient", "peaceful", "soft", "relaxing", "meditation"],
    "upbeat": ["upbeat", "happy", "energetic", "positive", "optimistic", "cheerful"],
    "romantic": ["romantic", "love", "tender", "emotional", "sweet"],
    "sad": ["sad", "melancholic", "emotional", "piano", "slow"],
    "dramatic": ["dramatic", "cinematic", "powerful", "epic", "suspense"],
    "inspiring": ["inspiring", "motivational", "hopeful", "uplifting", "dreamy"],
}


def search_pixabay_music(
    api_key: str,
    mood: str = "calm",
    per_page: int = 10,
    duration_min: int = 30,
    duration_max: int = 180,
) -> list[dict]:
    """Search Pixabay Music for royalty-free BGM matching a mood.

    Returns a list of track dicts with keys: id, url, title, duration, tags.
    """
    # Use mood tags as search query
    tags = MOOD_TAGS.get(mood, [mood])
    query = ", ".join(tags[:3])

    params = {
        "key": api_key,
        "q": query,
        "per_page": per_page,
    }

    try:
        resp = requests.get(PIXABAY_MUSIC_URL, params=params, timeout=(10, 30))
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[music] Pixabay search failed: {e}")
        return []

    tracks = []
    for hit in data.get("hits", []):
        duration = hit.get("duration", 0)
        if duration < duration_min or duration > duration_max:
            continue
        tracks.append({
            "id": hit.get("id"),
            "title": hit.get("title", "untitled"),
            "url": hit.get("url") or hit.get("audio_url") or hit.get("preview_url", ""),
            "duration": duration,
            "tags": [t.strip() for t in hit.get("tags", "").split(",") if t.strip()],
            "source": "pixabay",
        })

    return tracks


def download_pixabay_track(
    track: dict,
    save_dir: str,
    filename: str | None = None,
) -> str | None:
    """Download a single track from Pixabay.

    Returns local file path, or None on failure.
    """
    url = track.get("url", "")
    if not url:
        return None

    os.makedirs(save_dir, exist_ok=True)

    if not filename:
        ext = url.rsplit(".", 1)[-1] if "." in url else "mp3"
        filename = f"pixabay-{track['id']}.{ext}"

    filepath = os.path.join(save_dir, filename)
    if os.path.isfile(filepath) and os.path.getsize(filepath) > 0:
        return filepath  # already downloaded

    try:
        resp = requests.get(url, timeout=(30, 120))
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)
        return filepath
    except Exception as e:
        print(f"[music] download failed: {track.get('title', url)} => {e}")
        if os.path.isfile(filepath) and os.path.getsize(filepath) == 0:
            os.remove(filepath)
        return None


# ── Local library ──────────────────────────────────────────────────


def scan_library(library_dir: str) -> List[Dict]:
    """Scan a directory for MP3 files and return metadata.

    Returns list of dicts: {file, name, size, source}.
    """
    files = sorted(glob.glob(os.path.join(library_dir, "*.mp3")))
    result = []
    for f in files:
        result.append({
            "file": os.path.abspath(f),
            "name": os.path.splitext(os.path.basename(f))[0],
            "size": os.path.getsize(f),
            "source": "local",
        })
    return result


def pick_bgm(
    library: List[Dict],
    mood: str | None = None,
    avoid_recent: List[str] | None = None,
) -> Optional[Dict]:
    """Pick a BGM track from the library, optionally filtered by mood.

    Args:
        library: List of track dicts (from scan_library or search results).
        mood: Desired mood tag. If None, pick randomly.
        avoid_recent: List of filenames to avoid (already used recently).

    Returns:
        Selected track dict, or None if library is empty.
    """
    if not library:
        return None

    candidates = list(library)

    # Filter out recently used
    if avoid_recent:
        candidates = [t for t in candidates if t.get("file") not in avoid_recent
                      and t.get("name") not in avoid_recent]
        if not candidates:
            candidates = library  # fallback to full library

    # Mood-based selection (simple tag match on name/tags)
    if mood and mood in MOOD_TAGS:
        mood_keywords = MOOD_TAGS[mood]
        mood_matches = []
        for t in candidates:
            name = t.get("name", "").lower()
            tags = [tg.lower() for tg in t.get("tags", [])]
            if any(kw in name or kw in tags for kw in mood_keywords):
                mood_matches.append(t)
        if mood_matches:
            candidates = mood_matches

    return random.choice(candidates)


def init_library(
    target_dir: str,
    source_dir: str | None = None,
    pixabay_key: str | None = None,
    mood: str = "calm",
    count: int = 5,
) -> int:
    """Initialize a BGM library directory.

    1. Copy existing MP3s from source_dir (e.g. MoneyPrinterTurbo's songs).
    2. Optionally download new tracks from Pixabay.

    Returns number of tracks in the library after init.
    """
    os.makedirs(target_dir, exist_ok=True)

    # Copy from source
    if source_dir and os.path.isdir(source_dir):
        copied = 0
        for f in glob.glob(os.path.join(source_dir, "*.mp3")):
            dst = os.path.join(target_dir, os.path.basename(f))
            if not os.path.isfile(dst):
                import shutil
                shutil.copy2(f, dst)
                copied += 1
        if copied:
            print(f"[music] copied {copied} tracks from {source_dir}")

    # Download from Pixabay
    if pixabay_key:
        tracks = search_pixabay_music(
            api_key=pixabay_key, mood=mood, per_page=count
        )
        downloaded = 0
        for t in tracks[:count]:
            fn = f"pixabay-{t['id']}.mp3"
            if not os.path.isfile(os.path.join(target_dir, fn)):
                path = download_pixabay_track(t, target_dir, filename=fn)
                if path:
                    downloaded += 1
        if downloaded:
            print(f"[music] downloaded {downloaded} tracks from Pixabay")

    # Count final
    final = len(scan_library(target_dir))
    print(f"[music] library has {final} tracks")
    return final
