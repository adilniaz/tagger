import pytest
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Label
from widgets.file_list import FileList


class FileListApp(App):
    def compose(self) -> ComposeResult:
        yield FileList(id="fl")


@pytest.mark.asyncio
async def test_load_directory_lists_audio_files(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"")
    (tmp_path / "b.flac").write_bytes(b"")
    (tmp_path / "readme.txt").write_bytes(b"")
    app = FileListApp()
    async with app.run_test() as pilot:
        fl = app.query_one(FileList)
        fl.load(tmp_path)
        await pilot.pause()
        assert fl.all_paths() == sorted([tmp_path / "a.mp3", tmp_path / "b.flac"])


@pytest.mark.asyncio
async def test_load_single_file(tmp_path):
    p = tmp_path / "song.mp3"
    p.write_bytes(b"")
    app = FileListApp()
    async with app.run_test() as pilot:
        fl = app.query_one(FileList)
        fl.load(p)
        await pilot.pause()
        assert fl.all_paths() == [p]


@pytest.mark.asyncio
async def test_mark_dirty_and_clean(tmp_path):
    p = tmp_path / "song.mp3"
    p.write_bytes(b"")
    app = FileListApp()
    async with app.run_test() as pilot:
        fl = app.query_one(FileList)
        fl.load(p)
        await pilot.pause()
        fl.mark_dirty(p)
        assert fl.has_dirty()
        fl.mark_clean(p)
        assert not fl.has_dirty()


@pytest.mark.asyncio
async def test_empty_directory_shows_no_files_message(tmp_path):
    app = FileListApp()
    async with app.run_test() as pilot:
        fl = app.query_one(FileList)
        fl.load(tmp_path)
        await pilot.pause()
        assert fl.all_paths() == []
        labels = [str(lbl.render()) for lbl in fl.query(Label)]
        assert any("No supported" in l for l in labels)
