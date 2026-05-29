import pytest
from core.settings import Settings, EXTENDED_FIELDS


def test_default_settings_have_no_extended_fields():
    s = Settings()
    assert s.enabled_extended == set()


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    config = tmp_path / "settings.json"
    monkeypatch.setattr("core.settings.CONFIG_PATH", config)

    s = Settings(enabled_extended={"albumartist", "composer"})
    s.save()

    loaded = Settings.load()
    assert loaded.enabled_extended == {"albumartist", "composer"}


def test_load_returns_defaults_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("core.settings.CONFIG_PATH", tmp_path / "missing.json")
    s = Settings.load()
    assert s.enabled_extended == set()


def test_save_creates_parent_directories(tmp_path, monkeypatch):
    config = tmp_path / "nested" / "dir" / "settings.json"
    monkeypatch.setattr("core.settings.CONFIG_PATH", config)
    Settings(enabled_extended={"composer"}).save()
    assert config.exists()


def test_extended_fields_constant_contains_expected_keys():
    assert "albumartist" in EXTENDED_FIELDS
    assert "discnumber" in EXTENDED_FIELDS
    assert "composer" in EXTENDED_FIELDS
    assert "comment" in EXTENDED_FIELDS
    assert "lyrics" in EXTENDED_FIELDS
