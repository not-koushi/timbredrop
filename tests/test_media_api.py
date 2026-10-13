import sys
import types
from pathlib import Path

import pytest

from timbredrop.errors import TimbreDropError
from timbredrop.media import download_audio, fetch_video_info


class FakeDownloadError(Exception):
    pass


def install_fake_ytdlp(monkeypatch, fake_youtube_dl):
    module = types.ModuleType("yt_dlp")
    module.YoutubeDL = fake_youtube_dl
    module.__path__ = []
    utils = types.ModuleType("yt_dlp.utils")
    utils.DownloadError = FakeDownloadError
    monkeypatch.setitem(sys.modules, "yt_dlp", module)
    monkeypatch.setitem(sys.modules, "yt_dlp.utils", utils)


def test_fetch_video_info_calls_extractor_without_downloading(monkeypatch):
    calls = []

    class FakeYoutubeDL:
        def __init__(self, options):
            calls.append(("options", options))

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, url, download):
            calls.append(("extract", url, download))
            return {"title": "Example", "duration": 24}

    install_fake_ytdlp(monkeypatch, FakeYoutubeDL)
    info = fetch_video_info("https://youtu.be/abc_DEF-123")

    assert info["title"] == "Example"
    assert calls[0][1]["skip_download"] is True
    assert calls[0][1]["noplaylist"] is True
    assert calls[1] == ("extract", "https://youtu.be/abc_DEF-123", False)


def test_fetch_video_info_rejects_playlist_results(monkeypatch):
    class FakeYoutubeDL:
        def __init__(self, _options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, _url, download):
            return {"_type": "playlist", "entries": [{"id": "abc_DEF-123"}]}

    install_fake_ytdlp(monkeypatch, FakeYoutubeDL)
    with pytest.raises(TimbreDropError, match="Playlists are not supported"):
        fetch_video_info("https://youtu.be/abc_DEF-123")


def test_download_audio_uses_audio_format_and_returns_file(monkeypatch, tmp_path):
    hooks = []
    recorded_options = {}
    download_path = tmp_path / "source.webm"

    class FakeYoutubeDL:
        def __init__(self, options):
            recorded_options.update(options)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, _url, download):
            assert download is True
            output_pattern = Path(recorded_options["outtmpl"])
            target = Path(str(output_pattern).replace("%(ext)s", "webm"))
            target.write_bytes(b"fake audio bytes")
            download_path.parent.mkdir(parents=True, exist_ok=True)
            download_path.write_bytes(b"test")
            for hook in recorded_options.get("progress_hooks", []):
                hook({"status": "downloading", "downloaded_bytes": 4, "total_bytes": 4})
                hook({"status": "finished", "downloaded_bytes": 4, "total_bytes": 4})
            return {"title": "Example", "ext": "webm", "requested_downloads": [{"filepath": str(target)}]}

        def prepare_filename(self, _info):
            return str(download_path)

    install_fake_ytdlp(monkeypatch, FakeYoutubeDL)
    progress_events = []
    result, info = download_audio(
        "https://youtu.be/abc_DEF-123",
        tmp_path / "work",
        progress_events.append,
    )

    assert result == tmp_path / "work" / "source.webm"
    assert result.read_bytes() == b"fake audio bytes"
    assert info["title"] == "Example"
    assert recorded_options["format"] == "bestaudio/best"
    assert recorded_options["noplaylist"] is True
    assert progress_events[0]["status"] == "downloading"
    assert progress_events[1]["status"] == "finished"
