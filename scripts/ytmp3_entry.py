"""PyInstaller entry point for the TimbreDrop console application."""

from timbredrop.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
