from timbredrop.config import ALLOWED_BITRATES, default_config, load_config, write_default_config


def test_missing_config_uses_defaults(tmp_path):
    config, warnings = load_config(tmp_path / "missing.toml")
    assert config == default_config()
    assert warnings == []


def test_valid_config_loads_values(tmp_path):
    path = tmp_path / "config.toml"
    output_dir = tmp_path / "audio"
    path.write_text(
        f'output_dir = "{output_dir.as_posix()}"\n'
        "default_bitrate = 160\n"
        "duration_warning_minutes = 45\n"
        "preserve_metadata = false\n",
        encoding="utf-8",
    )
    config, warnings = load_config(path)
    assert config.output_dir == output_dir
    assert config.default_bitrate == 160
    assert config.duration_warning_minutes == 45
    assert config.preserve_metadata is False
    assert warnings == []


def test_invalid_fields_fall_back_individually(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_text('default_bitrate = 192\nduration_warning_minutes = 0\npreserve_metadata = "yes"\n')
    config, warnings = load_config(path)
    assert config.default_bitrate == 256
    assert config.duration_warning_minutes == 30
    assert config.preserve_metadata is True
    assert len(warnings) == 3


def test_malformed_toml_falls_back_to_defaults(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_text("default_bitrate = [", encoding="utf-8")
    config, warnings = load_config(path)
    assert config == default_config()
    assert len(warnings) == 1


def test_write_config_does_not_overwrite(tmp_path):
    path = tmp_path / "config.toml"
    created = write_default_config(path)
    assert created == path
    assert "default_bitrate = 256" in path.read_text(encoding="utf-8")
    try:
        write_default_config(path)
    except FileExistsError:
        pass
    else:
        raise AssertionError("write_default_config must not overwrite an existing file")


def test_allowed_bitrates_are_expected():
    assert ALLOWED_BITRATES == (96, 128, 160, 256)
