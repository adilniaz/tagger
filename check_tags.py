#!/usr/bin/env python3
"""
check_tags.py — check tag consistency against filenames.

Expected filename format:  {artist} - {title}.{ext}

Rules checked:
  title       must match the title portion of the filename
  artist      must match the artist portion of the filename
  albumartist must match the artist portion of the filename

Comparison is case-insensitive and whitespace-normalised.
Files whose names don't contain " - " are skipped.

Usage:
  python check_tags.py <path> [<path> ...]

  Each <path> can be a file or a directory (scanned non-recursively).
  Pass -r / --recursive to scan directories recursively.
  Pass -f / --fix to write corrected tags back to the files.

Exit code:
  0  no mismatches found (or all fixed successfully)
  1  at least one mismatch found (or fix failed for at least one file)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.tag_io import SUPPORTED_EXTENSIONS, read, write

# ── helpers ──────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _parse_filename(path: Path) -> tuple[str, str] | None:
    """Return (artist, title) from 'artist - title.ext', or None if pattern absent."""
    stem = path.stem
    if " - " not in stem:
        return None
    artist, title = stem.split(" - ", maxsplit=1)
    return artist.strip(), title.strip()


# ── per-file check ────────────────────────────────────────────────────────────

class _Issue:
    def __init__(self, field: str, found: str, expected: str) -> None:
        self.field = field
        self.found = found
        self.expected = expected

    def __str__(self) -> str:
        found_str = f'"{self.found}"' if self.found else "(missing)"
        return f"  {self.field + ':':<16} {found_str}  →  expected \"{self.expected}\""


def check_file(path: Path) -> list[_Issue]:
    parsed = _parse_filename(path)
    if parsed is None:
        return []

    expected_artist, expected_title = parsed

    try:
        tags = read(path)
    except Exception as exc:
        return [_Issue("(read error)", str(exc), "")]

    issues: list[_Issue] = []

    def _check(field: str, label: str, expected: str, required: bool) -> None:
        actual = tags.get(field, "").strip()
        if not actual:
            if required:
                issues.append(_Issue(label, "", expected))
        elif _norm(actual) != _norm(expected):
            issues.append(_Issue(label, actual, expected))

    _check("title",       "title",        expected_title,  required=True)
    _check("artist",      "artist",       expected_artist, required=True)
    _check("albumartist", "album artist", expected_artist, required=True)

    return issues


def fix_file(path: Path) -> list[_Issue]:
    """Apply corrections derived from the filename. Returns the issues that were fixed."""
    issues = check_file(path)
    if not issues:
        return []

    parsed = _parse_filename(path)
    assert parsed is not None  # check_file already returned early when None

    expected_artist, expected_title = parsed
    corrections: dict[str, str] = {}
    for issue in issues:
        if issue.field == "title":
            corrections["title"] = expected_title
        elif issue.field == "artist":
            corrections["artist"] = expected_artist
        elif issue.field == "album artist":
            corrections["albumartist"] = expected_artist

    try:
        write(path, corrections)
    except Exception as exc:
        return [_Issue("(write error)", str(exc), "")]

    return issues


# ── path collection ───────────────────────────────────────────────────────────

def _collect(roots: list[Path], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            if root.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(root)
        elif root.is_dir():
            glob = root.rglob("*") if recursive else root.iterdir()
            files.extend(
                sorted(
                    p for p in glob
                    if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
                )
            )
    return files


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check audio tag consistency against filenames."
    )
    parser.add_argument("paths", nargs="+", metavar="path")
    parser.add_argument(
        "-r", "--recursive", action="store_true",
        help="Scan directories recursively",
    )
    parser.add_argument(
        "-f", "--fix", action="store_true",
        help="Write corrected tags back to files",
    )
    args = parser.parse_args()

    files = _collect([Path(p) for p in args.paths], args.recursive)
    if not files:
        print("No supported audio/ebook files found.")
        sys.exit(0)

    n_ok = n_mismatch = 0
    n_fixed = n_fix_error = 0
    skipped: list[Path] = []

    for path in files:
        if _parse_filename(path) is None:
            skipped.append(path)
            continue

        issues = check_file(path)
        if not issues:
            n_ok += 1
            continue

        n_mismatch += 1
        print(path.name)
        for issue in issues:
            print(issue)

        if args.fix:
            fixed = fix_file(path)
            write_errors = [i for i in fixed if i.field == "(write error)"]
            if write_errors:
                n_fix_error += 1
                print(f"  ERROR fixing: {write_errors[0].found}")
            else:
                n_fixed += 1
                print("  -> fixed")

        print()

    total_checked = n_ok + n_mismatch
    parts = [
        f"{n_mismatch} mismatch{'es' if n_mismatch != 1 else ''}",
        f"{total_checked} file{'s' if total_checked != 1 else ''} checked",
        f"{n_ok} OK",
    ]
    if args.fix and n_fixed:
        parts.append(f"{n_fixed} fixed")
    if args.fix and n_fix_error:
        parts.append(f"{n_fix_error} fix error{'s' if n_fix_error != 1 else ''}")
    if skipped:
        parts.append(f"{len(skipped)} skipped (no 'artist - title' pattern)")
    print("  ".join(parts))
    for p in skipped:
        print(f"  skipped: {p.name}")

    sys.exit(1 if (n_mismatch and not args.fix) or n_fix_error else 0)


if __name__ == "__main__":
    main()
