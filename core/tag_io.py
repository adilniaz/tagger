from __future__ import annotations
from pathlib import Path
from mutagen import File as MutagenFile  # noqa: F401
from ebooklib import epub
from pypdf import PdfReader, PdfWriter

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


def _read_ebook(path: Path) -> dict[str, str]:
    ext = path.suffix.lower()
    if ext == ".epub":
        return _read_epub(path)
    if ext == ".pdf":
        return _read_pdf(path)
    if ext == ".fb2":
        return _read_fb2(path)
    if ext in (".mobi", ".azw"):
        return _read_mobi(path)
    return {}


def _write_ebook(path: Path, tags: dict[str, str]) -> None:
    ext = path.suffix.lower()
    if ext == ".epub":
        _write_epub(path, tags)
    elif ext == ".pdf":
        _write_pdf(path, tags)
    elif ext == ".fb2":
        _write_fb2(path, tags)
    # mobi/azw: write not supported


def _read_epub(path: Path) -> dict[str, str]:
    book = epub.read_epub(str(path))
    mapping = [
        ("title", "title"), ("artist", "creator"),
        ("album", "publisher"), ("date", "date"), ("genre", "subject"),
    ]
    result: dict[str, str] = {}
    for field_key, dc_key in mapping:
        items = book.get_metadata("DC", dc_key)
        if items:
            result[field_key] = str(items[0][0])
    return result


def _write_epub(path: Path, tags: dict[str, str]) -> None:
    book = epub.read_epub(str(path))
    dc_map = {
        "title": "title", "artist": "creator",
        "album": "publisher", "date": "date", "genre": "subject",
    }
    for field_key, dc_key in dc_map.items():
        if field_key in tags:
            book.set_unique_metadata("DC", dc_key, tags[field_key])
    epub.write_epub(str(path), book)


def _read_pdf(path: Path) -> dict[str, str]:
    reader = PdfReader(str(path))
    meta = reader.metadata
    mapping = [
        ("title", meta.title),
        ("artist", meta.author),
        ("genre", meta.subject),
        ("albumartist", meta.creator),
    ]
    return {k: v for k, v in mapping if v}


def _write_pdf(path: Path, tags: dict[str, str]) -> None:
    reader = PdfReader(str(path))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({
        "/Title": tags.get("title", ""),
        "/Author": tags.get("artist", ""),
        "/Subject": tags.get("genre", ""),
        "/Creator": tags.get("albumartist", ""),
    })
    with open(str(path), "wb") as f:
        writer.write(f)


def _read_fb2(path: Path) -> dict[str, str]:
    import xml.etree.ElementTree as ET
    ns = {"fb": "http://www.gribuser.ru/xml/fictionbook/2.0"}
    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
        title_info = root.find(".//fb:title-info", ns)
        if title_info is None:
            return {}
        result: dict[str, str] = {}
        bt = title_info.find("fb:book-title", ns)
        if bt is not None and bt.text:
            result["title"] = bt.text
        author = title_info.find("fb:author", ns)
        if author is not None:
            fn = author.find("fb:first-name", ns)
            ln = author.find("fb:last-name", ns)
            name = " ".join(
                p for p in [
                    fn.text if fn is not None else "",
                    ln.text if ln is not None else "",
                ] if p
            ).strip()
            if name:
                result["artist"] = name
        return result
    except ET.ParseError:
        return {}


def _write_fb2(path: Path, tags: dict[str, str]) -> None:
    import xml.etree.ElementTree as ET
    ns = {"fb": "http://www.gribuser.ru/xml/fictionbook/2.0"}
    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
        title_info = root.find(".//fb:title-info", ns)
        if title_info is None:
            return
        if "title" in tags:
            bt = title_info.find("fb:book-title", ns)
            if bt is not None:
                bt.text = tags["title"]
        tree.write(str(path), xml_declaration=True, encoding="utf-8")
    except ET.ParseError:
        pass


def _read_mobi(path: Path) -> dict[str, str]:
    try:
        import mobi
        import glob
        import xml.etree.ElementTree as ET
        _, extracted_dir = mobi.extract(str(path))
        opf_files = glob.glob(f"{extracted_dir}/*.opf")
        if not opf_files:
            return {}
        tree = ET.parse(opf_files[0])
        root = tree.getroot()
        ns = {"dc": "http://purl.org/dc/elements/1.1/"}
        result: dict[str, str] = {}
        t = root.find(".//dc:title", ns)
        if t is not None and t.text:
            result["title"] = t.text
        a = root.find(".//dc:creator", ns)
        if a is not None and a.text:
            result["artist"] = a.text
        return result
    except Exception:
        return {}
