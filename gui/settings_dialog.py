from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget,
)

from core.settings import EXTENDED_FIELDS, Settings
from core.tag_io import FIELD_LABELS


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(300)

        settings = Settings.load()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Extended metadata fields:"))

        self._checks: dict[str, QCheckBox] = {}
        for field in EXTENDED_FIELDS:
            label = FIELD_LABELS.get(field, field.title())
            check = QCheckBox(label)
            check.setChecked(field in settings.enabled_extended)
            self._checks[field] = check
            layout.addWidget(check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        enabled = {f for f, c in self._checks.items() if c.isChecked()}
        Settings(enabled_extended=enabled).save()
        self.accept()
