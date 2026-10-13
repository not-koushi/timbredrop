"""Interactive terminal interface for TimbreDrop."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

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

CYAN = "36"
GRAY = "90"


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


def _color(text: str, tone: str) -> str:
    """Apply a restrained ANSI accent only for interactive terminals."""
    if not sys.stdout.isatty() or "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb":
        return text
    return f"\033[{tone}m{text}\033[0m"


def _print_commands() -> None:
    print("Commands:")
    print(f"  {_color('url <link>', CYAN)}    download and convert a YouTube video's audio")
    print(f"  {_color('path', CYAN)}          show or change the output location")
    print(f"  {_color('exit', CYAN)}          quit TimbreDrop")
    print()


def _yes_no(prompt: str, default: bool = False) -> bool:
    choice_hint = "Y/n" if default else "y/N"
    while True:
        try:
            answer = input(f"{prompt} [{choice_hint}]: ").strip().lower()
        except EOFError:
            return False
        except KeyboardInterrupt:
            print()
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
        except KeyboardInterrupt:
            print()
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


def _external_process_env() -> dict[str, str]:
    """Return a safe environment for OS tools launched from the frozen app.

    PyInstaller modifies ``LD_LIBRARY_PATH`` on Linux so the bundled executable
    can load its private libraries. External desktop tools such as xdg-open,
    gio, and Kate must not inherit that private path: it can make system apps
    load incompatible bundled libraries and fail to open. Restore the original
    value for child processes while leaving TimbreDrop's own environment intact.
    """
    env = os.environ.copy()
    if sys.platform.startswith("linux") and getattr(sys, "frozen", False):
        original_library_path = env.pop("LD_LIBRARY_PATH_ORIG", None)
        if original_library_path:
            env["LD_LIBRARY_PATH"] = original_library_path
        else:
            env.pop("LD_LIBRARY_PATH", None)
    return env


def _open_with_system_default(
    path: Path,
    *,
    operating_system: str | None = None,
    platform_name: str | None = None,
) -> bool:
    """Open a text file using the OS desktop's associated editor, if available.

    On Linux, xdg-open delegates to the desktop's default application (e.g. Kate
    on a KDE desktop). Windows uses the file association, and macOS asks Launch
    Services for the default text editor. This function deliberately avoids
    invoking a shell.
    """
    operating_system = operating_system or os.name
    platform_name = platform_name or sys.platform

    if operating_system == "nt":
        startfile = getattr(os, "startfile", None)
        if startfile is None:
            return False
        try:
            startfile(str(path))
            return True
        except OSError as exc:
            print(f"Could not open the config with its associated app: {exc}", file=sys.stderr)
            return False

    if platform_name == "darwin":
        opener = shutil.which("open")
        if not opener:
            return False
        try:
            subprocess.Popen(
                [opener, "-t", str(path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=_external_process_env(),
            )
            return True
        except OSError as exc:
            print(f"Could not open the config with the default text editor: {exc}", file=sys.stderr)
            return False

    # Do not try to launch a GUI application from a headless Linux session.
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False

    opener = shutil.which("xdg-open")
    if opener:
        try:
            subprocess.Popen(
                [opener, str(path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=_external_process_env(),
            )
            return True
        except OSError as exc:
            print(
                f"Could not open the config with the desktop's default app: {exc}",
                file=sys.stderr,
            )

    # gio is available on many GNOME/KDE Linux installations as a fallback.
    gio = shutil.which("gio")
    if gio:
        try:
            subprocess.Popen(
                [gio, "open", str(path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=_external_process_env(),
            )
            return True
        except OSError as exc:
            print(f"Could not open the config with gio: {exc}", file=sys.stderr)
    return False


def _launch_config_editor_setting(path: Path, setting: str, variable_name: str) -> bool:
    """Launch a user-specified editor command without shell interpretation."""
    try:
        command = shlex.split(setting)
    except ValueError as exc:
        print(f"Invalid {variable_name} setting: {exc}", file=sys.stderr)
        return False
    if not command:
        return False

    executable = shutil.which(command[0])
    if not executable:
        print(f"Editor not found: {command[0]} (from {variable_name}).", file=sys.stderr)
        return False
    try:
        # Terminal editors run in the foreground so users can save and return.
        subprocess.run(
            [executable, *command[1:], str(path)],
            check=False,
            env=_external_process_env(),
        )
        return True
    except OSError as exc:
        print(f"Could not launch editor {command[0]}: {exc}", file=sys.stderr)
        return False


def _open_config_file(path: Path) -> bool:
    """Open the config in the user's preferred editor without invoking a shell.

    Priority:
    1. TIMBREDROP_EDITOR, an explicit TimbreDrop-specific override.
    2. The operating system's default text editor / file association.
    3. VISUAL or EDITOR for terminal/headless sessions.
    4. A common terminal editor as a last resort on Unix-like systems.

    GUI launchers may return before the config is saved; config is refreshed
    before each subsequent shell command.
    """
    explicit_editor = os.environ.get("TIMBREDROP_EDITOR")
    if explicit_editor:
        return _launch_config_editor_setting(path, explicit_editor, "TIMBREDROP_EDITOR")

    if _open_with_system_default(path):
        print(
            "Opened the config with your system's default text editor. "
            "Save it, then return here."
        )
        return True

    for variable_name in ("VISUAL", "EDITOR"):
        editor_setting = os.environ.get(variable_name)
        if editor_setting and _launch_config_editor_setting(path, editor_setting, variable_name):
            return True

    # Terminal-only/headless fallback when no system desktop editor is available.
    if os.name != "nt":
        for editor_name in ("nano", "micro", "vim", "vi"):
            executable = shutil.which(editor_name)
            if executable:
                try:
                    subprocess.run(
                        [executable, str(path)],
                        check=False,
                        env=_external_process_env(),
                    )
                    return True
                except OSError as exc:
                    print(f"Could not launch editor {editor_name}: {exc}", file=sys.stderr)
                    return False

    # Notepad is available on standard Windows installations if file association
    # launching was unavailable. It is not used when an OS association worked.
    if os.name == "nt":
        executable = shutil.which("notepad.exe") or shutil.which("notepad")
        if executable:
            try:
                subprocess.Popen([executable, str(path)], env=_external_process_env())
                return True
            except OSError as exc:
                print(f"Could not launch Notepad: {exc}", file=sys.stderr)

    print(
        "No suitable editor was found. Set TIMBREDROP_EDITOR to choose one, "
        f"or set VISUAL/EDITOR for terminal use.\nConfig: {path}"
    )
    return False


def _handle_path_command(output_dir: Path) -> None:
    target = config_path()
    print(f"Current output directory: {output_dir}")
    if not _yes_no("Would you like to change it?", default=False):
        return

    try:
        if not target.exists():
            write_default_config(target)
    except FileExistsError:
        pass
    except OSError as exc:
        print(f"Could not create the configuration file: {exc}", file=sys.stderr)
        return

    print(f"Opening configuration file: {target}")
    opened = _open_config_file(target)
    if opened:
        print("Changes are picked up before the next command. Set output_dir in this file.")


def _run_url_command(
    raw_url: str,
    config: Any,
    output_dir: Path,
) -> None:
    try:
        url = validate_youtube_url(raw_url)
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    try:
        print("Checking video metadata…")
        info = fetch_video_info(url)
        if not _check_duration(info, config.duration_warning_minutes):
            print("Skipped.")
            return
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
    reported_warnings: set[str] = set()
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
        reported_warnings.add(warning)

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

    output_override = args.output_dir.expanduser() if args.output_dir else None
    output_dir = output_override or config.output_dir

    _print_commands()
    print(f"{_color('TimbreDrop', CYAN)} {_color(__version__, GRAY)} — YouTube audio to MP3")
    print(f"Output directory: {_color(str(output_dir), CYAN)}")
    legal_note = "Use only content you own, have permission to download, or may lawfully save."
    print(_color(legal_note, GRAY))
    print("\nEnter a command below. Use 'help' to show the commands again.\n")

    while True:
        try:
            raw_command = input(f"{_color('ytmp3', CYAN)} ").strip()
        except EOFError:
            print("\nGoodbye.")
            return 0
        except KeyboardInterrupt:
            print("\nGoodbye.")
            return 130

        # Reload config after the user returns from a possibly external editor.
        fresh_config, fresh_warnings = load_config()
        config = fresh_config
        for warning in fresh_warnings:
            if warning not in reported_warnings:
                print(f"Warning: {warning}", file=sys.stderr)
                reported_warnings.add(warning)
        previous_output_dir = output_dir
        output_dir = output_override or config.output_dir
        if output_dir != previous_output_dir:
            print(f"Output directory updated: {_color(str(output_dir), CYAN)}")

        if not raw_command:
            continue

        command, separator, argument = raw_command.partition(" ")
        command = command.casefold()
        argument = argument.strip() if separator else ""

        if command in {"exit", "quit"}:
            print("Goodbye.")
            return 0
        if command == "help":
            _print_commands()
            print("Use 'path' to edit config.toml; use 'url <link>' to process a video.")
            continue
        if command == "path":
            _handle_path_command(output_dir)
            if output_override is not None:
                print("Note: --output-dir overrides the config path for this session.")
            continue
        if command == "url":
            if not argument:
                print("Usage: url <YouTube-URL>")
                continue
            _run_url_command(argument, config, output_dir)
            print()
            continue

        print("Unknown command. Use 'help' to see the available commands.")


if __name__ == "__main__":
    raise SystemExit(main())
