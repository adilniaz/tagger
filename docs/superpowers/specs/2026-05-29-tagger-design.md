# Tagger — Design Spec
**Date:** 2026-05-29

## Overview

A Python TUI application for viewing and editing metadata tags on audio and ebook files. Built with [Textual](https://github.com/Textualize/textual) for the UI and [mutagen](https://mutagen.readthedocs.io/) for audio tag I/O, with additional libraries for ebook formats.

---

## Layout

```
┌──────────────────────────────────────────────────────┐
│ tagger   [^B Browse] [^S Settings] [^Q Quit]         │
├─────────────────────┬────────────────────────────────┤
│ Files               │ Tag Editor                     │
│                     │                                │
│ ► song1.mp3         │ Title:  [                   ]  │
│   song2.mp3         │ Artist: [                   ]  │
│   song3.m4a         │ Album:  [                   ]  │
│                     │ Year:   [      ]               │
│                     │ Track:  [      ]               │
│                     │ Genre:  [                   ]  │
│                     │                                │
│                     │ [^W Save]   [^E Batch Edit]    │
└─────────────────────┴────────────────────────────────┘
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+B` | Open file/directory picker |
| `Ctrl+S` | Open Settings screen |
| `Ctrl+W` | Save current file |
| `Ctrl+E` | Open Batch Edit modal |
| `Ctrl+Q` | Quit |

---

## Screens & Components

### Main Screen (`main_screen.py`)
Two-panel layout. Houses the `FileList` and `TagEditor` widgets. Header contains Browse, Settings, and Quit buttons.

### Browser Screen (`browser_screen.py`)
Modal screen triggered by `Ctrl+B`. Lets the user navigate the filesystem and select either a single file or a directory. On confirm:
- **Single file** → loads directly into `TagEditor`; `FileList` shows just that file.
- **Directory** → `FileList` is populated with all supported audio/ebook files in that directory.

### Settings Screen (`settings_screen.py`)
Full-screen modal triggered by `Ctrl+S`. Displays:
- Checkboxes to enable extended tag fields: album artist, disc number, composer, comment, lyrics.
- Settings are saved to `~/.config/tagger/settings.json` and take effect immediately — `TagEditor` re-renders its field list on close.

### Batch Edit Screen (`batch_edit_screen.py`)
Modal triggered by `Ctrl+E`. Shows enabled tag fields with checkboxes to select which ones to apply, and input fields for the values. On confirm, writes the selected tag values to every file currently in the `FileList`.

---

## Widgets

### FileList (`widgets/file_list.py`)
- Lists all supported files in the loaded directory, or a single file if one was selected.
- Clicking a file loads its tags into `TagEditor`.
- Dirty (unsaved) files are marked with `*`.
- Shows a "No supported files found" message for empty results.

### TagEditor (`widgets/tag_editor.py`)
- Renders input fields for the active file's tags.
- Basic fields (always shown): title, artist, album, year, track number, genre.
- Extended fields (shown when enabled in settings): album artist, disc number, composer, comment, lyrics.
- Holds unsaved changes in memory. Dirty state is cleared on successful save.

---

## Core

### tag_io.py
The only module that touches file I/O. Routes to the correct backend by file extension. Exposes two functions:

```python
def read(path: Path) -> dict[str, str]: ...
def write(path: Path, tags: dict[str, str]) -> None: ...
```

All tag values are plain strings. The UI never imports mutagen or any ebook library directly.

### settings.py
Loads and saves `~/.config/tagger/settings.json`. Exposes a `Settings` dataclass with a list of enabled extended fields.

---

## Supported Formats

### Audio (via mutagen)

| Extension | Tag Format |
|-----------|-----------|
| `.mp3` | ID3 v2.3/v2.4 |
| `.m4a`, `.mp4` | iTunes MP4 |
| `.flac` | Vorbis Comment |
| `.ogg` | Vorbis Comment |
| `.opus` | Vorbis Comment |
| `.wma` | ASF |
| `.wav` | RIFF INFO |
| `.aiff`, `.aif` | ID3 |
| `.ape` | APEv2 |
| `.wv` | APEv2 (WavPack) |
| `.mpc` | APEv2 (Musepack) |

### Ebook (via separate libraries)

| Extension | Library | Fields |
|-----------|---------|--------|
| `.epub` | `ebooklib` | title, author, publisher, date, language, description, ISBN |
| `.pdf` | `pypdf` | title, author, subject, creator, keywords |
| `.fb2` | stdlib XML | title, author, genre, language, date |
| `.mobi`, `.azw` | `mobi` (best-effort) | title, author |

---

## Data Flow

1. `Ctrl+B` → `BrowserScreen` opens. User selects file or directory.
2. **File** → `tag_io.read()` → `TagEditor` populates fields. `FileList` shows one entry.
3. **Directory** → `FileList` scans for supported extensions. User clicks a file → same read flow.
4. User edits fields → changes held in `TagEditor` memory, file marked dirty in `FileList`.
5. `Ctrl+W` → `tag_io.write()` persists to disk, dirty mark cleared.
6. `Ctrl+E` → `BatchEditScreen` opens. User selects fields and values. On confirm, `tag_io.write()` called for every file in `FileList`.
7. `Ctrl+S` → `SettingsScreen` opens. On close, `TagEditor` re-renders with updated field list.

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Unsupported file format | File shown in list with warning indicator; tag editor shows error message |
| Navigate away with unsaved changes | Confirmation dialog: "Discard changes or save first?" |
| Write failure (e.g. permissions) | Toast notification with error message; dirty state preserved |
| Empty directory | FileList shows "No supported files found" |
| Missing tag field in file | Field renders as empty input, not an error |
| `.mobi`/`.azw` parse failure | Graceful fallback: show file with warning, skip unsupported fields |

---

## Project Structure

```
tagger/
├── main.py
├── app.py
├── screens/
│   ├── main_screen.py
│   ├── settings_screen.py
│   ├── batch_edit_screen.py
│   └── browser_screen.py
├── widgets/
│   ├── file_list.py
│   └── tag_editor.py
├── core/
│   ├── tag_io.py
│   └── settings.py
└── pyproject.toml
```

## Dependencies

```toml
[project]
dependencies = [
    "textual",
    "mutagen",
    "ebooklib",
    "pypdf",
    "mobi",
]
```
