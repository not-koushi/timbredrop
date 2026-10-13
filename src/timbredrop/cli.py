"""Interactive terminal interface for TimbreDrop."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

from timbredrop import __version__
from timbredrop.config import ALLOWED_BITRATES, config_path, load_config, write_default_config
from timbredrop.errors import MissingDependencyError, TimbreDropError
from timbredrop.media import (
    check_dependencies,
    download_audio,
    fetch_video_info,
    format_bytes,
    format_duration,
    transcode_mp3,
)
from timbredrop.urls import validate_youtube_url


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytmp3",
        description="Extract audio from one supported YouTube video and encode it as MP3.",
    )
    parser.add_argument("--version", action="version", version=f"TimbreDrop {__version__}")
    parser.add_argument(
        "--show-config", action="store_true", help="print the configuration file path and exit"
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="create the default config file without overwriting one",
    )
    parser.add_argument(
        "--output-dir", type=Path, help="override the configured output directory for this session"
    )
    return parser


def _yes_no(prompt: str, default: bool = False) -> bool:
    choice_hint = "Y/n" if default else "y/N"
    while True:
        try:
            answer = input(f"{prompt} [{choice_hint}]: ").strip().lower()
        except EOFError:
            return False
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter y or n.")


def _choose_bitrate(default: int) -> int:
    print("\nChoose MP3 output bitrate (constant bitrate):")
    for index, value in enumerate(ALLOWED_BITRATES, start=1):
        suffix = " (default)" if value == default else ""
        print(f"  {index}. {value} kbps{suffix}")
    while True:
        try:
            answer = input(f"Bitrate [{default}]: ").strip()
        except EOFError:
            return default
        if not answer:
            return default
        if answer.isdigit():
            numeric = int(answer)
            if numeric in ALLOWED_BITRATES:
                return numeric
            if 1 <= numeric <= len(ALLOWED_BITRATES):
                return ALLOWED_BITRATES[numeric - 1]
        print(
            f"Choose a number from 1 to {len(ALLOWED_BITRATES)}, or enter "
            f"{', '.join(map(str, ALLOWED_BITRATES))}."
        )


def _download_progress(status: dict[str, Any]) -> None:
    state = status.get("status")
    if state == "finished":
        print("\rDownload complete.                                      ")
        return
    if state != "downloading":
        if state == "error":
            print("\nDownload reported an error.")
        return

    downloaded = status.get("downloaded_bytes")
    total = status.get("total_bytes") or status.get("total_bytes_estimate")
    speed = status.get("speed")
    eta = status.get("eta")
    if isinstance(downloaded, (int, float)) and isinstance(total, (int, float)) and total > 0:
        percent = min(100.0, downloaded * 100.0 / total)
        line = (
            f"Downloading: {percent:5.1f}% "
            f"({format_bytes(int(downloaded))} / {format_bytes(int(total))})"
        )
    elif isinstance(downloaded, (int, float)):
        line = f"Downloading: {format_bytes(int(downloaded))}"
    else:
        line = "Downloading audio…"
    if isinstance(speed, (int, float)) and speed > 0:
        line += f" · {format_bytes(int(speed))}/s"
    if isinstance(eta, (int, float)) and eta >= 0:
        line += f" · ETA {format_duration(eta)}"
    print("\r" + line.ljust(100), end="", flush=True)


def _conversion_progress(percentage: float | None, elapsed_label: str | None) -> None:
    if percentage is not None:
        line = f"Converting to MP3: {percentage:5.1f}%"
    elif elapsed_label:
        line = f"Converting to MP3: elapsed {elapsed_label}"
    else:
        line = "Converting to MP3…"
    print("\r" + line.ljust(100), end="", flush=True)


def _safe_terminal_text(value: Any, fallback: str = "") -> str:
    """Strip control characters from untrusted metadata before displaying it."""
    text = str(value or fallback)
    return "".join(character for character in text if character.isprintable())


def _check_duration(info: dict[str, Any], warning_minutes: int) -> bool:
    duration = info.get("duration")
    title = _safe_terminal_text(info.get("title"), "Untitled video")
    print(f"\nTitle: {title}")
    if isinstance(duration, (int, float)) and duration > 0:
        print(f"Duration: {format_duration(duration)}")
        if duration > warning_minutes * 60:
            print(f"Warning: this video is longer than {warning_minutes} minutes.")
            return _yes_no("Continue with this video?", default=False)
        return True
    print("Duration could not be determined before downloading.")
    return _yes_no("Continue anyway?", default=False)


def _process_one(
    url: str,
    info: dict[str, Any],
    bitrate: int,
    output_dir: Path,
    preserve_metadata: bool,
) -> Path:
    print("\nDownloading the best available audio stream…")
    with tempfile.TemporaryDirectory(prefix="timbredrop-") as temporary_directory:
        source, download_info = download_audio(url, Path(temporary_directory), _download_progress)
        print("\nEncoding MP3…")
        merged_info = {**info, **download_info}
        result = transcode_mp3(
            source_path=source,
            output_dir=output_dir,
            info=merged_info,
            bitrate=bitrate,
            preserve_metadata=preserve_metadata,
            conversion_progress=_conversion_progress,
        )
    print("\rConversion complete.                                      ")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.show_config:
        print(config_path())
        return 0
    if args.init_config:
        try:
            created = write_default_config()
        except FileExistsError:
            print(f"Configuration already exists: {config_path()}", file=sys.stderr)
            print("Edit it manually; TimbreDrop will not overwrite it.", file=sys.stderr)
            return 1
        except OSError as exc:
            print(f"Could not create configuration file: {exc}", file=sys.stderr)
            return 1
        print(f"Created configuration file: {created}")
        return 0

    config, warnings = load_config()
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    try:
        check_dependencies()
    except MissingDependencyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if not shutil.which("deno"):
        print(
            "Warning: Deno was not found on PATH. yt-dlp may have reduced compatibility "
            "with YouTube extraction.",
            file=sys.stderr,
        )

    output_dir = args.output_dir.expanduser() if args.output_dir else config.output_dir
    print(f"TimbreDrop {__version__} — YouTube audio to MP3")
    print(f"Output directory: {output_dir}")
    print("Use only content you own, have permission to download, or may lawfully save.")
    print("Enter a URL below. Press Enter on an empty line to quit.\n")

    while True:
        try:
            raw_url = input("Enter YouTube URL: ").strip()
        except EOFError:
            print("\nGoodbye.")
            return 0
        except KeyboardInterrupt:
            print("\nGoodbye.")
            return 130
        if not raw_url:
            print("Goodbye.")
            return 0

        try:
            url = validate_youtube_url(raw_url)
        except ValueError as exc:
            print(f"Error: {exc}\n")
            continue

        try:
            print("Checking video metadata…")
            info = fetch_video_info(url)
            if not _check_duration(info, config.duration_warning_minutes):
                print("Skipped.\n")
                continue
            bitrate = _choose_bitrate(config.default_bitrate)
            result = _process_one(url, info, bitrate, output_dir, config.preserve_metadata)
            print("\nSuccess: MP3 created")
            print(f"  Title: {_safe_terminal_text(info.get('title'), result.stem)}")
            print(f"  Output bitrate: {bitrate} kbps CBR")
            print(f"  File: {result.resolve()}")
            print(f"  Size: {format_bytes(result.stat().st_size)}")
            print("  Note: the output bitrate does not restore quality absent from the source stream.")
        except (TimbreDropError, OSError) as exc:
            print(f"\nError: {exc}", file=sys.stderr)
        except KeyboardInterrupt:
            print("\nCancelled by user.")
        print("\n")


if __name__ == "__main__":
    raise SystemExit(main())
