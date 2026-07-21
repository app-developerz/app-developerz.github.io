#!/usr/bin/env python3
"""
Rebuild the Scripture Reader hosted Bible data from data/kjv-flat.json.

Run from the repository root:

    python tools/build-bible-data.py
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BOOKS_DIR = DATA_DIR / "books"
SOURCE = DATA_DIR / "kjv-flat.json"

BASE_URL = "https://app-developerz.github.io/data"
DATA_VERSION = "1.0.0"
SCHEMA_VERSION = 1

BOOK_ORDER = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation",
]


def slugify(book: str) -> str:
    return book.lower().replace("'", "").replace(" ", "-")


def write_json(path: Path, payload: Any, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        )
        handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    with SOURCE.open("r", encoding="utf-8") as handle:
        verses = json.load(handle)

    if len(verses) != 31102:
        raise ValueError(f"Expected 31,102 verses, found {len(verses):,}")

    order_lookup = {book: index + 1 for index, book in enumerate(BOOK_ORDER)}
    grouped = defaultdict(lambda: defaultdict(list))

    for item in verses:
        book = item["book"]
        grouped[book][int(item["chapter"])].append(
            OrderedDict(
                [
                    ("verse", int(item["verse"])),
                    ("reference", item["reference"]),
                    ("text", item["text"]),
                ]
            )
        )

    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in BOOKS_DIR.glob("*.json"):
        old_file.unlink()

    book_index = []
    total_chapters = 0
    total_verses = 0

    for book in BOOK_ORDER:
        chapters = []
        book_verse_count = 0

        for chapter_number in sorted(grouped[book]):
            chapter_verses = sorted(
                grouped[book][chapter_number],
                key=lambda entry: entry["verse"],
            )
            chapters.append(
                OrderedDict(
                    [
                        ("chapter", chapter_number),
                        ("verseCount", len(chapter_verses)),
                        ("verses", chapter_verses),
                    ]
                )
            )
            book_verse_count += len(chapter_verses)

        slug = slugify(book)
        testament = "Old" if order_lookup[book] <= 39 else "New"
        relative_path = f"books/{slug}.json"

        payload = OrderedDict(
            [
                ("schemaVersion", SCHEMA_VERSION),
                ("dataVersion", DATA_VERSION),
                ("translation", "KJV"),
                (
                    "book",
                    OrderedDict(
                        [
                            ("order", order_lookup[book]),
                            ("name", book),
                            ("slug", slug),
                            ("testament", testament),
                            ("chapterCount", len(chapters)),
                            ("verseCount", book_verse_count),
                        ]
                    ),
                ),
                ("chapters", chapters),
            ]
        )
        write_json(BOOKS_DIR / f"{slug}.json", payload)

        book_index.append(
            OrderedDict(
                [
                    ("order", order_lookup[book]),
                    ("name", book),
                    ("slug", slug),
                    ("testament", testament),
                    ("chapterCount", len(chapters)),
                    ("verseCount", book_verse_count),
                    ("path", relative_path),
                    ("url", f"{BASE_URL}/{relative_path}"),
                ]
            )
        )

        total_chapters += len(chapters)
        total_verses += book_verse_count

    if total_chapters != 1189 or total_verses != 31102:
        raise ValueError(
            f"Validation failed: chapters={total_chapters}, verses={total_verses}"
        )

    index_payload = OrderedDict(
        [
            ("schemaVersion", SCHEMA_VERSION),
            ("dataVersion", DATA_VERSION),
            (
                "translation",
                OrderedDict(
                    [
                        ("id", "kjv"),
                        ("name", "King James Version"),
                        ("language", "en"),
                    ]
                ),
            ),
            (
                "totals",
                OrderedDict(
                    [
                        ("books", 66),
                        ("chapters", total_chapters),
                        ("verses", total_verses),
                        ("oldTestamentVerses", 23145),
                        ("newTestamentVerses", 7957),
                    ]
                ),
            ),
            ("bookFileFormat", "grouped-chapters-v1"),
            ("booksBaseUrl", f"{BASE_URL}/books"),
            ("books", book_index),
        ]
    )
    write_json(DATA_DIR / "index.json", index_payload, pretty=True)

    manifest_files = []
    for path in sorted(DATA_DIR.rglob("*.json")):
        if path.name == "manifest.json":
            continue
        manifest_files.append(
            OrderedDict(
                [
                    ("path", path.relative_to(ROOT).as_posix()),
                    ("bytes", path.stat().st_size),
                    ("sha256", sha256_file(path)),
                ]
            )
        )

    write_json(
        DATA_DIR / "manifest.json",
        OrderedDict(
            [
                ("schemaVersion", SCHEMA_VERSION),
                ("dataVersion", DATA_VERSION),
                ("fileCount", len(manifest_files)),
                ("files", manifest_files),
            ]
        ),
        pretty=True,
    )

    print("Build complete")
    print(f"Books: {len(book_index)}")
    print(f"Chapters: {total_chapters}")
    print(f"Verses: {total_verses}")


if __name__ == "__main__":
    main()
