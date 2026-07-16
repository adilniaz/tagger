from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox,
    QSplitter, QToolBar,
)

from core.tag_io import (
    BASIC_FIELDS, EXTENDED_FIELDS, FIELD_LABELS, SUPPORTED_EXTENSIONS, read, write,
)
from core.settings import Settings
from gui.batch_edit_dialog import BatchEditDialog
from gui.file_table import FileTable
from gui.settings_dialog import SettingsDialog
from gui.tag_editor import TagEditorPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Tagger")
        self.resize(1200, 700)

        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_action = QAction("Open Folder", self)
        open_action.setShortcut(QKeySequence("Ctrl+B"))
        open_action.triggered.connect(self._open_folder)
        toolbar.addAction(open_action)

        open_files_action = QAction("Open File(s)", self)
        open_files_action.setShortcut(QKeySequence("Ctrl+O"))
        open_files_action.triggered.connect(self._open_files)
        toolbar.addAction(open_files_action)

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save)
        toolbar.addAction(save_action)

        batch_action = QAction("Batch Edit", self)
        batch_action.setShortcut(QKeySequence("Ctrl+E"))
        batch_action.triggered.connect(self._batch_edit)
        toolbar.addAction(batch_action)

        settings_action = QAction("Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(QApplication.quit)
        toolbar.addAction(quit_action)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._file_table = FileTable()
        self._tag_editor = TagEditorPanel()
        splitter.addWidget(self._file_table)
        splitter.addWidget(self._tag_editor)
        splitter.setSizes([720, 480])
        self.setCentralWidget(splitter)

        self._file_table.selection_changed.connect(self._on_selection_changed)
        self._tag_editor.dirty_changed.connect(
            lambda path, dirty: self._file_table.set_dirty(path, dirty)
        )
        self._tag_editor.file_saved.connect(self._file_table.set_clean)
        self._tag_editor.file_renamed.connect(self._file_table.rename_path)

        self._select_timer = QTimer(self)
        self._select_timer.setSingleShot(True)
        self._select_timer.setInterval(150)
        self._select_timer.timeout.connect(self._do_load_selection)
        self._pending_paths: list[Path] = []

    def _do_load_selection(self) -> None:
        paths = self._pending_paths
        self._pending_paths = []
        if not paths:
            self._tag_editor.clear()
        elif len(paths) == 1:
            self._tag_editor.load(paths[0])
        else:
            self._tag_editor.load_multi(paths)

    def _open_folder(self) -> None:
        if not self._confirm_discard():
            return
        folder = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder:
            self._tag_editor.clear_cache()
            self._file_table.load(Path(folder))

    def _open_files(self) -> None:
        if not self._confirm_discard():
            return
        exts = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTENSIONS))
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open File(s)", "", f"Supported files ({exts});;All files (*)"
        )
        if paths:
            self._tag_editor.clear_cache()
            self._file_table.load_files([Path(p) for p in paths])

    def _save(self) -> None:
        self._tag_editor.save()

    def _on_selection_changed(self, paths: list[Path]) -> None:
        self._pending_paths = list(paths)
        self._select_timer.start()

    def _confirm_discard(self) -> bool:
        dirty = self._file_table.dirty_paths()
        if not dirty:
            return True
        names = "\n".join(f"  • {p.name}" for p in dirty[:5])
        if len(dirty) > 5:
            names += f"\n  … and {len(dirty) - 5} more"
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            f"Discard unsaved changes in {len(dirty)} "
            f"file{'s' if len(dirty) != 1 else ''}?\n\n{names}",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
        )
        return reply == QMessageBox.StandardButton.Discard

    def _batch_edit(self) -> None:
        settings = Settings.load()
        active_fields = BASIC_FIELDS + [
            f for f in EXTENDED_FIELDS if f in settings.enabled_extended
        ]
        dialog = BatchEditDialog(active_fields, FIELD_LABELS, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.get_values()
        if not values:
            return
        targets = self._file_table.selected_paths() or self._file_table.all_paths()
        errors: list[str] = []
        for p in targets:
            try:
                tags = read(p)
                tags.update(values)
                write(p, tags)
                self._file_table.set_clean(p)
                self._file_table.update_tags(p, tags)
            except Exception as e:
                errors.append(f"{p.name}: {e}")
        if errors:
            QMessageBox.warning(self, "Batch Edit Errors", "\n".join(errors))
        current = self._tag_editor.current_path
        if current and current in set(targets):
            self._tag_editor.load(current)

    def _open_settings(self) -> None:
        SettingsDialog(self).exec()
        self._tag_editor.reload_settings()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if not self._confirm_discard():
            event.ignore()
            return
        self._file_table.shutdown()
        event.accept()
