#!/usr/bin/env python3
"""Test the Cubix ML Course transcript pipeline end-to-end.

Processes the 2 smallest MKV files from the ml_w7_8 folder
using the full transcript pipeline (probe -> extract -> chunk -> transcribe -> merge -> structure).

Output: test_output/Cubix_ML_Course/week_07/lesson_XX_slug/

Usage:
    python scripts/test_ml_course_pipeline.py \
        --input-dir "C:/Users/kassaiattila/Videos/ml_w7_8" \
        --output-dir "./test_output" \
        --max-files 2
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env for OPENAI_API_KEY
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


async def main(args: argparse.Namespace) -> None:
    from skills.cubix_course_capture.workflows.transcript_pipeline import (
        probe_audio, extract_audio, chunk_audio, transcribe,
        merge_transcripts, structure_transcript, config,
    )
    from skills.cubix_course_capture.models import (
        PipelineState, FileProcessingState, StageStatus,
    )
    from skills.cubix_course_capture.state.file_state import FileStateManager

    input_path = Path(args.input_dir)
    course_name = args.course_name
    output_base = Path(args.output_dir) / course_name

    # Override config
    config.output_dir = str(output_base)

    # Find smallest MKV files
    mkv_files = sorted(input_path.glob("*.mkv"), key=lambda f: f.stat().st_size)
    files = mkv_files[:args.max_files]

    if not files:
        print(f"Nincs MKV fajl: {input_path}")
        return

    # Initialize state manager
    state_mgr = FileStateManager(output_dir=str(output_base))
    state = state_mgr.load()
    state.course_name = course_name
    state.course_url = "https://cubixedu.com/kepzes/ml-engineer-26q1"
    state.course_title = "Cubix ML Engineer Course - Week 7-8"

    print("=" * 70)
    print(f"  CUBIX ML COURSE - TRANSCRIPT PIPELINE TESZT")
    print(f"  Course: {course_name}")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_base}")
    print(f"  Fajlok: {len(files)}")
    print("=" * 70)

    total_cost = 0.0

    for i, file_path in enumerate(files):
        file_mb = file_path.stat().st_size / (1024 * 1024)
        slug = file_path.stem.replace(" ", "_").replace("-", "_")

        # Course-aware output path
        week_dir = f"week_07"
        lesson_dir = f"lesson_{i+1:02d}_{slug[:30]}"
        lesson_path = output_base / week_dir / lesson_dir
        lesson_path.mkdir(parents=True, exist_ok=True)

        # Init state for this file
        fs = state_mgr.init_file(state, i, slug, file_path.stem, week_index=7, lesson_index=i+1)

        print(f"\n{'-' * 60}")
        print(f"  [{i+1}/{len(files)}] {file_path.name} ({file_mb:.1f} MB)")
        print(f"  Output: {lesson_path}")
        print(f"{'-' * 60}")

        start = time.monotonic()
        data = {"file_path": str(file_path)}

        # Step 1: Probe
        try:
            state_mgr.set_stage(state, slug, "probe", StageStatus.IN_PROGRESS)
            state_mgr.save(state)
            r1 = await probe_audio(data)
            state_mgr.set_stage(state, slug, "probe", StageStatus.COMPLETED)
            dur_min = r1["duration_seconds"] / 60
            print(f"  1. Probe: {r1['duration_seconds']:.1f}s ({dur_min:.1f} perc)")
        except Exception as e:
            state_mgr.set_stage(state, slug, "probe", StageStatus.FAILED, str(e))
            state_mgr.save(state)
            print(f"  !! Probe HIBA: {e}")
            continue

        # Step 2: Extract audio
        try:
            state_mgr.set_stage(state, slug, "extract", StageStatus.IN_PROGRESS)
            state_mgr.save(state)
            r2 = await extract_audio({**data, **r1})
            state_mgr.set_stage(state, slug, "extract", StageStatus.COMPLETED)
            audio_mb = r2["file_size_bytes"] / (1024 * 1024)
            print(f"  2. Audio: {audio_mb:.1f} MB")

            # Copy/link audio to lesson dir
            import shutil
            audio_dest = lesson_path / f"audio.m4a"
            if Path(r2["audio_path"]).exists():
                shutil.copy2(r2["audio_path"], audio_dest)
        except Exception as e:
            state_mgr.set_stage(state, slug, "extract", StageStatus.FAILED, str(e))
            state_mgr.save(state)
            print(f"  !! Extract HIBA: {e}")
            continue

        # Step 3: Chunk
        try:
            state_mgr.set_stage(state, slug, "chunk", StageStatus.IN_PROGRESS)
            r3 = await chunk_audio(r2)
            state_mgr.set_stage(state, slug, "chunk", StageStatus.COMPLETED)
            print(f"  3. Chunk: {r3['total_chunks']} darab")
        except Exception as e:
            state_mgr.set_stage(state, slug, "chunk", StageStatus.FAILED, str(e))
            state_mgr.save(state)
            print(f"  !! Chunk HIBA: {e}")
            continue

        # Step 4: Transcribe (STT)
        try:
            state_mgr.set_stage(state, slug, "transcribe", StageStatus.IN_PROGRESS)
            state_mgr.save(state)
            r4 = await transcribe(r3)
            state_mgr.set_stage(state, slug, "transcribe", StageStatus.COMPLETED)
            chunks = r4["chunk_transcripts"]
            stt_cost = sum(c.get("cost", 0) for c in chunks)
            total_text = sum(len(c.get("full_text", "")) for c in chunks)
            state_mgr.update_cost(state, slug, stt_cost=stt_cost)
            print(f"  4. STT: {total_text} karakter, ${stt_cost:.4f}")
        except Exception as e:
            state_mgr.set_stage(state, slug, "transcribe", StageStatus.FAILED, str(e))
            state_mgr.save(state)
            print(f"  !! STT HIBA: {e}")
            continue

        # Step 5: Merge
        try:
            state_mgr.set_stage(state, slug, "merge", StageStatus.IN_PROGRESS)
            r5 = await merge_transcripts({**r4, "title": file_path.stem})
            state_mgr.set_stage(state, slug, "merge", StageStatus.COMPLETED)
            full_text = r5.get("full_text", "")
            print(f"  5. Merge: {len(r5.get('segments', []))} szegmens")

            # Save SRT
            srt = r5.get("srt_content", "")
            if srt:
                srt_path = lesson_path / "transcript_hu.srt"
                srt_path.write_text(srt, encoding="utf-8")
                print(f"     -> {srt_path}")

            # Save plain text
            txt_path = lesson_path / "transcript_hu.txt"
            txt_path.write_text(full_text, encoding="utf-8")
        except Exception as e:
            state_mgr.set_stage(state, slug, "merge", StageStatus.FAILED, str(e))
            state_mgr.save(state)
            print(f"  !! Merge HIBA: {e}")
            continue

        # Step 6: Structure (LLM)
        try:
            state_mgr.set_stage(state, slug, "structure", StageStatus.IN_PROGRESS)
            state_mgr.save(state)
            r6 = await structure_transcript({
                "merged_transcript": r5,
                "title": file_path.stem,
            })
            state_mgr.set_stage(state, slug, "structure", StageStatus.COMPLETED)
            struct_cost = r6.get("structuring_cost", 0)
            state_mgr.update_cost(state, slug, structuring_cost=struct_cost)

            print(f"  6. Struktura:")
            print(f"     Osszefoglalas: {r6.get('summary', '')[:150]}")
            print(f"     Temak: {r6.get('key_topics', [])[:5]}")
            print(f"     Szekciok: {len(r6.get('sections', []))}")
            print(f"     Szotar: {len(r6.get('vocabulary', []))}")

            # Save structured JSON
            json_path = lesson_path / "structured.json"
            json_path.write_text(
                json.dumps(r6, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"     -> {json_path}")

            # Save markdown
            md_lines = [f"# {r6.get('title', slug)}", ""]
            md_lines.append(f"**Osszefoglalas:** {r6.get('summary', '')}")
            md_lines.append("")
            md_lines.append(f"**Temak:** {', '.join(r6.get('key_topics', []))}")
            md_lines.append("")
            for sec in r6.get("sections", []):
                md_lines.append(f"## {sec.get('title', '')}")
                md_lines.append(f"*{sec.get('summary', '')}*")
                md_lines.append("")
                md_lines.append(sec.get("content", ""))
                md_lines.append("")
            if r6.get("vocabulary"):
                md_lines.append("## Szotar")
                md_lines.append("")
                for v in r6["vocabulary"]:
                    md_lines.append(f"- **{v.get('term', '')}**: {v.get('definition', '')}")
            md_path = lesson_path / "tananyag.md"
            md_path.write_text("\n".join(md_lines), encoding="utf-8")
            print(f"     -> {md_path}")

        except Exception as e:
            state_mgr.set_stage(state, slug, "structure", StageStatus.FAILED, str(e))
            state_mgr.save(state)
            print(f"  !! Structure HIBA: {e}")
            continue

        duration = time.monotonic() - start
        file_cost = stt_cost + r6.get("structuring_cost", 0)
        total_cost += file_cost
        print(f"\n  Ido: {duration:.1f}s | Koltseg: ${file_cost:.4f}")

        # Save state
        state_mgr.save(state)

    # Final state save
    state.total_cost_usd = total_cost
    state_mgr.save(state)

    print(f"\n{'=' * 60}")
    print(f"  KESZ: {len(files)} fajl feldolgozva")
    print(f"  Koltseg: ${total_cost:.4f}")
    print(f"  Output: {output_base}")
    print(f"  State:  {state_mgr._state_path}")
    print(f"{'=' * 60}")

    # List output files
    print(f"\n  Generalt fajlok:")
    for p in sorted(output_base.rglob("*")):
        if p.is_file():
            size = p.stat().st_size
            print(f"    {p.relative_to(output_base)} ({size:,} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cubix ML Course transcript pipeline test")
    parser.add_argument("--input-dir", default="C:/Users/kassaiattila/Videos/ml_w7_8")
    parser.add_argument("--output-dir", default="./test_output")
    parser.add_argument("--course-name", default="Cubix_ML_Course")
    parser.add_argument("--max-files", type=int, default=2)
    asyncio.run(main(parser.parse_args()))
