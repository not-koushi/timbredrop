import pytest

from timbredrop import cli
from timbredrop.config import AppConfig
from timbredrop.config import load_config as real_load_config


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


def _stub_startup(monkeypatch, tmp_path):
    output_dir = tmp_path / "audio"
    config = AppConfig(output_dir=output_dir, default_bitrate=256, duration_warning_minutes=30)
    monkeypatch.setattr(cli, "load_config", lambda: (config, []))
    monkeypatch.setattr(cli, "check_dependencies", lambda: ("/usr/bin/ffmpeg", "/usr/bin/ffprobe"))
    monkeypatch.setattr(
        cli.shutil,
        "which",
        lambda name: "/usr/bin/deno" if name == "deno" else f"/usr/bin/{name}",
    )
    return output_dir


def test_main_processes_more_than_one_url(monkeypatch, tmp_path, capsys):
    output_dir = _stub_startup(monkeypatch, tmp_path)
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
            "url https://youtu.be/first123",
            "96",
            "url https://youtu.be/second1",
            "3",
            "exit",
        ]
    )
    prompts = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or next(answers))

    assert cli.main([]) == 0
    output = capsys.readouterr().out
    assert output.count("Success: MP3 created") == 2
    assert "Output bitrate: 96 kbps CBR" in output
    assert "Output bitrate: 160 kbps CBR" in output
    assert "Enter YouTube URL" not in output
    assert output.index("url <link>") < output.index("TimbreDrop")
    assert prompts[0].startswith("(>_ ytmp3)")
    assert (output_dir / "First.mp3").exists()
    assert (output_dir / "Second.mp3").exists()


def test_shell_lists_commands_and_exits(monkeypatch, tmp_path, capsys):
    _stub_startup(monkeypatch, tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "exit")

    assert cli.main([]) == 0
    output = capsys.readouterr().out
    assert "url <link>" in output
    assert "path" in output
    assert "exit" in output
    assert "Use only content you own" in output
    assert "Goodbye." in output


def test_url_command_requires_an_argument(monkeypatch, tmp_path, capsys):
    _stub_startup(monkeypatch, tmp_path)
    answers = iter(["url", "exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert cli.main([]) == 0
    assert "Usage: url <YouTube-URL>" in capsys.readouterr().out


def test_path_command_opens_config_and_reloads_new_output_path(monkeypatch, tmp_path, capsys):
    config_file = tmp_path / "config.toml"
    new_output = tmp_path / "new-audio"
    monkeypatch.setattr(cli, "config_path", lambda: config_file)
    monkeypatch.setattr(cli, "load_config", lambda: real_load_config(config_file))
    monkeypatch.setattr(cli, "check_dependencies", lambda: ("/usr/bin/ffmpeg", "/usr/bin/ffprobe"))
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_open(path):
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace('output_dir = ""', f'output_dir = "{new_output.as_posix()}"'),
            encoding="utf-8",
        )
        return True

    monkeypatch.setattr(cli, "_open_config_file", fake_open)
    answers = iter(["path", "y", "exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert cli.main([]) == 0
    output = capsys.readouterr().out
    assert f"Opening configuration file: {config_file}" in output
    assert f"Output directory updated: {new_output}" in output
    assert f'output_dir = "{new_output.as_posix()}"' in config_file.read_text(encoding="utf-8")


def test_show_config_prints_path_without_external_dependencies(monkeypatch, capsys, tmp_path):
    expected = tmp_path / "config.toml"
    monkeypatch.setattr(cli, "config_path", lambda: expected)
    assert cli.main(["--show-config"]) == 0
    assert capsys.readouterr().out.strip() == str(expected)


def test_safe_terminal_text_removes_control_characters():
    assert cli._safe_terminal_text("title\x1b[31m\nnext") == "title[31mnext"


def test_color_respects_no_color_environment(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert cli._color("hello", cli.CYAN) == "hello"


@pytest.mark.parametrize("platform_name", ["linux", "freebsd"])
def test_system_default_uses_desktop_file_association_on_unix(monkeypatch, tmp_path, platform_name):
    target = tmp_path / "config.toml"
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    launched = []
    monkeypatch.setattr(
        cli.shutil,
        "which",
        lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None,
    )
    monkeypatch.setattr(
        cli.subprocess,
        "Popen",
        lambda args, **kwargs: launched.append((args, kwargs)),
    )

    assert cli._open_with_system_default(
        target, operating_system="posix", platform_name=platform_name
    ) is True
    assert launched[0][0] == ["/usr/bin/xdg-open", str(target)]
    assert launched[0][1]["start_new_session"] is True


def test_system_default_uses_macos_text_editor(monkeypatch, tmp_path):
    target = tmp_path / "config.toml"
    launched = []
    monkeypatch.setattr(
        cli.shutil, "which", lambda name: "/usr/bin/open" if name == "open" else None
    )
    monkeypatch.setattr(cli.subprocess, "Popen", lambda args, **kwargs: launched.append(args))

    assert cli._open_with_system_default(
        target, operating_system="posix", platform_name="darwin"
    ) is True
    assert launched == [["/usr/bin/open", "-t", str(target)]]


def test_system_default_uses_windows_file_association(monkeypatch, tmp_path):
    target = tmp_path / "config.toml"
    opened = []
    monkeypatch.setattr(cli.os, "startfile", lambda value: opened.append(value), raising=False)

    assert cli._open_with_system_default(
        target, operating_system="nt", platform_name="win32"
    ) is True
    assert opened == [str(target)]


def test_path_editor_prefers_os_default_over_legacy_editor_variable(monkeypatch, tmp_path):
    target = tmp_path / "config.toml"
    monkeypatch.delenv("TIMBREDROP_EDITOR", raising=False)
    monkeypatch.setenv("EDITOR", "nano")
    monkeypatch.setenv("DISPLAY", ":0")
    opened = []
    monkeypatch.setattr(cli, "_open_with_system_default", lambda path: opened.append(path) or True)
    monkeypatch.setattr(
        cli.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("EDITOR should not win")
    )

    assert cli._open_config_file(target) is True
    assert opened == [target]


def test_timbredrop_editor_environment_override_has_priority(monkeypatch, tmp_path):
    target = tmp_path / "config.toml"
    monkeypatch.setenv("TIMBREDROP_EDITOR", "custom-editor --wait")
    monkeypatch.setenv("EDITOR", "nano")
    calls = []
    monkeypatch.setattr(
        cli,
        "_open_with_system_default",
        lambda _path: pytest.fail("OS default should not win"),
    )
    monkeypatch.setattr(
        cli.shutil,
        "which",
        lambda name: "/usr/bin/custom-editor" if name == "custom-editor" else None,
    )
    monkeypatch.setattr(cli.subprocess, "run", lambda args, **kwargs: calls.append(args))

    assert cli._open_config_file(target) is True
    assert calls == [["/usr/bin/custom-editor", "--wait", str(target)]]


def test_editor_environment_is_fallback_for_headless_session(monkeypatch, tmp_path):
    target = tmp_path / "config.toml"
    monkeypatch.delenv("TIMBREDROP_EDITOR", raising=False)
    monkeypatch.setenv("EDITOR", "nano")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    calls = []
    monkeypatch.setattr(cli, "_open_with_system_default", lambda _path: False)
    monkeypatch.setattr(
        cli.shutil, "which", lambda name: "/usr/bin/nano" if name == "nano" else None
    )
    monkeypatch.setattr(cli.subprocess, "run", lambda args, **kwargs: calls.append(args))

    assert cli._open_config_file(target) is True
    assert calls == [["/usr/bin/nano", str(target)]]
