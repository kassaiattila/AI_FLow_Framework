"""Cubix Course Capture skill - standalone entry point.

Usage:
    # Transcript pipeline (process existing video/audio files):
    python -m skills.cubix_course_capture transcript --input video.mkv --output ./output/Cubix_ML_Course

    # Full course capture (RPA + transcript):
    python -m skills.cubix_course_capture capture --url "https://cubixedu.com/kepzes/..." --course Cubix_ML_Course
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def run_transcript(input_path: str, output_dir: str, course_name: str) -> None:
    """Process a single video/audio file through the transcript pipeline."""
    import json

    from skills.cubix_course_capture.workflows.transcript_pipeline import (
        chunk_audio,
        config,
        extract_audio,
        merge_transcripts,
        probe_audio,
        structure_transcript,
        transcribe,
    )

    file_path = Path(input_path)
    if not file_path.exists():
        print(f"Fajl nem talalhato: {input_path}")
        return

    out_dir = Path(output_dir) / course_name
    config.output_dir = str(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Cubix Transcript Pipeline")
    print(f"Input: {file_path.name} ({file_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"Output: {out_dir}")
    print()

    data = {"file_path": str(file_path)}

    r1 = await probe_audio(data)
    print(f"1. Probe: {r1['duration_seconds']:.1f}s")

    r2 = await extract_audio({**data, **r1})
    print(f"2. Audio: {r2['file_size_bytes'] / 1024 / 1024:.1f} MB")

    r3 = await chunk_audio(r2)
    print(f"3. Chunk: {r3['total_chunks']} darab")

    r4 = await transcribe(r3)
    cost = sum(c.get("cost", 0) for c in r4["chunk_transcripts"])
    print(f"4. STT: ${cost:.4f}")

    r5 = await merge_transcripts({**r4, "title": file_path.stem})
    print(f"5. Merge: {len(r5.get('segments', []))} szegmens")

    r6 = await structure_transcript({"merged_transcript": r5, "title": file_path.stem})
    print(f"6. Struktura: {r6.get('summary', '')[:100]}")

    # Save outputs
    slug = file_path.stem.replace(" ", "_")
    lesson_dir = out_dir / slug
    lesson_dir.mkdir(parents=True, exist_ok=True)

    (lesson_dir / "structured.json").write_text(
        json.dumps(r6, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (lesson_dir / "transcript.txt").write_text(
        r5.get("full_text", ""), encoding="utf-8"
    )

    srt = r5.get("srt_content", "")
    if srt:
        (lesson_dir / "transcript.srt").write_text(srt, encoding="utf-8")

    print(f"\nKesz! Output: {lesson_dir}")


async def run_capture(url: str, course_name: str, output_dir: str) -> None:
    """Run full course capture (RPA + transcript)."""
    from skills.cubix_course_capture.models import CourseConfig
    from skills.cubix_course_capture.workflows.course_capture import process_course

    config = CourseConfig(
        course_name=course_name,
        course_url=url,
        output_base_dir=output_dir,
    )

    print("Cubix Course Capture")
    print(f"URL: {url}")
    print(f"Course: {course_name}")
    print(f"Output: {output_dir}/{course_name}")
    print()

    result = await process_course(config)
    print(f"Kesz! Eredmeny: {result.get('total_lessons', '?')} lecke feldolgozva")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cubix Course Capture")
    sub = parser.add_subparsers(dest="command", help="Command")

    # transcript subcommand
    tp = sub.add_parser("transcript", help="Process video/audio -> structured transcript")
    tp.add_argument("--input", "-i", required=True, help="Video/audio file path")
    tp.add_argument("--output", "-o", default="./output", help="Output base directory")
    tp.add_argument("--course", "-c", default="Cubix_ML_Course", help="Course name")

    # capture subcommand
    cp = sub.add_parser("capture", help="Full RPA course capture + transcript")
    cp.add_argument("--url", "-u", required=True, help="Course URL")
    cp.add_argument("--course", "-c", default="Cubix_ML_Course", help="Course name")
    cp.add_argument("--output", "-o", default="./output", help="Output base directory")

    args = parser.parse_args()

    if args.command == "transcript":
        asyncio.run(run_transcript(args.input, args.output, args.course))
    elif args.command == "capture":
        asyncio.run(run_capture(args.url, args.course, args.output))
    else:
        parser.print_help()
