from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import datetime
from typing import Any

from PySide6.QtCore import (
    Qt, QAbstractTableModel, QItemSelection, QModelIndex, QPersistentModelIndex,
    QThread, Signal, QSortFilterProxyModel,
)
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QTableView, QVBoxLayout, QHeaderView

from core.tag_io import read, SUPPORTED_EXTENSIONS, AUDIO_EXTENSIONS

COL_ICON = 0
COL_NAME = 1
COL_SIZE = 2
COL_TITLE = 3
COL_MODIFIED = 4
COL_ARTIST = 5
COL_ALBUM = 6
NUM_COLS = 7
HEADERS = ["", "Name", "Size", "Title", "Modified", "Artist", "Album"]


@dataclass
class _FileRow:
    path: Path
    size_str: str = ""
    mtime_str: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    dirty: bool = False


class TagLoaderThread(QThread):
    tags_loaded = Signal(Path, dict)

    def __init__(self, paths: list[Path], parent: QWidget | None = None):
        super().__init__(parent)
        self._paths = paths

    def run(self) -> None:
        for path in self._paths:
            try:
                tags = read(path)
            except Exception:
                tags = {}
            self.tags_loaded.emit(path, tags)


class FileTableModel(QAbstractTableModel):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._rows: list[_FileRow] = []
        self._path_index: dict[Path, int] = {}

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return NUM_COLS

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return HEADERS[section]
        return None

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == COL_ICON:
                return "♪" if row.path.suffix.lower() in AUDIO_EXTENSIONS else "📖"
            if col == COL_NAME:
                return f"* {row.path.name}" if row.dirty else row.path.name
            if col == COL_SIZE:
                return row.size_str
            if col == COL_TITLE:
                return row.title
            if col == COL_MODIFIED:
                return row.mtime_str
            if col == COL_ARTIST:
                return row.artist
            if col == COL_ALBUM:
                return row.album

        if role == Qt.ItemDataRole.FontRole and col == COL_NAME and row.dirty:
            font = QFont()
            font.setBold(True)
            return font

        if role == Qt.ItemDataRole.UserRole:
            return row.path

        return None

    def set_rows(self, rows: list[_FileRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self._path_index = {r.path: i for i, r in enumerate(rows)}
        self.endResetModel()

    def update_tags(self, path: Path, tags: dict) -> None:
        idx = self._path_index.get(path)
        if idx is None:
            return
        row = self._rows[idx]
        row.title = tags.get("title", "")
        row.artist = tags.get("artist", "")
        row.album = tags.get("album", "")
        self.dataChanged.emit(self.index(idx, COL_TITLE), self.index(idx, COL_ALBUM))

    def set_dirty(self, path: Path, dirty: bool) -> None:
        idx = self._path_index.get(path)
        if idx is None:
            return
        self._rows[idx].dirty = dirty
        name_idx = self.index(idx, COL_NAME)
        self.dataChanged.emit(name_idx, name_idx)

    def all_paths(self) -> list[Path]:
        return [r.path for r in self._rows]

    def dirty_paths(self) -> list[Path]:
        return [r.path for r in self._rows if r.dirty]


class FileTable(QWidget):
    selection_changed = Signal(list)  # list[Path]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._model = FileTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)

        self._view = QTableView()
        self._view.setModel(self._proxy)
        self._view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self._view.setSortingEnabled(True)
        self._view.verticalHeader().setVisible(False)
        self._view.setShowGrid(False)
        self._view.setAlternatingRowColors(True)

        hdr = self._view.horizontalHeader()
        hdr.setSectionResizeMode(COL_ICON, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_TITLE, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(COL_MODIFIED, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_ARTIST, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(COL_ALBUM, QHeaderView.ResizeMode.Interactive)
        hdr.setDefaultSectionSize(150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        self._view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._loader: TagLoaderThread | None = None
        self._ignore_selection = False

    def load(self, path: Path) -> None:
        if path.is_dir():
            paths = sorted(
                p for p in path.iterdir()
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
            )
        elif path.suffix.lower() in SUPPORTED_EXTENSIONS:
            paths = [path]
        else:
            paths = []

        rows: list[_FileRow] = []
        for p in paths:
            try:
                stat = p.stat()
                size_str = _format_size(stat.st_size)
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
                mtime_str = mtime.strftime("%-m/%-d/%y at %-I:%M %p")
            except OSError:
                size_str = ""
                mtime_str = ""
            rows.append(_FileRow(path=p, size_str=size_str, mtime_str=mtime_str))

        self._model.set_rows(rows)

        self._loader = TagLoaderThread(paths, self)
        self._loader.tags_loaded.connect(self._model.update_tags)
        self._loader.start()

    def set_dirty(self, path: Path, dirty: bool) -> None:
        self._model.set_dirty(path, dirty)

    def set_clean(self, path: Path) -> None:
        self._model.set_dirty(path, False)

    def update_tags(self, path: Path, tags: dict) -> None:
        self._model.update_tags(path, tags)

    def load_files(self, paths: list[Path]) -> None:
        rows: list[_FileRow] = []
        for p in paths:
            if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            try:
                stat = p.stat()
                size_str = _format_size(stat.st_size)
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
                mtime_str = mtime.strftime("%-m/%-d/%y at %-I:%M %p")
            except OSError:
                size_str = ""
                mtime_str = ""
            rows.append(_FileRow(path=p, size_str=size_str, mtime_str=mtime_str))
        self._model.set_rows(rows)
        self._loader = TagLoaderThread([r.path for r in rows], self)
        self._loader.tags_loaded.connect(self._model.update_tags)
        self._loader.start()

    def all_paths(self) -> list[Path]:
        return self._model.all_paths()

    def dirty_paths(self) -> list[Path]:
        return self._model.dirty_paths()

    def select_paths(self, paths: list[Path]) -> None:
        self._ignore_selection = True
        try:
            path_set = set(paths)
            selection = QItemSelection()
            for row in range(self._model.rowCount()):
                idx = self._model.index(row, 0)
                if self._model.data(idx, Qt.ItemDataRole.UserRole) in path_set:
                    proxy_idx = self._proxy.mapFromSource(idx)
                    last_col = self._proxy.index(proxy_idx.row(), NUM_COLS - 1)
                    selection.select(proxy_idx, last_col)
            self._view.selectionModel().select(
                selection, QItemSelectionModel.SelectionFlag.ClearAndSelect
            )
        finally:
            self._ignore_selection = False

    def _on_selection_changed(self) -> None:
        if self._ignore_selection:
            return
        indexes = self._view.selectionModel().selectedRows()
        paths = []
        for proxy_idx in indexes:
            source_idx = self._proxy.mapToSource(proxy_idx)
            path = self._model.data(source_idx, Qt.ItemDataRole.UserRole)
            if path:
                paths.append(path)
        if paths:
            self.selection_changed.emit(paths)


def _format_size(size: int) -> str:
    fsize: float = size
    for unit in ("B", "KiB", "MiB", "GiB"):
        if fsize < 1024:
            return f"{fsize:.0f} {unit}" if unit == "B" else f"{fsize:.1f} {unit}"
        fsize /= 1024
    return f"{fsize:.1f} TiB"
