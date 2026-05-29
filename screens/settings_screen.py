from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Button, Label
from textual.containers import Vertical
from core.settings import Settings, EXTENDED_FIELDS
from core.tag_io import FIELD_LABELS


class SettingsScreen(ModalScreen[None]):
    CSS = """
    SettingsScreen {
        align: center middle;
    }
    SettingsScreen > Vertical {
        width: 50%;
        height: auto;
        max-height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._settings = Settings.load()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Extended Fields")
            for field_key in EXTENDED_FIELDS:
                yield Checkbox(
                    FIELD_LABELS[field_key],
                    value=field_key in self._settings.enabled_extended,
                    id=f"cb-{field_key}",
                    name=field_key,
                )
            yield Button("Close", id="close-btn", variant="primary")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.name:
            if event.value:
                self._settings.enabled_extended.add(event.checkbox.name)
            else:
                self._settings.enabled_extended.discard(event.checkbox.name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self._settings.save()
            self.dismiss(None)
