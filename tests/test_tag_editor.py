import pytest
from pathlib import Path
from unittest.mock import patch
from textual.app import App, ComposeResult
from textual.widgets import Input, Label
from widgets.tag_editor import TagEditor
from core.settings import Settings


class TagEditorApp(App):
    def compose(self) -> ComposeResult:
        yield TagEditor(id="te")


@pytest.mark.asyncio
async def test_load_populates_basic_fields():
    tags = {"title": "Test Song", "artist": "Test Band", "album": "Test Album"}
    app = TagEditorApp()
    async with app.run_test() as pilot:
        te = app.query_one(TagEditor)
        with patch("widgets.tag_editor.read", return_value=tags), \
             patch("widgets.tag_editor.Settings.load", return_value=Settings()):
            te.load(Path("test.mp3"))
            await pilot.pause()
        inputs = {inp.name: inp.value for inp in te.query(Input)}
        assert inputs["title"] == "Test Song"
        assert inputs["artist"] == "Test Band"


@pytest.mark.asyncio
async def test_save_calls_write():
    tags = {"title": "Song"}
    app = TagEditorApp()
    async with app.run_test() as pilot:
        te = app.query_one(TagEditor)
        with patch("widgets.tag_editor.read", return_value=tags), \
             patch("widgets.tag_editor.Settings.load", return_value=Settings()), \
             patch("widgets.tag_editor.write") as mock_write:
            te.load(Path("test.mp3"))
            await pilot.pause()
            te.save()
        mock_write.assert_called_once()


@pytest.mark.asyncio
async def test_extended_fields_shown_when_enabled():
    tags = {}
    settings = Settings(enabled_extended={"albumartist", "composer"})
    app = TagEditorApp()
    async with app.run_test() as pilot:
        te = app.query_one(TagEditor)
        with patch("widgets.tag_editor.read", return_value=tags), \
             patch("widgets.tag_editor.Settings.load", return_value=settings):
            te.load(Path("test.mp3"))
            await pilot.pause()
        names = {inp.name for inp in te.query(Input)}
        assert "albumartist" in names
        assert "composer" in names
        assert "discnumber" not in names


@pytest.mark.asyncio
async def test_load_failure_shows_error():
    app = TagEditorApp()
    async with app.run_test() as pilot:
        te = app.query_one(TagEditor)
        with patch("widgets.tag_editor.read", side_effect=Exception("bad file")), \
             patch("widgets.tag_editor.Settings.load", return_value=Settings()):
            te.load(Path("corrupt.mp3"))
            await pilot.pause()
        labels = [str(lbl.render()) for lbl in te.query(Label)]
        assert any("Error" in l or "error" in l for l in labels)
