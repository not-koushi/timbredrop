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

## Requirements

- Python 3.11 or newer.
- FFmpeg with `libmp3lame` support and `ffprobe`, available on `PATH`.
- A supported JavaScript runtime for current yt-dlp YouTube extraction. [Deno](https://deno.com/) is recommended.
- Network access to the video and to the endpoints required by yt-dlp.

YouTube extraction can change over time. The latest yt-dlp version, its default EJS companion package, and a compatible JavaScript runtime improve compatibility but cannot guarantee that every video is accessible. See the [yt-dlp project](https://github.com/yt-dlp/yt-dlp) and [EJS guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS) for current requirements.

## Install from source

### Arch Linux

```bash
sudo pacman -Syu --needed git python python-pip ffmpeg deno

git clone https://github.com/not-koushi/timbredrop.git
cd timbredrop
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
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

```bash
ytmp3
```

The actual command contains no spaces: `ytmp3`.

1. Enter a supported YouTube video URL. Press Enter on an empty line to exit.
2. Review the video's title and duration. Long or unknown durations require confirmation.
3. Choose an output bitrate. Press Enter to accept the configured default (256 kbps).
4. Wait for download and conversion progress. The completed file path and file size are printed at the end.

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

An empty `output_dir` uses the user's Downloads directory under a `TimbreDrop` folder. `default_bitrate` must be `96`, `128`, `160`, or `256`. Invalid values fall back to defaults with a warning.

## Audio quality and bitrate

The selected bitrate is the output MP3's CBR target; it does **not** describe or improve the original YouTube stream. YouTube commonly delivers audio in lossy formats such as Opus or AAC. Converting those streams to MP3 is another lossy encoding step, and encoding at 256 kbps cannot restore information that was already discarded upstream. The 256 kbps default prioritizes a higher MP3 output bitrate, not a guarantee of higher fidelity than the source.

## Platform verification status

Linux unit tests and an FFmpeg MP3-encoding smoke test have been run in the development environment. YouTube extraction has not yet been live-tested from the maintainers' environment. Windows and macOS are not yet verified; do not treat their install instructions as a tested release. Cross-platform CI and packaged binaries are planned for later phases.

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
