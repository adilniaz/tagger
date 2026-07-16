from pathlib import Path
from PySide6.QtCore import Qt
from gui.file_table import (
    _FileRow, FileTableModel, _format_size, _format_mtime,
    COL_NAME, COL_SIZE, COL_MODIFIED, SORT_ROLE,
)


def test_format_size_bytes():
    assert _format_size(0) == "0 B"
    assert _format_size(500) == "500 B"
    assert _format_size(1024) == "1.0 KiB"
    assert _format_size(1536) == "1.5 KiB"
    assert _format_size(1048576) == "1.0 MiB"
    assert _format_size(1073741824) == "1.0 GiB"


def test_format_mtime():
    result = _format_mtime(1740000000.0)
    assert "at" in result
    assert len(result) > 0


def test_file_row_has_raw_numeric_attrs():
    p = Path("/tmp/test.mp3")
    row = _FileRow(path=p, size_bytes=1234567, mtime=1700000000.0,
                   size_str="1.2 MiB", mtime_str="1/1/23 at 12:00 PM")
    assert row.size_bytes == 1234567
    assert row.mtime == 1700000000.0
    assert row.size_str == "1.2 MiB"


def test_model_sort_role_returns_raw_values(qapp):
    model = FileTableModel()
    row = _FileRow(
        path=Path("/tmp/a.mp3"), size_bytes=1048576, mtime=1700000000.0,
        size_str="1.0 MiB", mtime_str="1/1/23 at 12:00 PM",
    )
    model.set_rows([row])
    idx = model.index(0, COL_SIZE)
    assert model.data(idx, SORT_ROLE) == 1048576
    assert model.data(model.index(0, COL_MODIFIED), SORT_ROLE) == 1700000000.0
    assert model.data(model.index(0, COL_NAME), SORT_ROLE) == "a.mp3"


def test_model_user_role_returns_path(qapp):
    model = FileTableModel()
    p = Path("/tmp/b.flac")
    model.set_rows([_FileRow(path=p)])
    idx = model.index(0, COL_NAME)
    assert model.data(idx, Qt.ItemDataRole.UserRole) == p


def test_model_dirty_paths(qapp):
    model = FileTableModel()
    p1 = Path("/tmp/a.mp3")
    p2 = Path("/tmp/b.mp3")
    model.set_rows([_FileRow(path=p1, dirty=True), _FileRow(path=p2, dirty=False)])
    dirty = model.dirty_paths()
    assert dirty == [p1]


def test_model_all_paths(qapp):
    model = FileTableModel()
    p1 = Path("/tmp/a.mp3")
    p2 = Path("/tmp/b.mp3")
    model.set_rows([_FileRow(path=p1), _FileRow(path=p2)])
    assert model.all_paths() == [p1, p2]
