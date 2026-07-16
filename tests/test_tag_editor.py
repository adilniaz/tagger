from pathlib import Path
from gui.tag_editor import _filename_error


def test_filename_error_rejects_empty():
    assert _filename_error("", "old.mp3", Path("/tmp")) is not None


def test_filename_error_rejects_separators():
    assert _filename_error("a/b.mp3", "old.mp3", Path("/tmp")) is not None
    assert _filename_error("../evil.mp3", "old.mp3", Path("/tmp")) is not None
    assert _filename_error("..", "old.mp3", Path("/tmp")) is not None
    assert _filename_error(".", "old.mp3", Path("/tmp")) is not None


def test_filename_error_rejects_existing_file(tmp_path):
    existing = tmp_path / "exists.mp3"
    existing.write_text("")
    error = _filename_error("exists.mp3", "other.mp3", tmp_path)
    assert error is not None
    assert "already exists" in error


def test_filename_error_accepts_valid_rename(tmp_path):
    assert _filename_error("new.mp3", "old.mp3", tmp_path) is None
    existing = tmp_path / "exists.mp3"
    existing.write_text("")
    assert _filename_error("exists.mp3", "exists.mp3", tmp_path) is None


def test_current_path_returns_none_when_empty(qapp):
    from gui.tag_editor import TagEditorPanel
    panel = TagEditorPanel()
    assert panel.current_path is None
