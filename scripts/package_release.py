"""Create a per-platform release ZIP containing the CLI and licensing notices."""

from __future__ import annotations

import argparse
import os
import platform
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def platform_key() -> str:
    if sys.platform.startswith("linux"):
        os_key = "linux"
    elif sys.platform == "darwin":
        os_key = "macos"
    elif os.name == "nt":
        os_key = "windows"
    else:
        raise SystemExit(f"Unsupported release platform: {sys.platform}")

    machine = platform.machine().lower()
    arch = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }.get(machine, machine.replace(" ", "_"))
    return f"{os_key}-{arch}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "release-assets")
    args = parser.parse_args()

    binary_name = "ytmp3.exe" if os.name == "nt" else "ytmp3"
    binary = ROOT / "dist" / binary_name
    if not binary.is_file():
        raise SystemExit(f"PyInstaller output not found: {binary}")

    required_files = [ROOT / "LICENSE", ROOT / "README.md", ROOT / "THIRD_PARTY_NOTICES.md"]
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise SystemExit("Required release files are missing: " + ", ".join(missing))

    archive_dir = args.output_dir.resolve()
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive = archive_dir / f"ytmp3-{platform_key()}.zip"

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(binary, binary.name)
        for file_path in required_files:
            bundle.write(file_path, file_path.name)

        licenses_dir = ROOT / "dist" / "THIRD_PARTY_LICENSES"
        if licenses_dir.is_dir():
            for item in sorted(licenses_dir.rglob("*")):
                if item.is_file():
                    bundle.write(item, Path("THIRD_PARTY_LICENSES") / item.relative_to(licenses_dir))

        external_dependencies = (
            "External runtime requirements (not bundled):\n"
            "- FFmpeg/FFprobe with libmp3lame support, available on PATH.\n"
            "- Deno (recommended JavaScript runtime for current yt-dlp YouTube extraction), on PATH.\n"
            "- A working network connection.\n"
        )
        bundle.writestr("RUNTIME_REQUIREMENTS.txt", external_dependencies)

    print(f"Created release archive: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
