from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QLineEdit,
    QScrollArea, QVBoxLayout, QWidget,
)


class BatchEditDialog(QDialog):
    def __init__(
        self,
        fields: list[str],
        labels: dict[str, str],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Batch Edit")
        self.setMinimumWidth(420)
        self._fields = fields
        self._checks: dict[str, QCheckBox] = {}
        self._inputs: dict[str, QLineEdit] = {}

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        layout.addWidget(scroll)

        content = QWidget()
        grid = QGridLayout(content)
        grid.setColumnStretch(1, 1)
        scroll.setWidget(content)

        for row, field in enumerate(fields):
            label = labels.get(field, field.title())
            check = QCheckBox(label + ":")
            inp = QLineEdit()
            inp.setEnabled(False)
            check.toggled.connect(inp.setEnabled)
            self._checks[field] = check
            self._inputs[field] = inp
            grid.addWidget(check, row, 0)
            grid.addWidget(inp, row, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> dict[str, str]:
        return {
            f: self._inputs[f].text()
            for f in self._fields
            if self._checks[f].isChecked()
        }
