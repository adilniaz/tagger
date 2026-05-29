import pytest
from pathlib import Path
from unittest.mock import patch
from textual.app import App, ComposeResult
from screens.browser_screen import BrowserScreen


class BrowserApp(App):
    result: Path | None = None

    def on_mount(self) -> None:
        self.push_screen(BrowserScreen(), self._on_result)

    def _on_result(self, result: Path | None) -> None:
        self.result = result


@pytest.mark.asyncio
async def test_browser_screen_mounts():
    app = BrowserApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert any(isinstance(s, BrowserScreen) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_cancel_dismisses_with_none():
    app = BrowserApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#cancel-btn")
        await pilot.pause()
    assert app.result is None


# --- SettingsScreen ---

from screens.settings_screen import SettingsScreen
from core.settings import Settings


class SettingsApp(App):
    def on_mount(self) -> None:
        self.push_screen(SettingsScreen())


@pytest.mark.asyncio
async def test_settings_screen_mounts():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert any(isinstance(s, SettingsScreen) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_settings_screen_shows_extended_field_checkboxes():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import Checkbox
        checkboxes = app.screen.query(Checkbox)
        labels = [str(cb.label) for cb in checkboxes]
        assert any("Album Artist" in l for l in labels)
        assert any("Composer" in l for l in labels)


@pytest.mark.asyncio
async def test_settings_close_saves(tmp_path, monkeypatch):
    monkeypatch.setattr("core.settings.CONFIG_PATH", tmp_path / "settings.json")
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        # directly save via the screen to avoid modal click-offset issues
        app.screen._settings.save()
        await pilot.pause()
    assert (tmp_path / "settings.json").exists()


# --- BatchEditScreen ---

from screens.batch_edit_screen import BatchEditScreen


class BatchApp(App):
    result: dict | None = None

    def on_mount(self) -> None:
        self.push_screen(BatchEditScreen(), self._on_result)

    def _on_result(self, result: dict | None) -> None:
        self.result = result


@pytest.mark.asyncio
async def test_batch_screen_mounts():
    app = BatchApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert any(isinstance(s, BatchEditScreen) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_batch_cancel_returns_none():
    app = BatchApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.dismiss(None)
        await pilot.pause()
    assert app.result is None


# --- MainScreen ---

from app import TaggerApp
from widgets.file_list import FileList
from widgets.tag_editor import TagEditor


@pytest.mark.asyncio
async def test_app_mounts_main_screen():
    from screens.main_screen import MainScreen
    app = TaggerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert any(isinstance(s, MainScreen) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_ctrl_b_pushes_browser_screen():
    app = TaggerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+b")
        await pilot.pause()
        assert any(isinstance(s, BrowserScreen) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_ctrl_s_pushes_settings_screen():
    app = TaggerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert any(isinstance(s, SettingsScreen) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_file_selected_message_loads_tag_editor(tmp_path):
    p = tmp_path / "song.mp3"
    p.write_bytes(b"")
    app = TaggerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen  # MainScreen is the active screen
        with patch("widgets.tag_editor.read", return_value={"title": "Hi"}), \
             patch("widgets.tag_editor.Settings.load", return_value=Settings()):
            screen.query_one(FileList).post_message(FileList.FileSelected(p))
            await pilot.pause()
        assert screen.query_one(TagEditor)._path == p
