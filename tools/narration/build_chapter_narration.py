#!/usr/bin/env python3
"""
Create seamless chapter MP3 files from existing per-verse narration.

This Python 3.13-compatible implementation uses:
- FFmpeg for MP3 decoding, edge-silence trimming, and MP3 encoding;
- Python's built-in wave module for PCM concatenation and exact timing;
- no pydub and no audioop/pyaudioop dependency.

Example:
    python build_chapter_narration.py --book Genesis
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any

try:
    import imageio_ffmpeg
except ImportError as error:
    print(
        "Unable to import imageio-ffmpeg.\n"
        f"Python executable: {sys.executable}\n"
        f"Import error: {type(error).__name__}: {error}",
        file=sys.stderr,
    )
    raise SystemExit(2)


DEFAULT_PUBLIC_BASE_URL = (
    "https://app-developerz.github.io/audio/kjv-chapters"
)

SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"JSON file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid JSON in {path}: {error}") from error


def find_book(index_data: dict[str, Any], requested: str) -> dict[str, Any]:
    wanted = requested.strip().lower()

    for book in index_data.get("books", []):
        if (
            str(book.get("name", "")).lower() == wanted
            or str(book.get("slug", "")).lower() == wanted
        ):
            return book

    raise RuntimeError(f"Book not found in index: {requested}")


def run_process(command: list[str], description: str) -> None:
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise RuntimeError(
            f"{description} failed with exit code {completed.returncode}.\n"
            f"{stderr}"
        )


def decode_and_trim_verse(
    ffmpeg: str,
    source_mp3: Path,
    output_wav: Path,
    *,
    threshold_db: float,
    minimum_silence_ms: int,
    keep_silence_ms: int,
) -> None:
    minimum_seconds = minimum_silence_ms / 1000.0
    keep_seconds = keep_silence_ms / 1000.0

    # The stop_periods=-1 form removes only qualifying trailing silence while
    # retaining speech pauses within the verse. start/stop_silence retains a
    # small amount of natural breathing room.
    audio_filter = (
        "silenceremove="
        f"start_periods=1:"
        f"start_duration={minimum_seconds:.3f}:"
        f"start_threshold={threshold_db}dB:"
        f"start_silence={keep_seconds:.3f}:"
        f"stop_periods=-1:"
        f"stop_duration={minimum_seconds:.3f}:"
        f"stop_threshold={threshold_db}dB:"
        f"stop_silence={keep_seconds:.3f}"
    )

    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source_mp3),
        "-af",
        audio_filter,
        "-ar",
        str(SAMPLE_RATE),
        "-ac",
        str(CHANNELS),
        "-c:a",
        "pcm_s16le",
        str(output_wav),
    ]
    run_process(command, f"Decoding {source_mp3}")


def read_pcm_wav(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as reader:
        channels = reader.getnchannels()
        sample_width = reader.getsampwidth()
        sample_rate = reader.getframerate()
        frame_count = reader.getnframes()

        if channels != CHANNELS:
            raise RuntimeError(
                f"Unexpected channel count in {path}: {channels}"
            )
        if sample_width != SAMPLE_WIDTH:
            raise RuntimeError(
                f"Unexpected sample width in {path}: {sample_width}"
            )
        if sample_rate != SAMPLE_RATE:
            raise RuntimeError(
                f"Unexpected sample rate in {path}: {sample_rate}"
            )

        return reader.readframes(frame_count), frame_count


def silence_frames(milliseconds: int) -> tuple[bytes, int]:
    if milliseconds <= 0:
        return b"", 0

    frame_count = round(SAMPLE_RATE * milliseconds / 1000.0)
    byte_count = frame_count * CHANNELS * SAMPLE_WIDTH
    return b"\x00" * byte_count, frame_count


def encode_chapter_mp3(
    ffmpeg: str,
    source_wav: Path,
    output_mp3: Path,
    bitrate: str,
) -> None:
    temporary_mp3 = output_mp3.with_name(
        output_mp3.stem + ".part.mp3"
    )

    if temporary_mp3.exists():
        temporary_mp3.unlink()

    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source_wav),
        "-ar",
        str(SAMPLE_RATE),
        "-ac",
        str(CHANNELS),
        "-c:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        "-write_xing",
        "1",
        "-f",
        "mp3",
        str(temporary_mp3),
    ]
    run_process(command, f"Encoding {output_mp3}")

    if not temporary_mp3.exists() or temporary_mp3.stat().st_size == 0:
        raise RuntimeError(f"FFmpeg produced an empty file: {temporary_mp3}")

    temporary_mp3.replace(output_mp3)


def build_chapter(
    *,
    ffmpeg: str,
    book_data: dict[str, Any],
    chapter_data: dict[str, Any],
    verse_audio_root: Path,
    output_root: Path,
    public_base_url: str,
    gap_ms: int,
    threshold_db: float,
    minimum_silence_ms: int,
    keep_silence_ms: int,
    bitrate: str,
    overwrite: bool,
) -> tuple[str, int]:
    book = book_data["book"]
    book_name = str(book["name"])
    book_slug = str(book["slug"])
    chapter_number = int(chapter_data["chapter"])

    output_directory = output_root / book_slug
    output_directory.mkdir(parents=True, exist_ok=True)

    mp3_path = output_directory / f"{chapter_number}.mp3"
    json_path = output_directory / f"{chapter_number}.json"

    if (
        not overwrite
        and mp3_path.exists()
        and mp3_path.stat().st_size > 0
        and json_path.exists()
        and json_path.stat().st_size > 0
    ):
        print(f"SKIP  {book_name} {chapter_number}: chapter files already exist")
        return "skipped", int(chapter_data["verseCount"])

    timing_entries: list[dict[str, Any]] = []
    verse_count = len(chapter_data["verses"])
    gap_bytes, gap_frames = silence_frames(gap_ms)
    total_frames = 0

    with tempfile.TemporaryDirectory(
        prefix=f"scripture-{book_slug}-{chapter_number}-"
    ) as temporary_directory:
        temp_root = Path(temporary_directory)
        chapter_wav = temp_root / "chapter.wav"

        with wave.open(str(chapter_wav), "wb") as writer:
            writer.setnchannels(CHANNELS)
            writer.setsampwidth(SAMPLE_WIDTH)
            writer.setframerate(SAMPLE_RATE)

            for verse_index, verse_data in enumerate(chapter_data["verses"]):
                verse_number = int(verse_data["verse"])
                reference = str(verse_data["reference"])
                verse_path = (
                    verse_audio_root
                    / book_slug
                    / str(chapter_number)
                    / f"{verse_number}.mp3"
                )

                if not verse_path.exists() or verse_path.stat().st_size == 0:
                    raise RuntimeError(
                        f"Missing verse narration for {reference}: {verse_path}"
                    )

                verse_wav = temp_root / f"verse-{verse_number}.wav"
                decode_and_trim_verse(
                    ffmpeg,
                    verse_path,
                    verse_wav,
                    threshold_db=threshold_db,
                    minimum_silence_ms=minimum_silence_ms,
                    keep_silence_ms=keep_silence_ms,
                )

                pcm_data, verse_frames = read_pcm_wav(verse_wav)
                start_seconds = total_frames / SAMPLE_RATE

                writer.writeframesraw(pcm_data)
                total_frames += verse_frames

                end_seconds = total_frames / SAMPLE_RATE
                duration_seconds = verse_frames / SAMPLE_RATE

                timing_entries.append(
                    {
                        "verseIndex": verse_index,
                        "verse": verse_number,
                        "reference": reference,
                        "startSeconds": round(start_seconds, 3),
                        "endSeconds": round(end_seconds, 3),
                        "durationSeconds": round(duration_seconds, 3),
                    }
                )

                if verse_index < verse_count - 1 and gap_frames > 0:
                    writer.writeframesraw(gap_bytes)
                    total_frames += gap_frames

        encode_chapter_mp3(
            ffmpeg,
            chapter_wav,
            mp3_path,
            bitrate,
        )

    public_base_url = public_base_url.rstrip("/")
    audio_url = (
        f"{public_base_url}/{book_slug}/{chapter_number}.mp3"
    )

    timing_payload = {
        "schemaVersion": 1,
        "translation": "KJV",
        "book": {
            "name": book_name,
            "slug": book_slug,
        },
        "chapter": chapter_number,
        "verseCount": verse_count,
        "audioUrl": audio_url,
        "durationSeconds": round(total_frames / SAMPLE_RATE, 3),
        "transition": {
            "gapMilliseconds": gap_ms,
            "silenceThresholdDb": threshold_db,
            "minimumSilenceMilliseconds": minimum_silence_ms,
            "keptEdgeSilenceMilliseconds": keep_silence_ms,
        },
        "audio": {
            "sampleRate": SAMPLE_RATE,
            "channels": CHANNELS,
            "bitrate": bitrate,
        },
        "verses": timing_entries,
    }

    json_path.write_text(
        json.dumps(timing_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(
        f"DONE  {book_name} {chapter_number}: "
        f"{verse_count} verses, {total_frames / SAMPLE_RATE:.1f}s"
    )
    return "generated", verse_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build continuous chapter narration and verse timing JSON "
            "from existing per-verse MP3 files."
        )
    )
    parser.add_argument(
        "--book",
        action="append",
        required=True,
        help='Book name or slug. May be repeated, for example --book "Genesis".',
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
        help="Path to the website repository's data directory.",
    )
    parser.add_argument(
        "--verse-audio-root",
        type=Path,
        required=True,
        help="Path to audio/kjv containing per-verse MP3 files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for continuous chapter MP3 and JSON files.",
    )
    parser.add_argument(
        "--public-base-url",
        default=DEFAULT_PUBLIC_BASE_URL,
    )
    parser.add_argument(
        "--gap-ms",
        type=int,
        default=180,
        help="Pause inserted between verses. Default: 180 ms.",
    )
    parser.add_argument(
        "--silence-threshold-db",
        type=float,
        default=-45.0,
        help="Edge-silence threshold. Default: -45 dBFS.",
    )
    parser.add_argument(
        "--minimum-silence-ms",
        type=int,
        default=100,
        help="Minimum edge silence to detect. Default: 100 ms.",
    )
    parser.add_argument(
        "--keep-silence-ms",
        type=int,
        default=80,
        help="Natural edge breathing room retained. Default: 80 ms.",
    )
    parser.add_argument(
        "--bitrate",
        default="48k",
        help="Output MP3 bitrate. Default: 48k.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing chapter MP3 and timing JSON files.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.gap_ms < 0:
        raise RuntimeError("--gap-ms cannot be negative.")
    if args.minimum_silence_ms < 1:
        raise RuntimeError("--minimum-silence-ms must be positive.")
    if args.keep_silence_ms < 0:
        raise RuntimeError("--keep-silence-ms cannot be negative.")

    data_root = args.data_root.resolve()
    verse_audio_root = args.verse_audio_root.resolve()
    output_root = args.output.resolve()
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    print(f"Python:        {sys.executable}")
    print(f"FFmpeg:        {ffmpeg}")
    print(f"Verse audio:   {verse_audio_root}")
    print(f"Chapter output:{output_root}")
    print(f"Verse gap:     {args.gap_ms} ms")

    generated = 0
    skipped = 0
    total_verses = 0
    index_data = load_json(data_root / "index.json")

    for requested_book in args.book:
        book_info = find_book(index_data, requested_book)
        book_path = data_root / str(book_info["path"])
        book_data = load_json(book_path)

        print()
        print("=" * 72)
        print(f'BUILDING {book_info["name"].upper()} CHAPTER AUDIO')
        print("=" * 72)

        for chapter_data in book_data["chapters"]:
            status, verse_count = build_chapter(
                ffmpeg=ffmpeg,
                book_data=book_data,
                chapter_data=chapter_data,
                verse_audio_root=verse_audio_root,
                output_root=output_root,
                public_base_url=args.public_base_url,
                gap_ms=args.gap_ms,
                threshold_db=args.silence_threshold_db,
                minimum_silence_ms=args.minimum_silence_ms,
                keep_silence_ms=args.keep_silence_ms,
                bitrate=args.bitrate,
                overwrite=args.overwrite,
            )
            total_verses += verse_count

            if status == "generated":
                generated += 1
            else:
                skipped += 1

        book_slug = str(book_data["book"]["slug"])
        manifest = {
            "schemaVersion": 1,
            "translation": "KJV",
            "book": book_data["book"],
            "chapterFilePattern": "{chapter}.mp3",
            "timingFilePattern": "{chapter}.json",
            "publicBaseUrl": (
                args.public_base_url.rstrip("/") + "/" + book_slug
            ),
            "buildSettings": {
                "gapMilliseconds": args.gap_ms,
                "silenceThresholdDb": args.silence_threshold_db,
                "minimumSilenceMilliseconds": args.minimum_silence_ms,
                "keptEdgeSilenceMilliseconds": args.keep_silence_ms,
                "bitrate": args.bitrate,
            },
        }
        manifest_path = output_root / book_slug / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    print()
    print("=" * 72)
    print("CHAPTER BUILD COMPLETE")
    print("=" * 72)
    print(f"Generated chapters: {generated}")
    print(f"Skipped chapters:   {skipped}")
    print(f"Processed verses:   {total_verses}")
    print(f"Output:              {output_root}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nChapter build stopped. Completed files were preserved.")
        raise SystemExit(130)
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
