import pytest

from timbredrop.media import (
    _candidate_output_path,
    _publish_without_overwrite,
    format_bytes,
    format_duration,
    sanitize_filename,
)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("../outside/path", ".._outside_path"),
        ('question: "bad"/name?', "question_ _bad__name_"),
        ("CON", "_CON"),
        (".  ", "video"),
        ("\n\t", "video"),
        (None, "video"),
    ],
)
def test_sanitize_filename(title, expected):
    assert sanitize_filename(title) == expected


def test_sanitize_filename_caps_length():
    assert len(sanitize_filename("x" * 300)) == 160


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(None, "unknown"), (59, "0:59"), (61, "1:01"), (3661, "1:01:01")],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


def test_format_bytes():
    assert format_bytes(1024) == "1.0 KiB"
    assert format_bytes(12) == "12 B"


def test_candidate_output_path_avoids_existing_files(tmp_path):
    (tmp_path / "Track.mp3").write_bytes(b"existing")
    assert _candidate_output_path(tmp_path, "Track") == tmp_path / "Track (2).mp3"


def test_publish_never_overwrites_existing_file(tmp_path):
    existing = tmp_path / "Track.mp3"
    existing.write_bytes(b"keep this file")
    temporary = tmp_path / ".temporary.mp3"
    temporary.write_bytes(b"new audio")

    published = _publish_without_overwrite(temporary, tmp_path, "Track")

    assert published == tmp_path / "Track (2).mp3"
    assert existing.read_bytes() == b"keep this file"
    assert published.read_bytes() == b"new audio"
    assert not temporary.exists()
