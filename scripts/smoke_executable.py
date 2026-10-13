"""Run a minimal smoke test against the PyInstaller executable."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def main() -> int:
    executable = Path("dist") / ("ytmp3.exe" if os.name == "nt" else "ytmp3")
    if not executable.is_file():
        raise SystemExit(f"Packaged executable not found: {executable}")

    result = subprocess.run(
        [str(executable.resolve()), "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"Executable smoke test failed ({result.returncode}).\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    expected = "TimbreDrop 0.1.2"
    if expected not in result.stdout:
        raise SystemExit(
            f"Unexpected version output. Expected {expected!r}; got {result.stdout!r}."
        )
    print(result.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
