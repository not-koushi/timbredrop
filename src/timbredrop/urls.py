"""Validation for supported single-video YouTube URLs."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}


def extract_video_id(url: str) -> str:
    """Return a video ID for a supported YouTube URL or raise ValueError."""
    candidate = url.strip()
    if not candidate:
        raise ValueError("Enter a YouTube video URL.")

    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("That URL is malformed.") from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Use a complete http:// or https:// YouTube URL.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URLs containing credentials are not supported.")
    if port not in {None, 80, 443}:
        raise ValueError("Non-standard URL ports are not supported.")

    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in _YOUTUBE_HOSTS:
        raise ValueError("That is not a supported YouTube URL.")

    path_parts = [part for part in parsed.path.split("/") if part]
    video_id: str | None = None

    if host in {"youtu.be", "www.youtu.be"}:
        if len(path_parts) == 1:
            video_id = path_parts[0]
    elif parsed.path.rstrip("/") == "/watch":
        video_id = parse_qs(parsed.query).get("v", [None])[0]
    elif len(path_parts) >= 2 and path_parts[0].lower() in {
        "shorts",
        "live",
        "embed",
        "v",
    }:
        video_id = path_parts[1]

    if not video_id or not _VIDEO_ID_RE.fullmatch(video_id):
        raise ValueError(
            "Could not find a valid video ID. Use a standard video, Shorts, live, embed, "
            "or youtu.be URL."
        )

    return video_id


def validate_youtube_url(url: str) -> str:
    """Validate URL shape and return the trimmed original URL.

    This is only an initial syntax check. yt-dlp performs the authoritative
    extractor check and determines whether the video can actually be accessed.
    """
    extract_video_id(url)
    return url.strip()
