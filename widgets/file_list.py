from __future__ import annotations
from pathlib import Path
from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import ListView, ListItem, Label
from textual import on
from core.tag_io import SUPPORTED_EXTENSIONS


class FileList(ListView):
    class FileSelected(Message):
        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._paths: list[Path] = []
        self._dirty: set[Path] = set()

    def load(self, path: Path) -> None:
        self._dirty.clear()
        if path.is_dir():
            self._paths = sorted(
                p for p in path.iterdir()
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
            )
        else:
            self._paths = [path]
        self._refresh()

    def mark_dirty(self, path: Path) -> None:
        self._dirty.add(path)
        self._refresh()

    def mark_clean(self, path: Path) -> None:
        self._dirty.discard(path)
        self._refresh()

    def has_dirty(self) -> bool:
        return bool(self._dirty)

    def all_paths(self) -> list[Path]:
        return list(self._paths)

    def _refresh(self) -> None:
        self.clear()
        if not self._paths:
            self.append(ListItem(Label("No supported files found")))
            return
        for path in self._paths:
            label = path.name + (" *" if path in self._dirty else "")
            self.append(ListItem(Label(label), name=str(path)))

    @on(ListView.Selected)
    def _on_selected(self, event: ListView.Selected) -> None:
        if event.item.name:
            self.post_message(self.FileSelected(Path(event.item.name)))
