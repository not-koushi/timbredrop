# Third-party notices for TimbreDrop binary releases

TimbreDrop's own source code is licensed under the MIT License; see `LICENSE`.

The PyInstaller release bundle includes Python packages used by this application, notably:

- **yt-dlp** — Unlicense. <https://github.com/yt-dlp/yt-dlp>
- **yt-dlp-ejs** — Unlicense with third-party MIT- and ISC-licensed components. <https://github.com/yt-dlp/ejs>
- **platformdirs** — MIT. <https://github.com/tox-dev/platformdirs>
- Additional dependencies installed through `yt-dlp[default]`, each subject to its own license.

The release workflow collects available license/copying/notice files from known runtime Python distributions into `THIRD_PARTY_LICENSES/` inside each release ZIP. `THIRD_PARTY_LICENSES/MANIFEST.txt` identifies the package versions and inventory at build time. These notices supplement, and do not replace, the upstream license terms.

FFmpeg/FFprobe and Deno are **not bundled** with these release archives. Users install them separately, so their license files are not redistributed as part of the TimbreDrop binary archive. FFmpeg's license depends on the build/distribution selected; see <https://ffmpeg.org/legal.html>. Deno's licensing is documented at <https://github.com/denoland/deno>.

TimbreDrop is independently developed and is not affiliated with or endorsed by YouTube. The software must only be used where the user has permission or a lawful basis to download the content.
