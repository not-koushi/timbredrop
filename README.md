# TimbreDrop

A minimal, cross-platform command-line application for extracting audio from one supported YouTube video and encoding it as MP3 using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org/).

> **Independent project:** TimbreDrop is not affiliated with or endorsed by YouTube. It is intended for content you own, have permission to download, or may lawfully save.

## Features

- Interactive terminal workflow; enter more than one URL in a session.
- Supports common single-video URL forms, including watch, `youtu.be`, Shorts, live and embed URLs.
- Retrieves title and duration before starting the download.
- Warns before downloading videos longer than 30 minutes; the threshold is configurable.
- Offers 96, 128, 160 or 256 kbps MP3 constant-bitrate (CBR) output.
- Shows download progress and FFmpeg conversion progress.
- Uses platform-specific configuration directories and the user's Downloads directory by default.
- Sanitizes filenames, avoids silently overwriting an existing MP3, and cleans up temporary files.
- Keeps YouTube extraction and audio conversion as separate steps for clearer errors and progress.
- Provides a compact command shell with `url <link>`, `path`, and `exit` commands.
- Uses a restrained cyan-and-gray terminal accent when supported; respects `NO_COLOR`.

## Requirements

- Python 3.11 or newer.
- FFmpeg with `libmp3lame` support and `ffprobe`, available on `PATH`.
- A supported JavaScript runtime for current yt-dlp YouTube extraction. [Deno](https://deno.com/) is recommended.
- Network access to the video and to the endpoints required by yt-dlp.

YouTube extraction can change over time. The latest yt-dlp version, its default EJS companion package, and a compatible JavaScript runtime improve compatibility but cannot guarantee that every video is accessible. See the [yt-dlp project](https://github.com/yt-dlp/yt-dlp) and [EJS guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS) for current requirements.

## Install from source

### Arch Linux

The intended end-user installation is an AUR package, so the eventual workflow
will be:

```bash
yay -S timbredrop
ytmp3
```

**The AUR package is not published yet**, so that command will not work until
publication. Do not use `sudo pacman -S timbredrop`: the package is not in the
official Arch repositories. Maintainers should follow
[`packaging/arch/README.md`](packaging/arch/README.md) to test the PKGBUILD first.

The Arch package contains only the Python application and documentation. It
uses system packages for `yt-dlp`, FFmpeg/FFprobe, Deno, Python and
`platformdirs`; it does not download or install the 20–40 MB portable ZIP.

For development from a checkout:

```bash
sudo pacman -Syu --needed git python python-pip ffmpeg deno
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run `ytmp3` or `python -m timbredrop` while the virtual environment is active.

### Other Linux distributions

Install Python 3.11+, FFmpeg/FFprobe, and Deno using your distribution's supported package manager, then follow the virtual-environment steps above. Package names vary by distribution.

### Windows (PowerShell)

Install Python 3.11+, FFmpeg, and Deno, and ensure each executable is on `PATH`. In PowerShell:

```powershell
git clone https://github.com/not-koushi/timbredrop.git
Set-Location timbredrop
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
ytmp3
```

Then run `ytmp3`. If PowerShell blocks activation, see Python's virtual-environment documentation; you can also use `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"` and invoke `.\.venv\Scripts\ytmp3.exe` directly. Windows execution has not yet been verified by the project maintainers.

### macOS

Install Python 3.11+, FFmpeg and Deno (for example, using Homebrew), then follow the Linux virtual-environment steps. macOS execution has not yet been verified by the project maintainers.

## Usage

Start the interactive shell:

```bash
ytmp3
```

The shell displays its available commands, version, current output directory, and legal reminder before showing the `(>_ ytmp3)` prompt.

| Command | Action |
|---|---|
| `url <YouTube-URL>` | Validate the URL, inspect video metadata, select a bitrate, then download and convert the audio. |
| `path` | Show the current output directory and offer to open the configuration file for editing. |
| `exit` | Quit the shell. |
| `help` | Print the command list again. |

Example:

```text
(>_ ytmp3) url https://youtu.be/VIDEO_ID
```

After each conversion, TimbreDrop returns to the shell so another URL can be processed. Follow the prompts to confirm long or unknown durations and choose an output bitrate. Press Enter to accept the configured bitrate (256 kbps by default).

The shell uses a muted cyan-and-gray accent only when stdout is an interactive terminal. Set `NO_COLOR=1` to disable ANSI colors. The `path` command first opens the configuration file with the operating system's default text editor (for example, Kate when Kate is the default text-file handler on KDE, the associated app on Windows, or the default text editor on macOS). If the session is headless or no desktop handler is available, TimbreDrop falls back to `VISUAL`/`EDITOR` and then a common terminal editor. Set `TIMBREDROP_EDITOR` to explicitly override editor selection, for example `TIMBREDROP_EDITOR="kate --new-window"`. Editor commands are launched without shell interpretation.

Override the output directory for one session:

```bash
ytmp3 --output-dir "$HOME/Music/YouTube Audio"
```

On PowerShell:

```powershell
ytmp3 --output-dir "$HOME\Music\YouTube Audio"
```

Use the command exactly as `ytmp3`.

## Configuration

Show the configuration path:

```bash
ytmp3 --show-config
```

Create the default configuration file without overwriting an existing one:

```bash
ytmp3 --init-config
```

The file is named `config.toml`. Its location is platform-dependent (and respects the platformdirs/XDG configuration environment):

- Linux: typically `~/.config/TimbreDrop/config.toml`.
- Windows: typically `%LOCALAPPDATA%\TimbreDrop\config.toml`.
- macOS: typically `~/Library/Application Support/TimbreDrop/config.toml`.

Example:

```toml
output_dir = ""
default_bitrate = 256
duration_warning_minutes = 30
preserve_metadata = true
```

An empty `output_dir` uses the user's Downloads directory under a `TimbreDrop` folder. `default_bitrate` must be `96`, `128`, `160`, or `256`. Invalid values fall back to defaults with a warning. The interactive `path` command opens this file for editing after confirmation; changes are reloaded before the next shell command. If you launched with `--output-dir`, that command-line override remains active until the process exits.

## Audio quality and bitrate

The selected bitrate is the output MP3's CBR target; it does **not** describe or improve the original YouTube stream. YouTube commonly delivers audio in lossy formats such as Opus or AAC. Converting those streams to MP3 is another lossy encoding step, and encoding at 256 kbps cannot restore information that was already discarded upstream. The 256 kbps default prioritizes a higher MP3 output bitrate, not a guarantee of higher fidelity than the source.

## Platform verification status

The Linux unit test suite and FFmpeg MP3-encoding smoke tests have been run in the development environment. An Arch Linux user has verified interactive shell startup and the default-editor workflow. This repository includes CI for tests on Linux, Windows, and macOS, plus release workflows for native builds; those workflows are not considered verified until they have run successfully on GitHub. A complete live download should still be checked on each operating system before claiming full platform support. No standalone release artifact is available until a version tag is pushed and the release workflow succeeds.

## Troubleshooting

- **`ffmpeg` or `ffprobe` missing:** install FFmpeg and ensure both executables are on `PATH`; restart the terminal after changing PATH.
- **Deno not found:** install Deno and ensure it is on `PATH`; some YouTube extraction paths may fail or be less compatible without a supported JavaScript runtime.
- **Video information unavailable:** check the URL and network connection, update yt-dlp, and check yt-dlp's current documentation for extractor changes.
- **Video not supported or requires authentication:** TimbreDrop does not extract account cookies, collect credentials, bypass DRM, or circumvent access controls. Some videos cannot be handled.
- **Existing MP3:** the application chooses a numbered filename rather than silently replacing an existing file.
- **Invalid configuration:** edit or remove the reported `config.toml`; invalid individual values fall back to defaults.

## Development and tests

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
ruff check .
```

Tests are designed to run without contacting YouTube. Live extraction depends on YouTube and yt-dlp's current compatibility, so it should be tested manually with a video you have the right to download.

## Legal and privacy considerations

Users are responsible for complying with applicable copyright law, YouTube's Terms of Service, and the permissions or licenses attached to the content. Use the tool only where downloading is authorized or lawful. The application does not intentionally upload audio to a separate conversion service; yt-dlp connects to YouTube and the endpoints required to retrieve the selected stream. No account cookies or credentials are collected by TimbreDrop.

## License

TimbreDrop is released under the MIT License. See [LICENSE](LICENSE). Third-party dependencies retain their own licenses; see each upstream project's documentation, particularly [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org/legal.html).

## Packaging and distribution

### Standalone executables

The **Release binaries** workflow is manually dispatched from `main` with the existing version tag supplied as `release_tag` (for example, `v0.1.4`). It builds a console executable natively on Linux, Windows, and macOS, smoke-tests its version output, and attaches per-platform ZIP archives to the GitHub release. Native builds are used because PyInstaller executables are OS-specific; CPU architecture depends on the GitHub runner used by the workflow.

The packaged CLI includes Python, TimbreDrop, yt-dlp and its EJS companion package. **FFmpeg/FFprobe and Deno are external runtime requirements and are not bundled.** Install them with a trusted operating-system package manager and put them on `PATH`. Run the matching executable with `--version` to verify that it starts, then check `RUNTIME_REQUIREMENTS.txt` in the release archive. The current workflow builds Linux x86_64, Windows x86_64, macOS Intel x86_64, and macOS Apple Silicon arm64 assets.

The release archives include the project license, a third-party notice, and the third-party Python license files found during the release build. See `THIRD_PARTY_NOTICES.md`. Standalone ZIPs are published separately: the matching version tag must exist and the manual **Release binaries** workflow must complete successfully.

### Build a standalone executable locally

```bash
python -m pip install -e ".[freeze]"
python -m PyInstaller --noconfirm --clean --onefile --console \
  --name ytmp3 --paths src --specpath build/pyinstaller-spec \
  --workpath build/pyinstaller-work --distpath dist \
  --collect-all yt_dlp --collect-all yt_dlp_ejs \
  --copy-metadata yt-dlp --copy-metadata yt-dlp-ejs \
  scripts/ytmp3_entry.py
python scripts/smoke_executable.py
python scripts/collect_licenses.py
python scripts/package_release.py
```

Build separately on each target operating system; do not copy a Linux executable to Windows or macOS.

### Arch Linux package

See [`packaging/arch/README.md`](packaging/arch/README.md) and [`packaging/arch/PKGBUILD`](packaging/arch/PKGBUILD). The release steps and tag trigger are documented in [`packaging/RELEASING.md`](packaging/RELEASING.md). This is an unofficial local PKGBUILD, not a package in the official Arch repositories and not yet published to the AUR. Build and inspect it locally before considering an AUR submission.

### Cross-platform CI

`.github/workflows/ci.yml` runs the unit tests on Linux, Windows, and macOS with Python 3.11–3.13, and performs a lint and wheel-build check on the Ubuntu runner. Passing CI verifies the automated suite and package metadata, but is not a substitute for testing a real permitted video download on each operating system.
