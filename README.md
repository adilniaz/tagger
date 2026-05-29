# tagger

A terminal UI app for editing metadata tags on audio and ebook files.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)

## Features

- **Browse** your filesystem and open a single file or an entire directory
- **Edit tags** for all common audio and ebook formats
- **Batch edit** — apply a field value to every file in the loaded directory at once
- **Dirty tracking** — unsaved files are marked with `*` in the file list; navigating away prompts you to confirm
- **Extended fields** — album artist, disc number, composer, comment, and lyrics are hidden by default and can be enabled per-field in Settings

## Supported formats

### Audio

| Extension | Tag format |
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

### Ebook

| Extension | Fields |
|-----------|--------|
| `.epub` | title, author, publisher, date, subject |
| `.pdf` | title, author, subject, creator |
| `.fb2` | title, author |
| `.mobi`, `.azw` | title, author (read-only, best-effort) |

## Installation

Requires Python 3.11+.

```bash
git clone <repo>
cd tagger
pip install textual mutagen ebooklib pypdf
python main.py
```

> **Note:** `.mobi`/`.azw` support requires the optional `mobi` package (`pip install mobi`). The app works fine without it — those files will just return empty tags.

## Usage

```
┌──────────────────────────────────────────────────────┐
│ tagger   [^B Browse] [^S Settings] [^Q Quit]         │
├─────────────────────┬────────────────────────────────┤
│ Files               │ Tag Editor                     │
│                     │                                │
│ ► song1.mp3         │ Title:  [                   ]  │
│   song2.mp3 *       │ Artist: [                   ]  │
│   song3.m4a         │ Album:  [                   ]  │
│                     │ Year:   [      ]               │
│                     │ Track:  [      ]               │
│                     │ Genre:  [                   ]  │
│                     │                                │
│                     │ [^W Save]   [^E Batch Edit]    │
└─────────────────────┴────────────────────────────────┘
```

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+B` | Open file/directory browser |
| `Ctrl+S` | Open Settings |
| `Ctrl+W` | Save current file |
| `Ctrl+E` | Open Batch Edit |
| `Ctrl+Q` | Quit |

### Workflow

1. Press `Ctrl+B` to open the browser. Navigate to a **file** or **directory** and press **Open**.
   - Single file: loaded directly into the tag editor.
   - Directory: all supported files are listed in the left panel.
2. Click a file in the list to load its tags into the editor.
3. Edit any field. The file is marked `*` in the list while it has unsaved changes.
4. Press `Ctrl+W` (or the Save button) to write tags to disk.
5. To apply the same value to all files in the list, press `Ctrl+E` — check the fields you want to change, enter values, and press **Apply**.

### Settings

Press `Ctrl+S` to open Settings. Toggle extended fields on or off:

- Album Artist
- Disc Number
- Composer
- Comment
- Lyrics

Settings are saved to `~/.config/tagger/settings.json` and take effect immediately when you close the Settings screen.

## Development

```bash
# Install dev dependencies
pip install textual mutagen ebooklib pypdf pytest pytest-asyncio

# Run all tests
python -m pytest

# Run a specific test file
python -m pytest tests/test_tag_io_audio.py -v

# Run a single test
python -m pytest tests/test_tag_io_audio.py::test_read_returns_basic_tags -v
```

### Project structure

```
tagger/
├── main.py                    # entry point
├── app.py                     # TaggerApp (Textual App subclass)
├── core/
│   ├── tag_io.py              # all file read/write — the only place that imports mutagen/ebooklib/pypdf
│   └── settings.py            # settings dataclass + ~/.config/tagger/settings.json persistence
├── widgets/
│   ├── file_list.py           # left panel — file list with dirty-state tracking
│   └── tag_editor.py          # right panel — tag form fields
├── screens/
│   ├── main_screen.py         # two-panel layout, keyboard bindings, event wiring
│   ├── browser_screen.py      # Ctrl+B filesystem picker modal
│   ├── settings_screen.py     # Ctrl+S extended-field checkboxes modal
│   └── batch_edit_screen.py   # Ctrl+E batch apply modal
└── tests/
    ├── test_settings.py
    ├── test_tag_io_audio.py
    ├── test_tag_io_ebook.py
    ├── test_file_list.py
    ├── test_tag_editor.py
    └── test_screens.py
```

### Architecture note

All UI code works with plain `dict[str, str]` tag values — it never imports mutagen, ebooklib, or pypdf directly. The `core/tag_io.py` module is the single boundary between the UI and the filesystem. This keeps the widgets and screens easy to test with mocks.

Tag field keys follow the mutagen "easy" naming convention: `title`, `artist`, `album`, `date`, `tracknumber`, `genre`, `albumartist`, `discnumber`, `composer`, `comment`, `lyrics`.
