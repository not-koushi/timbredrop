"""Ensure the requested release tag matches the project version."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    release_tag = os.environ.get("RELEASE_TAG", "").strip()

    project = tomllib.loads(
        (root / "pyproject.toml").read_text(encoding="utf-8")
    )
    expected_tag = f"v{project['project']['version']}"

    if release_tag != expected_tag:
        raise SystemExit(
            f"Release tag mismatch: expected {expected_tag!r}, "
            f"received {release_tag!r}."
        )

    print(f"Release tag {release_tag} matches the project version.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
