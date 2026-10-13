"""Small TOML configuration loader with safe defaults."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir, user_downloads_dir

APP_NAME = "TimbreDrop"
ALLOWED_BITRATES = (96, 128, 160, 256)

DEFAULT_CONFIG_TEXT = '''# TimbreDrop configuration. Values shown here are the defaults.
# Empty output_dir uses the platform's Downloads directory / TimbreDrop.
output_dir = ""
# Allowed values: 96, 128, 160, 256 (kbps CBR).
default_bitrate = 256
# Warn and ask for confirmation above this duration (minutes).
duration_warning_minutes = 30
# Preserve available metadata such as title and uploader/channel.
preserve_metadata = true
'''


@dataclass(frozen=True)
class AppConfig:
    output_dir: Path
    default_bitrate: int = 256
    duration_warning_minutes: int = 30
    preserve_metadata: bool = True


def config_path() -> Path:
    """Return the OS-appropriate path to config.toml."""
    return Path(user_config_dir(APP_NAME, appauthor=False)) / "config.toml"


def default_output_dir() -> Path:
    """Return a platform-aware Downloads/TimbreDrop output directory."""
    return Path(user_downloads_dir()) / APP_NAME


def default_config() -> AppConfig:
    return AppConfig(output_dir=default_output_dir())


def write_default_config(path: Path | None = None) -> Path:
    """Create the default configuration file without overwriting an existing one."""
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(DEFAULT_CONFIG_TEXT)
    return target


def _get_valid_int(
    raw: dict[str, Any],
    key: str,
    default: int,
    allowed: tuple[int, ...] | None = None,
    minimum: int = 1,
) -> tuple[int, str | None]:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        return default, f"Invalid config value for {key!r}; using {default}."
    if value < minimum or (allowed is not None and value not in allowed):
        expected = (
            f"one of {', '.join(map(str, allowed))}"
            if allowed
            else f"an integer >= {minimum}"
        )
        return default, f"Invalid config value for {key!r}; expected {expected}. Using {default}."
    return value, None


def load_config(path: Path | None = None) -> tuple[AppConfig, list[str]]:
    """Load TOML configuration, falling back field-by-field on invalid values."""
    target = path or config_path()
    defaults = default_config()
    warnings: list[str] = []

    try:
        with target.open("rb") as stream:
            raw = tomllib.load(stream)
    except FileNotFoundError:
        return defaults, warnings
    except (OSError, tomllib.TOMLDecodeError) as exc:
        warnings.append(f"Could not read config file {target}: {exc}. Using defaults.")
        return defaults, warnings

    if not isinstance(raw, dict):
        warnings.append("Config root must be a TOML table. Using defaults.")
        return defaults, warnings

    output_value = raw.get("output_dir", "")
    if not isinstance(output_value, str):
        warnings.append(
            "Invalid config value for 'output_dir'; using the default output directory."
        )
        output_dir = defaults.output_dir
    elif not output_value.strip():
        output_dir = defaults.output_dir
    else:
        output_dir = Path(output_value).expanduser()
        if not output_dir.is_absolute():
            warnings.append(
                "'output_dir' must be an absolute path; using the default output directory."
            )
            output_dir = defaults.output_dir

    bitrate, bitrate_warning = _get_valid_int(
        raw, "default_bitrate", defaults.default_bitrate, allowed=ALLOWED_BITRATES
    )
    if bitrate_warning:
        warnings.append(bitrate_warning)

    duration, duration_warning = _get_valid_int(
        raw, "duration_warning_minutes", defaults.duration_warning_minutes, minimum=1
    )
    if duration_warning:
        warnings.append(duration_warning)

    preserve_metadata = raw.get("preserve_metadata", defaults.preserve_metadata)
    if not isinstance(preserve_metadata, bool):
        warnings.append("Invalid config value for 'preserve_metadata'; using true.")
        preserve_metadata = defaults.preserve_metadata

    return AppConfig(
        output_dir=output_dir,
        default_bitrate=bitrate,
        duration_warning_minutes=duration,
        preserve_metadata=preserve_metadata,
    ), warnings
