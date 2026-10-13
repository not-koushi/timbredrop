# Changelog

## 0.1.4

- Correct application/package metadata to match the release version.
- Keep standalone binary releases optional; the Arch path uses system dependencies.
- Prepare a pinned source-based Arch package for local testing and AUR submission.
- Retain the frozen-Linux external-editor launch fix.

## 0.1.3

- Fix opening external desktop applications from the Linux standalone executable.
- Restore the original `LD_LIBRARY_PATH` for child processes launched from a PyInstaller bundle, preventing bundled library paths from breaking `xdg-open`, `gio`, or the configured editor.
- Add regression tests for frozen-Linux child-process environments.
