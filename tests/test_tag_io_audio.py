from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from core.tag_io import read, write, SUPPORTED_EXTENSIONS, BASIC_FIELDS, FIELD_LABELS


def _mock_mutagen(tags: dict):
    m = MagicMock()
    store = dict(tags)
    m.get.side_effect = lambda k, default=None: [store[k]] if k in store else default
    m.__contains__ = lambda self, k: k in store
    m.__setitem__ = lambda self, k, v: store.update({k: v})
    m.__delitem__.side_effect = lambda k: store.pop(k, None)
    m.save = MagicMock()
    return m


def test_read_returns_basic_tags():
    mock_file = _mock_mutagen({"title": "Song", "artist": "Band", "album": "Record"})
    with patch("core.tag_io.MutagenFile", return_value=mock_file):
        result = read(Path("track.mp3"))
    assert result["title"] == "Song"
    assert result["artist"] == "Band"
    assert result["album"] == "Record"


def test_read_returns_empty_dict_for_missing_tags():
    mock_file = _mock_mutagen({})
    with patch("core.tag_io.MutagenFile", return_value=mock_file):
        result = read(Path("track.flac"))
    assert result == {}


def test_read_returns_empty_dict_when_mutagen_returns_none():
    with patch("core.tag_io.MutagenFile", return_value=None):
        result = read(Path("track.mp3"))
    assert result == {}


def test_write_calls_save():
    mock_file = _mock_mutagen({})
    with patch("core.tag_io.MutagenFile", return_value=mock_file):
        write(Path("track.mp3"), {"title": "New Title", "artist": "New Artist"})
    mock_file.save.assert_called_once()


def test_write_deletes_empty_tags():
    mock_file = _mock_mutagen({"title": "Old"})
    with patch("core.tag_io.MutagenFile", return_value=mock_file):
        write(Path("track.mp3"), {"title": ""})
    mock_file.__delitem__.assert_called_with("title")


def test_read_raises_for_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported"):
        read(Path("file.xyz"))


def test_write_raises_when_mutagen_returns_none():
    with patch("core.tag_io.MutagenFile", return_value=None):
        with pytest.raises(IOError):
            write(Path("track.mp3"), {"title": "x"})


def test_supported_extensions_includes_common_audio():
    for ext in (".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wma",
                ".wav", ".aiff", ".aif", ".ape", ".wv", ".mpc"):
        assert ext in SUPPORTED_EXTENSIONS


def test_basic_fields_has_six_entries():
    assert len(BASIC_FIELDS) == 6


def test_field_labels_has_label_for_each_basic_field():
    for f in BASIC_FIELDS:
        assert f in FIELD_LABELS
