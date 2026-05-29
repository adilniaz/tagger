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
