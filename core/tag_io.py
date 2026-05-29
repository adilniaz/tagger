from __future__ import annotations
from pathlib import Path
from mutagen import File as MutagenFile  # noqa: F401

AUDIO_EXTENSIONS = frozenset({
    ".mp3", ".m4a", ".mp4", ".flac", ".ogg", ".opus",
    ".wma", ".wav", ".aiff", ".aif", ".ape", ".wv", ".mpc",
})
EBOOK_EXTENSIONS = frozenset({".epub", ".pdf", ".fb2", ".mobi", ".azw"})
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | EBOOK_EXTENSIONS

BASIC_FIELDS = ["title", "artist", "album", "date", "tracknumber", "genre"]
EXTENDED_FIELDS = ["albumartist", "discnumber", "composer", "comment", "lyrics"]
ALL_FIELDS = BASIC_FIELDS + EXTENDED_FIELDS

FIELD_LABELS: dict[str, str] = {
    "title": "Title",
    "artist": "Artist",
    "album": "Album",
    "date": "Year",
    "tracknumber": "Track",
    "genre": "Genre",
    "albumartist": "Album Artist",
    "discnumber": "Disc",
    "composer": "Composer",
    "comment": "Comment",
    "lyrics": "Lyrics",
}


def read(path: Path) -> dict[str, str]:
    ext = path.suffix.lower()
    if ext in AUDIO_EXTENSIONS:
        return _read_audio(path)
    if ext in EBOOK_EXTENSIONS:
        return _read_ebook(path)
    raise ValueError(f"Unsupported format: {ext}")


def write(path: Path, tags: dict[str, str]) -> None:
    ext = path.suffix.lower()
    if ext in AUDIO_EXTENSIONS:
        _write_audio(path, tags)
    elif ext in EBOOK_EXTENSIONS:
        _write_ebook(path, tags)
    else:
        raise ValueError(f"Unsupported format: {ext}")


def _read_audio(path: Path) -> dict[str, str]:
    f = MutagenFile(str(path), easy=True)
    if f is None:
        return {}
    result: dict[str, str] = {}
    for key in ALL_FIELDS:
        val = f.get(key)
        if val:
            result[key] = str(val[0])
    return result


def _write_audio(path: Path, tags: dict[str, str]) -> None:
    f = MutagenFile(str(path), easy=True)
    if f is None:
        raise IOError(f"Cannot open audio file: {path}")
    for key, value in tags.items():
        if value:
            f[key] = value
        elif key in f:
            del f[key]
    f.save()


# Ebook backends — implemented in Task 4
def _read_ebook(path: Path) -> dict[str, str]:
    raise NotImplementedError


def _write_ebook(path: Path, tags: dict[str, str]) -> None:
    raise NotImplementedError
