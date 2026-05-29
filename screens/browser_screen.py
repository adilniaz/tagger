from __future__ import annotations
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import DirectoryTree, Button, Label
from textual.containers import Vertical


class BrowserScreen(ModalScreen[Path | None]):
    CSS = """
    BrowserScreen {
        align: center middle;
    }
    BrowserScreen > Vertical {
        width: 70%;
        height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    DirectoryTree { height: 1fr; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._selected: Path | None = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Select a file or directory, then press Open")
            yield DirectoryTree(str(Path.home()), id="dir-tree")
            yield Button("Open", id="open-btn", variant="primary")
            yield Button("Cancel", id="cancel-btn")

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        self._selected = event.path

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self._selected = event.path

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-btn":
            self.dismiss(self._selected)
        else:
            self.dismiss(None)
