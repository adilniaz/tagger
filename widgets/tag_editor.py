from __future__ import annotations
from pathlib import Path
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, Button
from textual.containers import VerticalScroll
from core.tag_io import read, write, BASIC_FIELDS, EXTENDED_FIELDS, FIELD_LABELS
from core.settings import Settings


class TagEditor(Widget):
    class FileSaved(Message):
        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    class DirtyChanged(Message):
        def __init__(self, path: Path, dirty: bool) -> None:
            super().__init__()
            self.path = path
            self.dirty = dirty

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._path: Path | None = None
        self._original: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Label("No file loaded — press ^B to browse", id="te-placeholder")

    def load(self, path: Path) -> None:
        self._path = path
        try:
            self._original = read(path)
        except Exception as exc:
            self._original = {}
            self.query("*").remove()
            self.mount(Label(f"Error reading file: {exc}"))
            return
        self._rebuild(Settings.load())

    def reload_settings(self) -> None:
        if self._path:
            self._rebuild(Settings.load())

    def _rebuild(self, settings: Settings) -> None:
        self.query("*").remove()
        fields = BASIC_FIELDS + [
            f for f in EXTENDED_FIELDS if f in settings.enabled_extended
        ]
        scroll = VerticalScroll()
        self.mount(scroll)
        for field_key in fields:
            scroll.mount(Label(FIELD_LABELS[field_key]))
            scroll.mount(Input(
                value=self._original.get(field_key, ""),
                id=f"field-{field_key}",
                name=field_key,
            ))
        scroll.mount(Button("^W Save", id="save-btn", variant="primary"))

    def save(self) -> None:
        if not self._path:
            return
        tags = {inp.name: inp.value for inp in self.query(Input)}
        write(self._path, tags)
        self._original = dict(tags)
        self.post_message(self.FileSaved(self._path))

    @property
    def is_dirty(self) -> bool:
        if not self._path:
            return False
        return any(
            inp.value != self._original.get(inp.name, "")
            for inp in self.query(Input)
        )

    def on_input_changed(self, _: Input.Changed) -> None:
        if self._path:
            self.post_message(self.DirtyChanged(self._path, self.is_dirty))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self.save()
