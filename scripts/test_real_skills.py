#!/usr/bin/env python3
"""Real-world integration test for Process Documentation + Cubix Transcript Pipeline.

Usage:
    python scripts/test_real_skills.py \
        --input-dir "C:/Users/kassaiattila/Videos/ml_w7_8" \
        --output-dir "./test_output" \
        --max-files 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# --- PART 1: Process Documentation (Diagram Generation) ---

async def test_process_documentation() -> None:
    """Test the Process Documentation pipeline with real Hungarian processes."""
    from skills.process_documentation.workflow import (
        classify_intent, elaborate, extract, review, generate_diagram, export_all
    )

    test_cases = [
        {
            "name": "Szabadsag igenyeles",
            "input": (
                "A szabadság igénylés folyamata a következő: "
                "a dolgozó kitölti a szabadság igénylő lapot az intraneten, "
                "megadja a kívánt dátumot és a helyettesítő személyt. "
                "A közvetlen vezető kapja meg az igénylést és jóváhagyja vagy elutasítja. "
                "Elutasítás esetén a dolgozó módosíthatja az igénylést. "
                "Jóváhagyás után a HR rögzíti a rendszerben és levonja a szabadság keretet. "
                "A dolgozó és a helyettesítő értesítést kap emailben."
            ),
        },
        {
            "name": "Szamla feldolgozas",
            "input": (
                "Bejövő számla feldolgozás: a postás hozza a számlát vagy emailben érkezik. "
                "A pénzügyi asszisztens rögzíti a rendszerben a számla adatait. "
                "Ha a számla összege 500.000 Ft felett van, akkor a pénzügyi igazgató "
                "jóváhagyása szükséges. Ha alatta van, automatikusan megy utalásra. "
                "Az utalás után a rendszer könyveli a számlát és archíválja."
            ),
        },
        {
            "name": "Uj kollegafelvitel",
            "input": (
                "Új munkatárs felvételi folyamat: a HR meghirdeti az állást a karrieroldalon. "
                "A jelöltek beküldik az önéletrajzukat. A HR szűri a beérkezett pályázatokat "
                "és kiválasztja a megfelelő jelölteket interjúra. "
                "A szakmai vezető interjúztat és értékeli a jelölteket. "
                "Ha alkalmas, a HR bérajánlatot küld. A jelölt elfogadja vagy elutasítja. "
                "Elfogadás esetén a HR elkészíti a munkaszerződést, "
                "a jelölt aláírja, és megkezdődik az onboarding folyamat."
            ),
        },
    ]

    print("\n" + "=" * 80)
    print("  PROCESS DOCUMENTATION SKILL - VALOS TESZT")
    print("=" * 80)

    for tc in test_cases:
        print(f"\n{'-' * 60}")
        print(f"  Folyamat: {tc['name']}")
        print(f"{'-' * 60}")

        start = time.monotonic()

        # Step 1: Classify
        data = {"user_input": tc["input"]}
        r1 = await classify_intent(data)
        print(f"  1. Klasszifikacio: {r1['category']} (confidence: {r1['confidence']:.2f})")

        if r1["category"] != "process":
            print(f"  !! Nem folyamat - kihagyva")
            continue

        # Step 2: Elaborate
        r2 = await elaborate({**r1, "user_input": tc["input"]})
        elab_text = r2["elaborated_text"]
        print(f"  2. Kibovites: {len(elab_text)} karakter ({len(tc['input'])} -> {len(elab_text)})")

        # Step 3: Extract
        r3 = await extract(r2)
        ext = r3["extraction"]
        print(f"  3. BPMN kivonas: {ext['title']}")
        print(f"     Aktorok: {[a['name'] for a in ext['actors']]}")
        print(f"     Lepesek: {len(ext['steps'])} db")
        for s in ext["steps"]:
            stype = s["step_type"]
            actor = s.get("actor", "-")
            print(f"       [{stype:20s}] {s['name']} (actor: {actor})")

        # Step 4: Review
        r4 = await review({**r3, "original_input": tc["input"]})
        rev = r4["review"]
        print(f"  4. Review: {rev['score']}/10 (elfogadhato: {rev['is_acceptable']})")
        print(f"     Teljesseg: {rev['completeness_score']}, Logika: {rev['logic_score']}")
        if rev["issues"]:
            print(f"     Problanak: {rev['issues'][:2]}")

        # Step 5: Generate Diagram
        r5 = await generate_diagram(r3)
        mermaid = r5["mermaid_code"]
        print(f"  5. Mermaid diagram ({len(mermaid)} karakter)")

        # Step 6: Export All Formats
        r6 = await export_all({**r5, "output_dir": "./test_output/diagrams"})
        saved = r6.get("saved_files", [])
        duration = (time.monotonic() - start) * 1000
        print(f"  6. Export ({len(saved)} fajl mentve):")
        for f in saved:
            print(f"     -> {f}")
        print(f"\n  Teljes idotartam: {duration:.0f}ms")
        print(f"  Koltseg: ~$0.02-0.05")


# --- PART 2: Cubix Transcript Pipeline ---

async def test_transcript_pipeline(
    input_dir: str,
    output_dir: str,
    max_files: int = 3,
) -> None:
    """Test the Transcript Pipeline with real video files."""
    from skills.cubix_course_capture.workflows.transcript_pipeline import (
        probe_audio, extract_audio, chunk_audio, transcribe,
        merge_transcripts, structure_transcript, config,
    )

    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"\n!! Input konyvtar nem talalhato: {input_dir}")
        return

    # Find smallest MKV files
    mkv_files = sorted(input_path.glob("*.mkv"), key=lambda f: f.stat().st_size)
    if not mkv_files:
        print(f"\n!! Nincs MKV file a konyvtarban: {input_dir}")
        return

    files_to_process = mkv_files[:max_files]

    # Override output directory
    config.output_dir = output_dir
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("  CUBIX TRANSCRIPT PIPELINE - VALOS TESZT")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Feldolgozando fajlok: {len(files_to_process)}")
    print("=" * 80)

    total_cost = 0.0

    for i, file_path in enumerate(files_to_process):
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"\n{'-' * 60}")
        print(f"  [{i + 1}/{len(files_to_process)}] {file_path.name} ({file_size_mb:.1f} MB)")
        print(f"{'-' * 60}")

        start = time.monotonic()
        data: dict = {"file_path": str(file_path)}

        # Step 1: Probe
        try:
            r1 = await probe_audio(data)
            dur_min = r1["duration_seconds"] / 60
            print(f"  1. Probe: {r1['duration_seconds']:.1f}s ({dur_min:.1f} perc), "
                  f"codec={r1['codec']}, {r1['sample_rate']}Hz")
        except Exception as e:
            print(f"  !! Probe HIBA: {e}")
            continue

        # Step 2: Extract audio
        try:
            r2 = await extract_audio({**data, **r1})
            audio_size_mb = r2["file_size_bytes"] / (1024 * 1024)
            print(f"  2. Audio extraktalas: {r2['audio_path']} ({audio_size_mb:.1f} MB)")
        except Exception as e:
            print(f"  !! Extract HIBA: {e}")
            continue

        # Step 3: Chunk
        try:
            r3 = await chunk_audio(r2)
            print(f"  3. Darabolas: {r3['total_chunks']} darab")
        except Exception as e:
            print(f"  !! Chunk HIBA: {e}")
            continue

        # Step 4: Transcribe (STT - ez a koltsseges lepes)
        try:
            r4 = await transcribe(r3)
            chunks = r4["chunk_transcripts"]
            stt_cost = sum(c.get("cost", 0) for c in chunks)
            total_text_len = sum(len(c.get("full_text", "")) for c in chunks)
            print(f"  4. Transzkripcio: {len(chunks)} chunk feldolgozva, "
                  f"{total_text_len} karakter, koltseg: ${stt_cost:.4f}")
        except Exception as e:
            print(f"  !! Transcribe HIBA: {e}")
            continue

        # Step 5: Merge
        try:
            r5 = await merge_transcripts({
                **r4,
                "title": file_path.stem,
            })
            # merge_transcripts returns MergedTranscript.model_dump() directly
            merged = r5
            full_text = merged.get("full_text", "")
            print(f"  5. Merge: {len(merged.get('segments', []))} szegmens, "
                  f"{len(full_text)} karakter")
            # Show first 200 chars of transcript
            if full_text:
                preview = full_text[:200].replace("\n", " ")
                print(f"     Elonezet: {preview}...")
        except Exception as e:
            print(f"  !! Merge HIBA: {e}")
            continue

        # Step 6: Structure
        try:
            r6 = await structure_transcript({
                "merged_transcript": merged,
                "title": file_path.stem,
            })
            struct = r6 if isinstance(r6, dict) else r6
            struct_cost = struct.get("structuring_cost", 0)
            print(f"  6. Strukturalas:")
            print(f"     Osszefoglalas: {struct.get('summary', 'N/A')[:200]}")
            print(f"     Temak: {struct.get('key_topics', [])[:5]}")
            sections = struct.get("sections", [])
            print(f"     Szekciok: {len(sections)} db")
            for sec in sections[:3]:
                print(f"       - {sec.get('title', '?')}")
            vocab = struct.get("vocabulary", [])
            print(f"     Szotar: {len(vocab)} kifejezes")
            for v in vocab[:3]:
                print(f"       - {v.get('term', '?')}: {v.get('definition', '?')[:60]}")
            print(f"     Koltseg: ${struct_cost:.4f}")
        except Exception as e:
            print(f"  !! Structure HIBA: {e}")
            continue

        duration = (time.monotonic() - start)
        file_cost = stt_cost + struct.get("structuring_cost", 0)
        total_cost += file_cost
        print(f"\n  Idotartam: {duration:.1f}s | Koltseg: ${file_cost:.4f}")

        # Save outputs
        output_file = out_path / f"{file_path.stem}_structured.json"
        output_file.write_text(
            json.dumps(struct, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  Mentve: {output_file}")

        # Save plain text
        text_file = out_path / f"{file_path.stem}_transcript.txt"
        text_file.write_text(
            struct.get("cleaned_text", full_text),
            encoding="utf-8",
        )
        print(f"  Mentve: {text_file}")

        # Save SRT if available
        srt_content = merged.get("srt_content", "")
        if srt_content:
            srt_file = out_path / f"{file_path.stem}.srt"
            srt_file.write_text(srt_content, encoding="utf-8")
            print(f"  Mentve: {srt_file}")

    print(f"\n{'=' * 60}")
    print(f"  OSSZEGZES: {len(files_to_process)} fajl feldolgozva")
    print(f"  Teljes koltseg: ${total_cost:.4f}")
    print(f"  Output konyvtar: {output_dir}")
    print(f"{'=' * 60}")


# --- MAIN ---

async def main(args: argparse.Namespace) -> None:
    """Run both skill tests."""
    # Process Documentation tests
    await test_process_documentation()

    # Transcript Pipeline tests
    await test_transcript_pipeline(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        max_files=args.max_files,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-world skill integration tests")
    parser.add_argument(
        "--input-dir",
        default="C:/Users/kassaiattila/Videos/ml_w7_8",
        help="Input directory with MKV video files",
    )
    parser.add_argument(
        "--output-dir",
        default="./test_output",
        help="Output directory for transcripts and diagrams",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=3,
        help="Maximum number of files to process (smallest first)",
    )
    args = parser.parse_args()
    asyncio.run(main(args))
