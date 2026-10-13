"""Collect text license files for runtime Python dependencies into a release folder."""

from __future__ import annotations

import importlib.metadata
import re
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "THIRD_PARTY_LICENSES"
RUNTIME_DISTRIBUTIONS = {
    "yt-dlp",
    "yt-dlp-ejs",
    "platformdirs",
    "brotli",
    "certifi",
    "mutagen",
    "pycryptodomex",
    "requests",
    "urllib3",
    "websockets",
    "charset-normalizer",
    "idna",
}
LICENSE_NAME = re.compile(r"^(license|licence|copying|notice)(\.|$)", re.IGNORECASE)


def normalized_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    manifest_lines = [
        "Third-party Python distribution license inventory",
        "Generated during the release build; this inventory supplements THIRD_PARTY_NOTICES.md.",
        "",
    ]
    installed = {
        normalized_name(distribution.metadata.get("Name", "")): distribution
        for distribution in importlib.metadata.distributions()
        if distribution.metadata.get("Name")
    }

    for name in sorted(RUNTIME_DISTRIBUTIONS):
        distribution = installed.get(normalized_name(name))
        if distribution is None:
            manifest_lines.append(f"{name}: distribution not found at build time")
            continue

        license_files: list[Path] = []
        for relative in distribution.files or ():
            basename = Path(str(relative)).name
            if not LICENSE_NAME.match(basename):
                continue
            source = Path(distribution.locate_file(relative))
            if source.is_file():
                license_files.append(source)

        license_label = distribution.metadata.get("License-Expression") or distribution.metadata.get(
            "License", "license not declared in package metadata"
        )
        manifest_lines.append(f"{name} {distribution.version}: {license_label}")
        if not license_files:
            manifest_lines.append("  No separate license file found in installed distribution.")
            continue

        destination = output / normalized_name(name)
        destination.mkdir(parents=True, exist_ok=True)
        copied: set[str] = set()
        for index, source in enumerate(license_files, start=1):
            filename = source.name
            if filename in copied:
                filename = f"{index}-{filename}"
            copied.add(filename)
            shutil.copy2(source, destination / filename)
            manifest_lines.append(f"  {normalized_name(name)}/{filename}")

    (output / "MANIFEST.txt").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"Collected third-party license notices in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
