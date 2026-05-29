from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Input, Button, Label
from textual.containers import Vertical, Horizontal
from core.tag_io import BASIC_FIELDS, EXTENDED_FIELDS, FIELD_LABELS
from core.settings import Settings


class BatchEditScreen(ModalScreen[dict[str, str] | None]):
    CSS = """
    BatchEditScreen {
        align: center middle;
    }
    BatchEditScreen > Vertical {
        width: 65%;
        height: auto;
        max-height: 85%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    .batch-row { height: auto; margin-bottom: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        settings = Settings.load()
        self._active_fields = BASIC_FIELDS + [
            f for f in EXTENDED_FIELDS if f in settings.enabled_extended
        ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Batch Edit — check fields to apply to all files")
            for field_key in self._active_fields:
                with Horizontal(classes="batch-row"):
                    yield Checkbox(
                        FIELD_LABELS[field_key],
                        value=False,
                        id=f"bcb-{field_key}",
                        name=field_key,
                    )
                    yield Input(
                        placeholder=FIELD_LABELS[field_key],
                        id=f"bv-{field_key}",
                        name=field_key,
                        disabled=True,
                    )
            with Horizontal():
                yield Button("Apply", id="batch-apply-btn", variant="primary")
                yield Button("Cancel", id="batch-cancel-btn")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.name:
            inp = self.query_one(f"#bv-{event.checkbox.name}", Input)
            inp.disabled = not event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "batch-cancel-btn":
            self.dismiss(None)
            return
        result: dict[str, str] = {}
        for field_key in self._active_fields:
            cb = self.query_one(f"#bcb-{field_key}", Checkbox)
            if cb.value:
                inp = self.query_one(f"#bv-{field_key}", Input)
                result[field_key] = inp.value
        self.dismiss(result if result else None)
