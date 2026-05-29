from __future__ import annotations
from pathlib import Path
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, Button, Label
from textual.containers import Horizontal, Vertical
from widgets.file_list import FileList
from widgets.tag_editor import TagEditor


class _ConfirmScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Unsaved changes — discard and continue?")
            yield Button("Discard", id="discard-btn", variant="error")
            yield Button("Keep editing", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "discard-btn")


class MainScreen(Screen):
    BINDINGS = [
        Binding("ctrl+b", "browse", "^B Browse"),
        Binding("ctrl+s", "settings", "^S Settings"),
        Binding("ctrl+w", "save", "^W Save"),
        Binding("ctrl+e", "batch_edit", "^E Batch Edit"),
        Binding("ctrl+q", "quit", "^Q Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield FileList(id="file-list")
            yield TagEditor(id="tag-editor")
        yield Footer()

    def action_browse(self) -> None:
        from screens.browser_screen import BrowserScreen
        self.app.push_screen(BrowserScreen(), self._on_browse_result)

    def _on_browse_result(self, path: object) -> None:
        if isinstance(path, Path):
            self.query_one(FileList).load(path)

    def action_settings(self) -> None:
        from screens.settings_screen import SettingsScreen
        self.app.push_screen(
            SettingsScreen(),
            lambda _: self.query_one(TagEditor).reload_settings(),
        )

    def action_save(self) -> None:
        te = self.query_one(TagEditor)
        try:
            te.save()
        except Exception as exc:
            self.app.notify(f"Save failed: {exc}", severity="error")

    def action_batch_edit(self) -> None:
        from screens.batch_edit_screen import BatchEditScreen
        self.app.push_screen(BatchEditScreen(), self._apply_batch)

    def _apply_batch(self, result: dict | None) -> None:
        if not result:
            return
        from core.tag_io import read, write
        failed: list[str] = []
        for path in self.query_one(FileList).all_paths():
            try:
                tags = read(path)
                tags.update(result)
                write(path, tags)
            except Exception:
                failed.append(path.name)
        if failed:
            self.app.notify(f"Failed: {', '.join(failed)}", severity="error")
        else:
            self.app.notify("Batch edit applied")

    def on_file_list_file_selected(self, message: FileList.FileSelected) -> None:
        te = self.query_one(TagEditor)
        if te.is_dirty:
            self.app.push_screen(
                _ConfirmScreen(),
                lambda discard: te.load(message.path) if discard else None,
            )
        else:
            te.load(message.path)

    def on_tag_editor_file_saved(self, message: TagEditor.FileSaved) -> None:
        self.query_one(FileList).mark_clean(message.path)

    def on_tag_editor_dirty_changed(self, message: TagEditor.DirtyChanged) -> None:
        fl = self.query_one(FileList)
        if message.dirty:
            fl.mark_dirty(message.path)
        else:
            fl.mark_clean(message.path)
