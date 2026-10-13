import pytest

from timbredrop import cli
from timbredrop.config import AppConfig


def test_choose_bitrate_accepts_exact_value(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "160")
    assert cli._choose_bitrate(256) == 160


def test_choose_bitrate_accepts_numbered_choice(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "3")
    assert cli._choose_bitrate(256) == 160


def test_choose_bitrate_defaults_on_empty_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    assert cli._choose_bitrate(128) == 128


def test_duration_under_threshold_does_not_prompt(monkeypatch):
    def unexpected_prompt(*_args, **_kwargs):
        raise AssertionError("duration within threshold should not prompt")

    monkeypatch.setattr(cli, "_yes_no", unexpected_prompt)
    assert cli._check_duration({"title": "Short", "duration": 1800}, 30) is True


def test_long_duration_requires_confirmation(monkeypatch):
    monkeypatch.setattr(cli, "_yes_no", lambda *_args, **_kwargs: False)
    assert cli._check_duration({"title": "Long", "duration": 1801}, 30) is False


@pytest.mark.parametrize("duration", [None, 0])
def test_unknown_duration_requires_confirmation(monkeypatch, duration):
    prompts = []
    monkeypatch.setattr(cli, "_yes_no", lambda prompt, **_kwargs: prompts.append(prompt) or True)
    assert cli._check_duration({"title": "Unknown", "duration": duration}, 30) is True
    assert prompts == ["Continue anyway?"]


def test_main_processes_more_than_one_url(monkeypatch, tmp_path, capsys):
    output_dir = tmp_path / "audio"
    config = AppConfig(output_dir=output_dir, default_bitrate=256, duration_warning_minutes=30)
    monkeypatch.setattr(cli, "load_config", lambda: (config, []))
    monkeypatch.setattr(cli, "check_dependencies", lambda: ("/usr/bin/ffmpeg", "/usr/bin/ffprobe"))
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/deno" if name == "deno" else f"/usr/bin/{name}")
    monkeypatch.setattr(
        cli,
        "fetch_video_info",
        lambda url: {"title": "First" if "first" in url else "Second", "duration": 15},
    )

    def fake_process(url, info, bitrate, output, preserve):
        output.mkdir(parents=True, exist_ok=True)
        path = output / f"{info['title']}.mp3"
        path.write_bytes(f"{bitrate}:{preserve}".encode())
        return path

    monkeypatch.setattr(cli, "_process_one", fake_process)
    answers = iter(
        [
            "https://youtu.be/first123",
            "96",
            "https://youtu.be/second1",
            "3",
            "",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert cli.main([]) == 0
    output = capsys.readouterr().out
    assert output.count("Success: MP3 created") == 2
    assert "Output bitrate: 96 kbps CBR" in output
    assert "Output bitrate: 160 kbps CBR" in output
    assert (output_dir / "First.mp3").exists()
    assert (output_dir / "Second.mp3").exists()


def test_show_config_prints_path_without_external_dependencies(monkeypatch, capsys, tmp_path):
    expected = tmp_path / "config.toml"
    monkeypatch.setattr(cli, "config_path", lambda: expected)
    assert cli.main(["--show-config"]) == 0
    assert capsys.readouterr().out.strip() == str(expected)


def test_safe_terminal_text_removes_control_characters():
    assert cli._safe_terminal_text("title\x1b[31m\nnext") == "title[31mnext"
