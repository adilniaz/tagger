from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from check_tags import _parse_filename, _norm, check_file


def test_parse_filename_returns_artist_title():
    result = _parse_filename(Path("/home/user/Artist - Title.mp3"))
    assert result == ("Artist", "Title")


def test_parse_filename_ignores_extra_dashes():
    result = _parse_filename(Path("/home/user/A - B - C.flac"))
    assert result == ("A", "B - C")


def test_parse_filename_skips_no_separator():
    assert _parse_filename(Path("/home/user/notitle.mp3")) is None
    assert _parse_filename(Path("/home/user/nodash.flac")) is None


def test_norm_strips_whitespace_and_lowercases():
    assert _norm("  Hello  World  ") == "hello world"
    assert _norm("CAPS") == "caps"


def test_check_file_ok_when_tags_match():
    tags = {"title": "Song", "artist": "Band", "albumartist": "Band"}
    with patch("check_tags.read", return_value=tags):
        issues = check_file(Path("/tmp/Band - Song.mp3"))
    assert len(issues) == 0


def test_check_file_detects_mismatch():
    tags = {"title": "Wrong", "artist": "Band", "albumartist": "Band"}
    with patch("check_tags.read", return_value=tags):
        issues = check_file(Path("/tmp/Band - Song.mp3"))
    field_names = [i.field for i in issues]
    assert "title" in field_names


def test_check_file_skips_unnamed():
    assert len(check_file(Path("/tmp/notagpattern.mp3"))) == 0
