import pytest

from timbredrop.urls import extract_video_id, validate_youtube_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=abc_DEF-123", "abc_DEF-123"),
        ("https://youtu.be/abc_DEF-123?t=30", "abc_DEF-123"),
        ("https://youtube.com/shorts/abc_DEF-123", "abc_DEF-123"),
        ("https://m.youtube.com/live/abc_DEF-123", "abc_DEF-123"),
        ("https://www.youtube-nocookie.com/embed/abc_DEF-123", "abc_DEF-123"),
    ],
)
def test_extract_supported_video_ids(url, expected):
    assert extract_video_id(url) == expected
    assert validate_youtube_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "ftp://youtube.com/watch?v=abc_DEF-123",
        "https://example.com/watch?v=abc_DEF-123",
        "https://youtube.com/watch",
        "https://youtube.com/playlist?list=PL123456789",
        "https://youtube.com/watch?v=bad/id",
        "https://user:pass@youtube.com/watch?v=abc_DEF-123",
        "https://youtube.com:8443/watch?v=abc_DEF-123",
    ],
)
def test_rejects_unsupported_url(url):
    with pytest.raises(ValueError):
        validate_youtube_url(url)
