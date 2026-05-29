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
