# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
python main.py

# Run all tests
python -m pytest

# Run a single test file
python -m pytest tests/test_tag_io_audio.py -v

# Run a single test
python -m pytest tests/test_tag_io_audio.py::test_read_returns_basic_tags -v

# Install dependencies (no editable install — hatchling editable mode is broken in this env)
pip install textual mutagen ebooklib pypdf pytest pytest-asyncio
```

## Architecture

The app is a [Textual](https://github.com/Textualize/textual) TUI. The single rule that governs the whole design: **the UI never imports mutagen, ebooklib, or pypdf**. All file I/O goes through `core/tag_io.py`, which returns plain `dict[str, str]` to everyone else.

### Layers

```
app.py / main.py          — entry point; TaggerApp mounts MainScreen
screens/                  — full-screen and modal Screen subclasses
widgets/                  — reusable Widget subclasses used by MainScreen
core/tag_io.py            — only place that touches audio/ebook files
core/settings.py          — persists ~/.config/tagger/settings.json
```

### Screen stack

`TaggerApp` starts with `MainScreen` on the stack. All other screens are pushed as modals and dismissed with a return value:

| Screen | Trigger | Returns |
|--------|---------|---------|
| `BrowserScreen` | `Ctrl+B` | `Path \| None` |
| `SettingsScreen` | `Ctrl+S` | `None` (saves on dismiss) |
| `BatchEditScreen` | `Ctrl+E` | `dict[str, str] \| None` |
| `_ConfirmScreen` | dirty navigation | `bool` (discard?) |

`push_screen(screen, callback)` — the callback receives the dismissed value and runs in the context of `MainScreen`.

### MainScreen data flow

```
Ctrl+B → BrowserScreen → path → FileList.load(path)
FileList click → FileList.FileSelected message → MainScreen → TagEditor.load(path)
TagEditor edit → TagEditor.DirtyChanged message → MainScreen → FileList.mark_dirty/clean
Ctrl+W → MainScreen.action_save → TagEditor.save() → TagEditor.FileSaved → FileList.mark_clean
Ctrl+E → BatchEditScreen → dict → MainScreen._apply_batch → tag_io.read/write per file
Ctrl+S → SettingsScreen (saves on close) → TagEditor.reload_settings()
```

### Messaging pattern

Widgets communicate upward via Textual `Message` subclasses, not direct calls. Three messages are defined:

- `FileList.FileSelected(path)` — user clicked a file
- `TagEditor.FileSaved(path)` — save completed successfully
- `TagEditor.DirtyChanged(path, dirty)` — edit state changed

`MainScreen` handles all three via `on_*` methods. Widgets never hold references to each other.

### core/tag_io.py

Two public functions: `read(path) -> dict[str, str]` and `write(path, dict)`. Both dispatch on `path.suffix.lower()` to either the audio branch (mutagen `easy=True` API, normalised field names) or the ebook branch.

**Field name convention** — all tag keys are lowercase mutagen "easy" names: `title`, `artist`, `album`, `date`, `tracknumber`, `genre`, `albumartist`, `discnumber`, `composer`, `comment`, `lyrics`. The constants `BASIC_FIELDS`, `EXTENDED_FIELDS`, `ALL_FIELDS`, and `FIELD_LABELS` in `tag_io.py` are the single source of truth for field names across the whole app.

**Format support:**
- Audio (mutagen `easy=True`): `.mp3`, `.m4a/.mp4`, `.flac`, `.ogg`, `.opus`, `.wma`, `.wav`, `.aiff/.aif`, `.ape`, `.wv`, `.mpc`
- Ebook: `.epub` (ebooklib DC metadata), `.pdf` (pypdf `/Title /Author /Subject /Creator`), `.fb2` (stdlib XML, namespace `http://www.gribuser.ru/xml/fictionbook/2.0`), `.mobi/.azw` (best-effort via optional `mobi` package — read-only, silently returns `{}` on failure)

`epub` and `PdfReader` are imported at **module level** in `tag_io.py` so tests can patch `core.tag_io.epub.read_epub` and `core.tag_io.PdfReader`.

### core/settings.py

`Settings` is a dataclass with one field: `enabled_extended: set[str]`. `Settings.load()` reads `CONFIG_PATH` each time it is called — no caching. The `CONFIG_PATH` module-level variable can be monkeypatched in tests (see `tests/test_settings.py`).

### TagEditor widget

`TagEditor._rebuild(settings)` tears down and remounts the entire widget DOM (removes all children, mounts a new `VerticalScroll` containing `Label`/`Input` pairs). This is called on `load()` and `reload_settings()`. Dirty state is computed by comparing current `Input.value` against `_original` — there is no reactive state; `is_dirty` is a property that iterates inputs.

### FileList widget

`FileList._refresh()` clears and rebuilds the `ListView` from `_paths` on every mutation. The `name` attribute of each `ListItem` stores the absolute path string; `_on_selected` reconstructs a `Path` from it.

## Testing

Tests use `pytest-asyncio` with `asyncio_mode = "auto"`. All Textual widget and screen tests use `async with app.run_test() as pilot`.

**Key patterns:**

- **Querying modal screens** — `app.query_one(SomeScreen)` does not work for screens; use `app.screen_stack` or `app.screen` instead.
- **Querying within a modal** — use `app.screen.query(Widget)` not `app.query(Widget)`.
- **Label text** — `str(label.render())` not `label.renderable` (not available in this Textual version).
- **Monkeypatching settings** — `monkeypatch.setattr("core.settings.CONFIG_PATH", tmp_path / "settings.json")`.
- **Mocking mutagen** — patch `core.tag_io.MutagenFile`; mock `__delitem__` via `.side_effect`, not by replacing it with a lambda (otherwise `assert_called_with` breaks).
- **Mocking ebook libs** — patch `core.tag_io.epub.read_epub`, `core.tag_io.epub.write_epub`, `core.tag_io.PdfReader` (module-level names, not inside-function imports).
