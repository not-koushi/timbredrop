"""YouTube metadata retrieval, audio download, and MP3 encoding."""

from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import unicodedata
from collections import deque
from pathlib import Path
from typing import Any, Callable

from timbredrop.config import ALLOWED_BITRATES
from timbredrop.errors import MissingDependencyError, TimbreDropError

ProgressHook = Callable[[dict[str, Any]], None]
ConversionProgress = Callable[[float | None, str | None], None]
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def check_dependencies() -> tuple[str, str]:
    """Return FFmpeg/FFprobe executable paths or raise a friendly error."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    missing = []
    if not ffmpeg:
        missing.append("ffmpeg")
    if not ffprobe:
        missing.append("ffprobe")
    if missing:
        raise MissingDependencyError(
            f"Missing required executable(s): {', '.join(missing)}. Install FFmpeg and make "
            "sure its bin directory is on PATH."
        )
    return ffmpeg, ffprobe


def format_duration(seconds: float | int | None) -> str:
    if seconds is None or seconds < 0:
        return "unknown"
    whole = int(seconds)
    hours, remainder = divmod(whole, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def sanitize_filename(title: str | None, max_length: int = 160) -> str:
    """Make untrusted metadata safe as a portable filename stem."""
    value = unicodedata.normalize("NFC", str(title or "video"))
    value = "".join(char for char in value if char.isprintable())
    value = _INVALID_FILENAME_CHARS.sub("_", value)
    value = re.sub(r"\s+", " ", value).strip().rstrip(". ")
    value = value[:max_length].rstrip(". ")
    if not value or value in {".", ".."}:
        value = "video"
    if value.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES:
        value = f"_{value}"
    return value


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TiB"


def _short_error(exc: BaseException) -> str:
    message = str(exc).strip().replace("\r", " ").replace("\n", " ")
    return message or exc.__class__.__name__


def fetch_video_info(url: str) -> dict[str, Any]:
    """Retrieve metadata without downloading the media."""
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 2,
    }
    try:
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import DownloadError
    except ImportError as exc:
        raise MissingDependencyError(
            "yt-dlp is not installed in this Python environment. Install TimbreDrop with "
            "`python -m pip install -e .`."
        ) from exc

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        raise TimbreDropError(f"Could not retrieve video information: {_short_error(exc)}") from exc
    except Exception as exc:
        raise TimbreDropError(f"Metadata lookup failed: {_short_error(exc)}") from exc

    if not isinstance(info, dict):
        raise TimbreDropError("yt-dlp did not return video metadata for this URL.")
    if info.get("_type") in {"playlist", "multi_video"} or info.get("entries") is not None:
        raise TimbreDropError("Playlists are not supported. Enter a URL for one video.")
    return info


def download_audio(
    url: str,
    working_dir: Path,
    progress_hook: ProgressHook | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Download the best available audio stream into a temporary directory."""
    working_dir.mkdir(parents=True, exist_ok=True)
    options: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": str(working_dir / "source.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
    }
    if progress_hook:
        options["progress_hooks"] = [progress_hook]

    try:
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import DownloadError
    except ImportError as exc:
        raise MissingDependencyError(
            "yt-dlp is not installed in this Python environment. Install TimbreDrop with "
            "`python -m pip install -e .`."
        ) from exc

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if not isinstance(info, dict):
                raise TimbreDropError("yt-dlp did not return downloaded video information.")
            prepared_path = Path(ydl.prepare_filename(info))
    except TimbreDropError:
        raise
    except DownloadError as exc:
        raise TimbreDropError(f"Audio download failed: {_short_error(exc)}") from exc
    except Exception as exc:
        raise TimbreDropError(f"Audio download failed: {_short_error(exc)}") from exc

    possible_paths: list[Path] = []
    requested_downloads = info.get("requested_downloads")
    if isinstance(requested_downloads, list):
        for requested in requested_downloads:
            if isinstance(requested, dict) and requested.get("filepath"):
                possible_paths.append(Path(requested["filepath"]))
    possible_paths.append(prepared_path)
    possible_paths.extend(path for path in working_dir.iterdir() if path.is_file())

    for path in possible_paths:
        if path.exists() and path.is_file() and path.stat().st_size > 0:
            return path, info
    raise TimbreDropError("The download completed but no usable audio file was found.")


def _candidate_output_path(output_dir: Path, title: str) -> Path:
    stem = sanitize_filename(title)
    candidate = output_dir / f"{stem}.mp3"
    suffix = 2
    while candidate.exists():
        candidate = output_dir / f"{stem} ({suffix}).mp3"
        suffix += 1
    return candidate


def _publish_without_overwrite(temp_file: Path, output_dir: Path, title: str) -> Path:
    """Atomically publish output without replacing an existing file where possible."""
    stem = sanitize_filename(title)
    first_candidate = _candidate_output_path(output_dir, title)
    numbered = re.fullmatch(re.escape(stem) + r" \((\d+)\)\.mp3", first_candidate.name)
    suffix = int(numbered.group(1)) if numbered else 1
    while True:
        name = f"{stem}.mp3" if suffix == 1 else f"{stem} ({suffix}).mp3"
        candidate = output_dir / name
        try:
            os.link(temp_file, candidate)
            temp_file.unlink(missing_ok=True)
            return candidate
        except FileExistsError:
            suffix += 1
        except OSError:
            # Some filesystems disallow hard links. Exclusive creation still guarantees
            # that we never overwrite a file, though the copy itself is not atomic.
            try:
                descriptor = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
            except FileExistsError:
                suffix += 1
                continue
            try:
                with os.fdopen(descriptor, "wb") as destination, temp_file.open("rb") as source:
                    shutil.copyfileobj(source, destination)
                temp_file.unlink(missing_ok=True)
                return candidate
            except Exception:
                candidate.unlink(missing_ok=True)
                raise


def _read_pipe_lines(pipe: Any, destination: queue.Queue[str | None]) -> None:
    try:
        for line in iter(pipe.readline, ""):
            destination.put(line.rstrip("\r\n"))
    finally:
        pipe.close()
        destination.put(None)


def transcode_mp3(
    source_path: Path,
    output_dir: Path,
    info: dict[str, Any],
    bitrate: int,
    preserve_metadata: bool = True,
    conversion_progress: ConversionProgress | None = None,
) -> Path:
    """Encode source audio to MP3 CBR and safely publish the finished file."""
    if bitrate not in ALLOWED_BITRATES:
        raise TimbreDropError(f"Unsupported bitrate {bitrate}; choose one of {ALLOWED_BITRATES}.")
    ffmpeg, _ = check_dependencies()
    output_dir.mkdir(parents=True, exist_ok=True)
    title = sanitize_filename(info.get("title"))
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".timbredrop-", suffix=".mp3", dir=output_dir
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    stderr_tail: deque[str] = deque(maxlen=30)
    duration = info.get("duration")
    duration = float(duration) if isinstance(duration, (float, int)) and duration > 0 else None

    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostats",
        "-progress",
        "pipe:1",
        "-i",
        str(source_path),
        "-map",
        "0:a:0",
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        f"{bitrate}k",
        "-abr",
        "0",
        "-compression_level",
        "2",
        "-id3v2_version",
        "3",
    ]
    if preserve_metadata:
        command.extend(["-map_metadata", "0"])
        tags = {
            "title": str(info.get("title") or ""),
            "artist": str(info.get("artist") or info.get("uploader") or info.get("channel") or ""),
        }
        upload_date = str(info.get("upload_date") or "")
        if re.match(r"^\d{4}", upload_date):
            tags["date"] = upload_date[:4]
        for key, value in tags.items():
            clean_value = _CONTROL_CHARS.sub(" ", value).strip()
            if clean_value:
                command.extend(["-metadata", f"{key}={clean_value}"])
    command.extend(["-f", "mp3", "-y", str(temporary_path)])

    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        if process.stdout is None or process.stderr is None:
            process.kill()
            process.wait()
            raise TimbreDropError("Could not read FFmpeg progress output.")

        stdout_queue: queue.Queue[str | None] = queue.Queue()
        stdout_thread = threading.Thread(
            target=_read_pipe_lines, args=(process.stdout, stdout_queue), daemon=True
        )
        stdout_thread.start()

        def collect_stderr() -> None:
            assert process.stderr is not None
            for line in process.stderr:
                text = line.strip()
                if text:
                    stderr_tail.append(text)
            process.stderr.close()

        stderr_thread = threading.Thread(target=collect_stderr, daemon=True)
        stderr_thread.start()
        started = time.monotonic()
        timeout_seconds = max(600.0, (duration or 3600.0) * 3.0 + 300.0)
        reached_eof = False
        while not reached_eof:
            if time.monotonic() - started > timeout_seconds:
                process.kill()
                process.wait(timeout=10)
                raise TimbreDropError("FFmpeg timed out while converting the audio.")
            try:
                line = stdout_queue.get(timeout=1.0)
            except queue.Empty:
                if process.poll() is not None and not stdout_thread.is_alive():
                    break
                continue
            if line is None:
                reached_eof = True
                continue
            if line.startswith("out_time_ms="):
                try:
                    elapsed = int(line.split("=", 1)[1]) / 1_000_000
                except ValueError:
                    elapsed = None
                if conversion_progress:
                    percentage = (
                        min(100.0, elapsed * 100.0 / duration)
                        if elapsed is not None and duration
                        else None
                    )
                    elapsed_text = format_duration(elapsed) if elapsed is not None else None
                    conversion_progress(percentage, elapsed_text)
            elif line.startswith("out_time=") and conversion_progress:
                elapsed_label = line.split("=", 1)[1]
                if not duration:
                    conversion_progress(None, elapsed_label)

        return_code = process.wait(timeout=30)
        stderr_thread.join(timeout=2)
        stdout_thread.join(timeout=2)
        if return_code != 0:
            detail = " | ".join(stderr_tail) if stderr_tail else f"exit code {return_code}"
            raise TimbreDropError(f"FFmpeg could not convert this audio: {detail}")
        if not temporary_path.exists() or temporary_path.stat().st_size == 0:
            raise TimbreDropError("FFmpeg finished without producing a valid MP3 file.")

        try:
            return _publish_without_overwrite(temporary_path, output_dir, title)
        except OSError as exc:
            raise TimbreDropError(f"Could not write the MP3 output file: {_short_error(exc)}") from exc
    except KeyboardInterrupt:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        raise
    except FileNotFoundError as exc:
        raise MissingDependencyError(
            "FFmpeg was not found. Install FFmpeg and ensure it is on PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        if process is not None:
            process.kill()
            process.wait()
        raise TimbreDropError("FFmpeg did not exit cleanly after conversion.") from exc
    except OSError as exc:
        raise TimbreDropError(f"Could not run FFmpeg: {_short_error(exc)}") from exc
    finally:
        temporary_path.unlink(missing_ok=True)
