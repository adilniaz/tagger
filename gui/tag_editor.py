from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFormLayout, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from core.tag_io import BASIC_FIELDS, EXTENDED_FIELDS, FIELD_LABELS, read, write
from core.settings import Settings


class TagEditorPanel(QWidget):
    dirty_changed = Signal(Path, bool)
    file_saved = Signal(Path)
    file_renamed = Signal(Path, Path)   # old_path, new_path

    _paths: list[Path]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._paths = []
        self._multi = False
        self._original: dict[str, str] = {}
        self._filename_original = ""
        self._inputs: dict[str, QLineEdit] = {}
        # Cache: path → (filename_text, tag_values); survives file-switch without saving
        self._edit_cache: dict[Path, tuple[str, dict[str, str]]] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        self._form_widget = QWidget()
        self._form_layout = QFormLayout(self._form_widget)
        self._form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        scroll.setWidget(self._form_widget)

        self._save_btn = QPushButton("Save  Ctrl+S")
        self._save_btn.setEnabled(False)
        self._save_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._save_btn.clicked.connect(self.save)
        outer.addWidget(self._save_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._rebuild()

    @property
    def current_path(self) -> Path | None:
        return self._paths[0] if self._paths else None

    def _rebuild(self) -> None:
        self._inputs.clear()
        while self._form_layout.rowCount() > 0:
            self._form_layout.removeRow(0)

        # Filename field — always first
        self._filename_input = QLineEdit()
        self._filename_input.setEnabled(bool(self._paths) and not self._multi)
        self._filename_input.textChanged.connect(self._on_text_changed)
        self._form_layout.addRow("File name:", self._filename_input)

        settings = Settings.load()
        active_fields = BASIC_FIELDS + [
            f for f in EXTENDED_FIELDS if f in settings.enabled_extended
        ]
        for field in active_fields:
            label = FIELD_LABELS.get(field, field.title())
            inp = QLineEdit()
            inp.setEnabled(bool(self._paths))
            inp.textChanged.connect(self._on_text_changed)
            self._inputs[field] = inp
            self._form_layout.addRow(label + ":", inp)

    def _on_text_changed(self) -> None:
        if self._paths:
            dirty = self.is_dirty
            for p in self._paths:
                self.dirty_changed.emit(p, dirty)
            self._save_btn.setEnabled(dirty)

    @property
    def is_dirty(self) -> bool:
        if not self._multi and self._filename_input.text() != self._filename_original:
            return True
        return any(
            self._inputs[f].text() != self._original.get(f, "")
            for f in self._inputs
        )

    def load(self, path: Path) -> None:
        self._load_paths([path])

    def load_multi(self, paths: list[Path]) -> None:
        self._load_paths(paths)

    def _load_paths(self, paths: list[Path]) -> None:
        # Cache current single-file state before switching away
        if len(self._paths) == 1 and self.is_dirty:
            self._edit_cache[self._paths[0]] = (
                self._filename_input.text(),
                {f: inp.text() for f, inp in self._inputs.items()},
            )

        self._paths = list(paths)
        self._multi = len(paths) > 1

        all_tags: list[dict[str, str]] = []
        for p in paths:
            try:
                all_tags.append(read(p))
            except Exception:
                all_tags.append({})

        common: dict[str, str] = {}
        for field in self._inputs:
            vals = [t.get(field, "") for t in all_tags]
            common[field] = vals[0] if len(set(vals)) == 1 else ""

        self._original = common

        # Restore cached edits for single-file, otherwise use on-disk values
        cached = self._edit_cache.get(paths[0]) if not self._multi and paths else None
        on_disk_name = paths[0].name if not self._multi and paths else ""
        filename_display = cached[0] if cached else on_disk_name
        tag_display = cached[1] if cached else common
        self._filename_original = paths[0].name if not self._multi and paths else ""

        self._filename_input.blockSignals(True)
        self._filename_input.setText(filename_display)
        self._filename_input.setEnabled(not self._multi)
        if self._multi:
            self._filename_input.setPlaceholderText("Multiple files")
        else:
            self._filename_input.setPlaceholderText("")
        self._filename_input.blockSignals(False)

        for field, inp in self._inputs.items():
            inp.blockSignals(True)
            inp.setText(tag_display.get(field, ""))
            if self._multi:
                all_vals = [t.get(field, "") for t in all_tags]
                inp.setPlaceholderText(
                    "" if len(set(all_vals)) == 1 else "Multiple values"
                )
            else:
                inp.setPlaceholderText("")
            inp.setEnabled(True)
            inp.blockSignals(False)

        dirty = self.is_dirty
        self._save_btn.setEnabled(dirty)
        for p in paths:
            self.dirty_changed.emit(p, dirty)

    def save(self) -> None:
        if not self._paths or not self.is_dirty:
            return

        if not self._multi:
            old_path = self._paths[0]
            new_name = self._filename_input.text().strip()

            if new_name and new_name != self._filename_original:
                error = _filename_error(new_name, self._filename_original, old_path.parent)
                if error is not None:
                    QMessageBox.critical(self, "Rename Failed", error)
                    return
                new_path = old_path.parent / new_name
                try:
                    old_path.rename(new_path)
                except Exception as e:
                    QMessageBox.critical(self, "Rename Failed", str(e))
                    return
                self._edit_cache.pop(old_path, None)
                self._paths[0] = new_path
                self._filename_original = new_name
                self.file_renamed.emit(old_path, new_path)

            tags = {f: inp.text() for f, inp in self._inputs.items()}
            try:
                write(self._paths[0], tags)
            except Exception as e:
                QMessageBox.critical(self, "Save Failed", str(e))
                return
            self._edit_cache.pop(self._paths[0], None)
            self._original = dict(tags)
            self._save_btn.setEnabled(False)
            self.file_saved.emit(self._paths[0])
            self.dirty_changed.emit(self._paths[0], False)
        else:
            updates = {
                f: inp.text()
                for f, inp in self._inputs.items()
                if inp.text() != self._original.get(f, "")
            }
            errors: list[str] = []
            for p in self._paths:
                try:
                    tags = read(p)
                    tags.update(updates)
                    write(p, tags)
                    self.file_saved.emit(p)
                    self.dirty_changed.emit(p, False)
                except Exception as e:
                    errors.append(f"{p.name}: {e}")
            if errors:
                QMessageBox.critical(self, "Save Failed", "\n".join(errors))
                return
            for f, v in updates.items():
                self._original[f] = v
            self._save_btn.setEnabled(False)

    def clear(self) -> None:
        self._paths = []
        self._multi = False
        self._original = {}
        self._filename_original = ""
        self._filename_input.blockSignals(True)
        self._filename_input.clear()
        self._filename_input.setEnabled(False)
        self._filename_input.setPlaceholderText("")
        self._filename_input.blockSignals(False)
        for inp in self._inputs.values():
            inp.blockSignals(True)
            inp.clear()
            inp.setEnabled(False)
            inp.setPlaceholderText("")
            inp.blockSignals(False)
        self._save_btn.setEnabled(False)

    def clear_cache(self) -> None:
        self._edit_cache.clear()

    def reload_settings(self) -> None:
        old_filename = self._filename_input.text()
        old_values = {f: inp.text() for f, inp in self._inputs.items()}
        old_placeholders = {f: inp.placeholderText() for f, inp in self._inputs.items()}
        self._rebuild()
        self._filename_input.blockSignals(True)
        self._filename_input.setText(old_filename)
        self._filename_input.blockSignals(False)
        for field, inp in self._inputs.items():
            val = old_values.get(field, self._original.get(field, ""))
            inp.blockSignals(True)
            inp.setText(val)
            if field in old_placeholders:
                inp.setPlaceholderText(old_placeholders[field])
            inp.blockSignals(False)
        self._save_btn.setEnabled(self.is_dirty)


def _filename_error(new_name: str, original_name: str, parent_dir: Path) -> str | None:
    if not new_name:
        return "Filename cannot be empty."
    p = Path(new_name)
    if p.name != new_name:
        return "Filename must not contain path separators."
    if new_name in (".", ".."):
        return f'"{new_name}" is not a valid filename.'
    target = parent_dir / new_name
    if target.exists() and new_name != original_name:
        return f'"{new_name}" already exists.'
    return None
