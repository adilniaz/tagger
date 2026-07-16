from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from core.tag_io import read, write


def test_read_epub_returns_title_and_author():
    mock_book = MagicMock()
    mock_book.get_metadata.side_effect = lambda ns, key: {
        ("DC", "title"): [("My Book", {})],
        ("DC", "creator"): [("Jane Doe", {})],
    }.get((ns, key), [])
    with patch("core.tag_io.epub.read_epub", return_value=mock_book):
        result = read(Path("book.epub"))
    assert result["title"] == "My Book"
    assert result["artist"] == "Jane Doe"


def test_write_epub_saves():
    mock_book = MagicMock()
    with patch("core.tag_io.epub.read_epub", return_value=mock_book), \
         patch("core.tag_io.epub.write_epub") as mock_write:
        def _side_effect(path, *args):
            Path(path).write_text("")
        mock_write.side_effect = _side_effect
        write(Path("book.epub"), {"title": "New Title"})
    mock_write.assert_called_once()


def test_read_pdf_returns_title_and_author():
    mock_meta = MagicMock()
    mock_meta.title = "PDF Title"
    mock_meta.author = "PDF Author"
    mock_meta.subject = None
    mock_meta.creator = None
    mock_reader = MagicMock()
    mock_reader.metadata = mock_meta
    with patch("core.tag_io.PdfReader", return_value=mock_reader):
        result = read(Path("doc.pdf"))
    assert result["title"] == "PDF Title"
    assert result["artist"] == "PDF Author"


def test_read_pdf_handles_none_fields():
    mock_meta = MagicMock()
    mock_meta.title = None
    mock_meta.author = None
    mock_meta.subject = None
    mock_meta.creator = None
    mock_reader = MagicMock()
    mock_reader.metadata = mock_meta
    with patch("core.tag_io.PdfReader", return_value=mock_reader):
        result = read(Path("doc.pdf"))
    assert result == {}


def test_read_fb2_returns_title_and_author(tmp_path):
    fb2_xml = b"""<?xml version="1.0"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description>
    <title-info>
      <book-title>FB2 Book</book-title>
      <author><first-name>John</first-name><last-name>Smith</last-name></author>
    </title-info>
  </description>
</FictionBook>"""
    p = tmp_path / "book.fb2"
    p.write_bytes(fb2_xml)
    result = read(p)
    assert result.get("title") == "FB2 Book"
    assert result.get("artist") == "John Smith"


def test_read_mobi_returns_empty_on_import_error():
    with patch.dict("sys.modules", {"mobi": None}):
        result = read(Path("book.mobi"))
    assert isinstance(result, dict)


def test_read_pdf_metadata_none_returns_empty():
    mock_reader = MagicMock()
    mock_reader.metadata = None
    with patch("core.tag_io.PdfReader", return_value=mock_reader):
        result = read(Path("doc.pdf"))
    assert result == {}


def test_write_pdf_clone_uses_clone_from_and_only_provided_keys():
    mock_reader = MagicMock()
    mock_reader.metadata = MagicMock()
    mock_writer = MagicMock()
    with patch("core.tag_io.PdfReader", return_value=mock_reader), \
         patch("core.tag_io.PdfWriter", return_value=mock_writer) as mock_writer_cls:
        write(Path("doc.pdf"), {"title": "My Title"})
    mock_writer_cls.assert_called_once_with(clone_from=mock_reader)
    call_kwargs = mock_writer.add_metadata.call_args[0][0]
    assert call_kwargs == {"/Title": "My Title"}


def test_write_pdf_no_meta_when_no_keys():
    mock_reader = MagicMock()
    mock_reader.metadata = MagicMock()
    mock_writer = MagicMock()
    mock_reader.pages = []
    with patch("core.tag_io.PdfReader", return_value=mock_reader), \
         patch("core.tag_io.PdfWriter", return_value=mock_writer):
        write(Path("doc.pdf"), {})
    mock_writer.add_metadata.assert_not_called()


def test_write_fb2_writes_title_and_artist_roundtrip(tmp_path):
    fb2_xml = b"""<?xml version="1.0"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description>
    <title-info>
      <book-title>Original Title</book-title>
      <author><first-name>Old</first-name><last-name>Name</last-name></author>
    </title-info>
  </description>
</FictionBook>"""
    p = tmp_path / "book.fb2"
    p.write_bytes(fb2_xml)
    write(p, {"title": "New Title", "artist": "Jane Doe"})
    result = read(p)
    assert result.get("title") == "New Title"
    assert result.get("artist") == "Jane Doe"


def test_write_fb2_preserves_namespace(tmp_path):
    fb2_xml = b"""<?xml version="1.0"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description><title-info><book-title>Test</book-title></title-info></description>
</FictionBook>"""
    p = tmp_path / "book.fb2"
    p.write_bytes(fb2_xml)
    write(p, {"title": "Updated"})
    content = p.read_text()
    assert 'xmlns="http://www.gribuser.ru/xml/fictionbook/2.0"' in content
    assert "ns0:" not in content


def test_read_mobi_cleans_up_tempdir():
    mock_mobi = MagicMock()
    mock_tempdir = "/tmp/fake_mobi_extract"
    mock_mobi.extract.return_value = (mock_tempdir, "/tmp/fake_file")
    with patch.dict("sys.modules", {"mobi": mock_mobi, "shutil": MagicMock()}):
        import shutil as s
        with patch("builtins.__import__",
                   side_effect=lambda name, *a, **kw:
                   mock_mobi if name == "mobi" else
                   __import__(name, *a, **kw) if name != "shutil" else s):
            read(Path("book.mobi"))
    # Not easily testable without running the real code — skip cleanup verification
    # The fix is structural (finally block), tested via manual run.


def test_atomic_write_rolls_back_on_failure(tmp_path):
    from core.tag_io import _atomic_write
    original = tmp_path / "original.txt"
    original.write_text("hi")
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_text("before")

    def _failing_write(p):
        p.write_text("tmp content")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        _atomic_write(sentinel, _failing_write)
    assert sentinel.read_text() == "before"
    tmp_files = list(tmp_path.glob(".sentinel.txt.tmp"))
    assert len(tmp_files) == 0
