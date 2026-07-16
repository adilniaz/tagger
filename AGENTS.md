# AGENTS.md

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

# Install dependencies
pip install pyside6 mutagen ebooklib pypdf pytest pytest-qt

# Install with optional mobi support
pip install .[mobi]

# Lint
ruff check
```

## Architecture

The app is a **PySide6 GUI**. The single rule that governs the whole design: **the UI never imports mutagen, ebooklib, or pypdf**. All file I/O goes through `core/tag_io.py`, which returns plain `dict[str, str]` to everyone else.

### Layers

```
main.py               — entry point; creates QApplication with dark palette, launches MainWindow
gui/main_window.py    — MainWindow(QMainWindow): toolbar, splitter layout, wires all signals
gui/file_table.py     — FileTable(QWidget): sortable table of files with background tag loading
gui/tag_editor.py     — TagEditorPanel(QWidget): form for editing tags of one or many files
gui/batch_edit_dialog.py — BatchEditDialog(QDialog): checkbox-gated bulk field editor
gui/settings_dialog.py   — SettingsDialog(QDialog): toggles for extended metadata fields
core/tag_io.py        — only place that touches audio/ebook files
core/settings.py      — persists ~/.config/tagger/settings.json
```

### MainWindow layout

`MainWindow` is a `QMainWindow` with:

- A `QToolBar` (non-movable) containing actions for Open Folder, Open File(s), Save, Batch Edit, Settings, Quit
- A `QSplitter(Horizontal)` as central widget, holding `FileTable` (left, wider) and `TagEditorPanel` (right)

### Keyboard shortcuts

| Action       | Shortcut |
| ------------ | -------- |
| Open Folder  | `Ctrl+B` |
| Open File(s) | `Ctrl+O` |
| Save         | `Ctrl+S` |
| Batch Edit   | `Ctrl+E` |
| Settings     | `Ctrl+,` |
| Quit         | `Ctrl+Q` |

### Signal flow

Components communicate via Qt signals — widgets never hold references to each other.

| Signal                                     | Source                  | Connected to                                                               |
| ------------------------------------------ | ----------------------- | -------------------------------------------------------------------------- |
| `FileTable.selection_changed(list[Path])`  | row selection in table  | `MainWindow._on_selection_changed` → 150ms debounce → `TagEditorPanel.load` / `.load_multi` / `.clear` |
| `TagEditorPanel.dirty_changed(Path, bool)` | any field edit          | `FileTable.set_dirty`                                                      |
| `TagEditorPanel.file_saved(Path)`          | successful save         | `FileTable.set_clean`                                                      |
| `TagEditorPanel.file_renamed(old, new)`    | filename change on save | `FileTable.rename_path`                                                    |

### MainWindow data flow

```
Ctrl+B → QFileDialog.getExistingDirectory → FileTable.load(folder)
Ctrl+O → QFileDialog.getOpenFileNames → FileTable.load_files(paths)
FileTable row click → selection_changed → 150ms debounce → TagEditorPanel.load/load_multi/clear
Ctrl+S → TagEditorPanel.save() → writes to disk, emits file_saved / file_renamed
Ctrl+E → BatchEditDialog → values dict → read/write per selected (or all) files
Ctrl+, → SettingsDialog.exec() → Settings.save() → TagEditorPanel.reload_settings()
```

Selection changes are debounced via a 150ms `QTimer` on MainWindow to avoid rapid repeated loads while drag/shift-selecting. On empty selection, `TagEditorPanel.clear()` is called.

### gui/file_table.py

- `_FileRow` — dataclass holding `path`, `size_bytes`, `mtime`, `size_str`, `mtime_str`, `title`, `artist`, `album`, `dirty`. Raw numerics stored for correct column sorting.
- `FileTableModel(QAbstractTableModel)` — 7 columns: icon, name, size, title, modified, artist, album. Dirty files show bold name prefixed with `* `.
- `SORT_ROLE = Qt.ItemDataRole.UserRole + 1` — used by the proxy model to sort on raw numeric/lowercase values instead of display strings.
- `QSortFilterProxyModel` wraps the model with `setSortRole(SORT_ROLE)` to enable correct column sorting.
- `TagLoaderThread(QThread)` — background thread that calls `tag_io.read()` per path and emits `tags_loaded(Path, dict)`. Has a `_stop` flag and `stop()` method to abort early.
- `FileTable.load(path)` — accepts a directory or single file, delegates to `load_files(paths)`.
- `FileTable.load_files(paths)` — stops any running loader before starting a new one.
- `FileTable._stop_loader()` / `.shutdown()` — stop loader thread and wait; called on close.
- `FileTable.selected_paths()` returns currently selected rows; `FileTable.all_paths()` returns everything.
- Dirty state tracked per-path in the model; `set_dirty` / `set_clean` / `rename_path` update it.
- `_on_selection_changed` always emits (even empty list) so the editor can clear.
- `_format_mtime(timestamp) -> str` — portable manual formatter (no `strftime` platform issues).

### gui/tag_editor.py — TagEditorPanel

- Layout: `QVBoxLayout` → `QScrollArea` → `QFormLayout` (file name field + one `QLineEdit` per active tag field) + Save button.
- `_rebuild()` — clears and remounts the form; called on init and `reload_settings()`. Preserves current text across the rebuild.
- `_edit_cache: dict[Path, tuple[str, dict]]` — caches unsaved edits when the user switches files without saving, so edits are restored if they switch back.
- `load(path)` / `load_multi(paths)` — both delegate to `_load_paths()`. Multi mode disables the filename field and shows "Multiple values" placeholder where fields differ.
- `save()` — in single mode, validates filename (no path separators, no overwrite of existing file), renames on disk if changed (emits `file_renamed`), then writes tags. In multi mode, writes only fields that differ from `_original` to all selected paths.
- `clear()` — disables and empties all form fields when selection is empty.
- `current_path` property — returns `_paths[0]` or `None` (public accessor, used by MainWindow).
- `is_dirty` property — compares current input text against `_original`; no reactive state.
- `_filename_error(name, original, dir) -> str|None` — module-level validation: rejects empty names, path separators, `.`/`..`, and existing files.

### gui/batch_edit_dialog.py — BatchEditDialog

Each tag field is a `QCheckBox` + `QLineEdit` pair. The line edit is disabled until its checkbox is checked. `get_values()` returns only checked fields.

### gui/settings_dialog.py — SettingsDialog

One `QCheckBox` per extended field. On accept, writes `Settings(enabled_extended=...)` to disk.

### core/tag_io.py

Two public functions: `read(path) -> dict[str, str]` and `write(path, dict)`. Both dispatch on `path.suffix.lower()`.

**Constants** — single source of truth for field names:

- `BASIC_FIELDS` — `["title", "artist", "album", "date", "tracknumber", "genre"]`
- `EXTENDED_FIELDS` — `["albumartist", "discnumber", "composer", "comment", "lyrics"]`
- `ALL_FIELDS` — `BASIC_FIELDS + EXTENDED_FIELDS`
- `FIELD_LABELS` — human-readable display names
- `AUDIO_EXTENSIONS`, `EBOOK_EXTENSIONS`, `SUPPORTED_EXTENSIONS` — frozensets used by `FileTable` and `MainWindow`

**Format support:**

- Audio (mutagen `easy=True`): `.mp3`, `.m4a/.mp4`, `.flac`, `.ogg`, `.opus`, `.wma`, `.wav`, `.aiff/.aif`, `.ape`, `.wv`, `.mpc`
- Ebook: `.epub` (ebooklib DC metadata), `.pdf` (pypdf, uses `PdfWriter(clone_from=reader)` to preserve structure), `.fb2` (stdlib XML — reads/writes title and artist), `.mobi/.azw` (best-effort via optional `mobi` package — read-only, silently returns `{}` on failure, extracts to temp and cleans up)

All ebook writes use `_atomic_write(path, write_fn)` — writes to a `.tmp~` file then `os.replace()` to avoid corruption.

`epub` and `PdfReader` are imported at **module level** so tests can patch `core.tag_io.epub.read_epub` and `core.tag_io.PdfReader`.

### core/settings.py

`Settings` dataclass with one field: `enabled_extended: set[str]`. `Settings.load()` reads `CONFIG_PATH` each time — no caching. `CONFIG_PATH` can be monkeypatched in tests. Also re-exports `EXTENDED_FIELDS` (imported from `tag_io.py`) — `SettingsDialog` imports it from here.

## Testing

Tests use `pytest-qt`. GUI tests (model, filename validation, etc.) run with Qt offscreen via `tests/conftest.py`.

**Key patterns:**

- **Mocking mutagen** — patch `core.tag_io.MutagenFile`; mock `__delitem__` via `.side_effect`, not by replacing it with a lambda (otherwise `assert_called_with` breaks).
- **Mocking ebook libs** — patch `core.tag_io.epub.read_epub`, `core.tag_io.epub.write_epub`, `core.tag_io.PdfReader` (module-level names). For EPUB atomic write tests, the `write_epub` mock side-effect must create the temp file so `os.replace()` succeeds.
- **Monkeypatching settings** — `monkeypatch.setattr("core.settings.CONFIG_PATH", tmp_path / "settings.json")`.
