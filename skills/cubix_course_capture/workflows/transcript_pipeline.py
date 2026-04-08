"""Transcript pipeline workflow for Cubix Course Capture.

Six-step DAG that takes a video/audio file through probing, extraction,
chunking, transcription, merging, and AI-powered structuring.

Steps:
    1. probe_audio   - ffprobe metadata extraction (shell)
    2. extract_audio  - ffmpeg audio extraction (shell)
    3. chunk_audio    - split large files into Whisper-sized chunks (shell)
    4. transcribe     - OpenAI Whisper STT per chunk
    5. merge_transcripts - timestamp-aware merge with deduplication
    6. structure_transcript - LLM structuring via prompt template
"""

from __future__ import annotations

import asyncio
import difflib
import json
from pathlib import Path
from typing import Any

import structlog
from skills.cubix_course_capture.config import TranscriptPipelineConfig
from skills.cubix_course_capture.models import (
    AudioProbeResult,
    ChunkInfo,
    ChunkOutput,
    ChunkTranscript,
    ExtractAudioOutput,
    MergedTranscript,
    StructuredTranscript,
    TopicSection,
    TranscriptSegment,
    VocabularyItem,
)

from aiflow.engine.step import step
from aiflow.engine.workflow import WorkflowBuilder, workflow
from aiflow.models.backends.litellm_backend import LiteLLMBackend
from aiflow.models.client import ModelClient
from aiflow.prompts.manager import PromptManager

__all__ = [
    "probe_audio",
    "extract_audio",
    "chunk_audio",
    "transcribe",
    "merge_transcripts",
    "structure_transcript",
    "transcript_pipeline",
]

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_backend = LiteLLMBackend(default_model="openai/gpt-4o-mini")
_models = ModelClient(generation_backend=_backend)
_prompts = PromptManager()
_prompts.register_yaml_dir(Path(__file__).parent.parent / "prompts")

config = TranscriptPipelineConfig()


# ---------------------------------------------------------------------------
# Step 1 - probe_audio
# ---------------------------------------------------------------------------


@step(name="probe_audio", step_type="shell")
async def probe_audio(data: dict[str, Any]) -> dict[str, Any]:
    """Probe an audio or video file with ffprobe and return stream metadata."""
    file_path = data["file_path"]
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    proc = await asyncio.create_subprocess_exec(
        config.ffprobe_path,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed (rc={proc.returncode}): {stderr.decode().strip()}")

    probe = json.loads(stdout.decode())

    # Find the first audio stream
    audio_stream: dict[str, Any] = {}
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "audio":
            audio_stream = stream
            break

    fmt = probe.get("format", {})
    duration = float(audio_stream.get("duration", fmt.get("duration", 0)))
    file_size = path.stat().st_size

    result = AudioProbeResult(
        file_path=str(path),
        duration_seconds=duration,
        codec=audio_stream.get("codec_name", "unknown"),
        sample_rate=int(audio_stream.get("sample_rate", config.sample_rate)),
        channels=int(audio_stream.get("channels", config.audio_channels)),
        bitrate=int(audio_stream.get("bit_rate", fmt.get("bit_rate", 64000))),
        file_size_bytes=file_size,
    )

    logger.info(
        "probe_audio.done",
        file=str(path),
        duration=result.duration_seconds,
        codec=result.codec,
        size_mb=round(file_size / 1024 / 1024, 2),
    )
    return result.model_dump()


# ---------------------------------------------------------------------------
# Step 2 - extract_audio
# ---------------------------------------------------------------------------


@step(name="extract_audio", step_type="shell")
async def extract_audio(data: dict[str, Any]) -> dict[str, Any]:
    """Extract audio track from a video file using ffmpeg."""
    file_path = data["file_path"]
    path = Path(file_path)

    base_dir = Path(data.get("output_dir", config.output_dir))
    output_dir = base_dir / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{path.stem}.{config.audio_format}"

    # Detect whether the input contains a video stream
    has_video = False
    probe_streams = data.get("streams", [])
    if not probe_streams:
        # Re-probe to check for video
        proc = await asyncio.create_subprocess_exec(
            config.ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            probe = json.loads(stdout.decode())
            probe_streams = probe.get("streams", [])

    for stream in probe_streams:
        if isinstance(stream, dict) and stream.get("codec_type") == "video":
            has_video = True
            break

    if has_video:
        cmd = [
            config.ffmpeg_path,
            "-i",
            str(path),
            "-vn",
            "-acodec",
            "aac",
            "-ar",
            str(data.get("sample_rate", config.sample_rate)),
            "-ac",
            str(data.get("channels", config.audio_channels)),
            "-b:a",
            config.audio_bitrate,
            "-y",
            str(output_path),
        ]
    else:
        # Input is already audio-only — re-encode to target format to avoid
        # codec/container mismatches (e.g. PCM WAV → M4A needs AAC encoding)
        cmd = [
            config.ffmpeg_path,
            "-i",
            str(path),
            "-acodec",
            "aac",
            "-ar",
            str(data.get("sample_rate", config.sample_rate)),
            "-ac",
            str(data.get("channels", config.audio_channels)),
            "-b:a",
            config.audio_bitrate,
            "-y",
            str(output_path),
        ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg extract failed (rc={proc.returncode}): {stderr.decode().strip()}"
        )

    out_size = output_path.stat().st_size
    duration = float(data.get("duration_seconds", 0))

    result = ExtractAudioOutput(
        audio_path=str(output_path),
        duration_seconds=duration,
        file_size_bytes=out_size,
    )

    logger.info(
        "extract_audio.done",
        output=str(output_path),
        duration=duration,
        size_mb=round(out_size / 1024 / 1024, 2),
    )
    return result.model_dump()


# ---------------------------------------------------------------------------
# Step 3 - chunk_audio
# ---------------------------------------------------------------------------


@step(name="chunk_audio", step_type="shell")
async def chunk_audio(data: dict[str, Any]) -> dict[str, Any]:
    """Split a large audio file into Whisper-compatible chunks via ffmpeg."""
    audio_path = data["audio_path"]
    file_size = data["file_size_bytes"]
    duration = data.get("duration_seconds", 0.0)

    # If small enough, return a single chunk
    if file_size <= config.max_chunk_bytes:
        single = ChunkInfo(
            chunk_index=0,
            file_path=audio_path,
            start_seconds=0.0,
            end_seconds=duration,
            duration_seconds=duration,
        )
        result = ChunkOutput(chunks=[single], total_chunks=1)
        logger.info("chunk_audio.single_chunk", size_mb=round(file_size / 1024 / 1024, 2))
        return result.model_dump()

    # Calculate how many chunks we need
    num_chunks = max(2, -(-file_size // config.max_chunk_bytes))  # ceil division
    chunk_duration = duration / num_chunks
    overlap = config.chunk_overlap_seconds

    output_dir = Path(data.get("output_dir", config.output_dir)) / "chunks"
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks: list[ChunkInfo] = []
    stem = Path(audio_path).stem

    for i in range(num_chunks):
        start = max(0.0, i * chunk_duration - (overlap if i > 0 else 0))
        end = min(duration, (i + 1) * chunk_duration)
        seg_duration = end - start

        chunk_path = output_dir / f"{stem}_chunk{i:03d}.{config.audio_format}"
        cmd = [
            config.ffmpeg_path,
            "-i",
            str(audio_path),
            "-ss",
            str(start),
            "-t",
            str(seg_duration),
            "-acodec",
            "copy",
            "-y",
            str(chunk_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(
                f"ffmpeg chunk {i} failed (rc={proc.returncode}): {stderr.decode().strip()}"
            )

        chunks.append(
            ChunkInfo(
                chunk_index=i,
                file_path=str(chunk_path),
                start_seconds=start,
                end_seconds=end,
                duration_seconds=seg_duration,
            )
        )

    result = ChunkOutput(chunks=chunks, total_chunks=len(chunks))
    logger.info(
        "chunk_audio.done", total_chunks=len(chunks), chunk_duration=round(chunk_duration, 1)
    )
    return result.model_dump()


# ---------------------------------------------------------------------------
# Step 4 - transcribe
# ---------------------------------------------------------------------------


@step(name="transcribe")
async def transcribe(data: dict[str, Any]) -> dict[str, Any]:
    """Transcribe each audio chunk using OpenAI Whisper API."""
    import openai

    chunks_raw: list[dict[str, Any]] = data["chunks"]
    chunks = [ChunkInfo(**c) for c in chunks_raw]

    client = openai.AsyncOpenAI()
    whisper_cost_per_minute = 0.006  # USD per minute for whisper-1

    chunk_transcripts: list[dict[str, Any]] = []

    for chunk in chunks:
        chunk_path = Path(chunk.file_path)
        logger.info("transcribe.start", chunk=chunk.chunk_index, file=str(chunk_path))

        with open(chunk_path, "rb") as f:
            response = await client.audio.transcriptions.create(
                model=config.stt_model,
                file=f,
                language=config.stt_language,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        segments: list[dict[str, Any]] = []
        raw_segments = getattr(response, "segments", []) or []
        for idx, seg in enumerate(raw_segments):
            # seg can be a Pydantic object or dict depending on openai SDK version
            if isinstance(seg, dict):
                s_start = seg.get("start", 0.0)
                s_end = seg.get("end", 0.0)
                s_text = seg.get("text", "")
                s_conf = seg.get("avg_logprob", 1.0)
            else:
                s_start = getattr(seg, "start", 0.0)
                s_end = getattr(seg, "end", 0.0)
                s_text = getattr(seg, "text", "")
                s_conf = getattr(seg, "avg_logprob", 1.0)
            segments.append(
                TranscriptSegment(
                    id=idx,
                    start=float(s_start),
                    end=float(s_end),
                    text=str(s_text).strip(),
                    confidence=float(s_conf) if s_conf is not None else 1.0,
                ).model_dump()
            )

        full_text = getattr(response, "text", "")
        seg_duration = chunk.duration_seconds
        cost = (seg_duration / 60.0) * whisper_cost_per_minute

        ct = ChunkTranscript(
            chunk_index=chunk.chunk_index,
            model=config.stt_model,
            language=config.stt_language,
            duration_seconds=seg_duration,
            segments=[TranscriptSegment(**s) for s in segments],
            full_text=full_text,
            cost=cost,
        )
        chunk_transcripts.append(ct.model_dump())

        logger.info(
            "transcribe.chunk_done",
            chunk=chunk.chunk_index,
            segments=len(segments),
            cost=round(cost, 4),
        )

    return {
        "chunk_transcripts": chunk_transcripts,
        "chunks": data.get("chunks", []),
        "output_dir": data.get("output_dir", ""),
    }


# ---------------------------------------------------------------------------
# Step 5 - merge_transcripts
# ---------------------------------------------------------------------------


def _segments_overlap(text_a: str, text_b: str, threshold: float = 0.6) -> bool:
    """Return True if two segment texts are similar enough to be duplicates."""
    ratio = difflib.SequenceMatcher(None, text_a.strip(), text_b.strip()).ratio()
    return ratio >= threshold


@step(name="merge_transcripts")
async def merge_transcripts(data: dict[str, Any]) -> dict[str, Any]:
    """Merge chunk transcripts into a single timeline, deduplicating overlaps."""
    chunk_transcripts_raw: list[dict[str, Any]] = data["chunk_transcripts"]
    title = data.get("title", "Untitled")

    transcripts = [ChunkTranscript(**ct) for ct in chunk_transcripts_raw]

    if len(transcripts) == 1:
        ct = transcripts[0]
        merged = MergedTranscript(
            title=title,
            total_duration_seconds=ct.duration_seconds,
            segments=ct.segments,
            full_text=ct.full_text,
            total_cost=ct.cost,
            chunk_count=1,
        )
        logger.info("merge_transcripts.single_chunk", segments=len(ct.segments))
        return merged.model_dump()

    # Multi-chunk merge with timestamp adjustment and deduplication
    merged_segments: list[TranscriptSegment] = []
    total_cost = 0.0
    global_id = 0

    # We need the chunk start offsets from the chunk_audio step.
    # They are embedded in each ChunkTranscript via the chunk_index.
    # Reconstruct offsets from the data if available, otherwise from segments.
    chunks_info: list[dict[str, Any]] = data.get("chunks", [])
    offset_map: dict[int, float] = {}
    for ci in chunks_info:
        offset_map[ci.get("chunk_index", 0)] = ci.get("start_seconds", 0.0)

    for ct in transcripts:
        offset = offset_map.get(ct.chunk_index, 0.0)
        total_cost += ct.cost

        for seg in ct.segments:
            adjusted_start = seg.start + offset
            adjusted_end = seg.end + offset

            # Deduplicate: check if last merged segment is similar (overlap region)
            if merged_segments:
                last = merged_segments[-1]
                if adjusted_start <= last.end + 1.0 and _segments_overlap(last.text, seg.text):
                    # Skip duplicate segment from overlap
                    continue

            merged_segments.append(
                TranscriptSegment(
                    id=global_id,
                    start=adjusted_start,
                    end=adjusted_end,
                    text=seg.text,
                    confidence=seg.confidence,
                )
            )
            global_id += 1

    full_text = " ".join(seg.text.strip() for seg in merged_segments)
    total_duration = merged_segments[-1].end if merged_segments else 0.0

    # Generate SRT content
    srt_lines: list[str] = []
    for seg in merged_segments:
        srt_lines.append(str(seg.id + 1))
        srt_lines.append(f"{_format_srt_time(seg.start)} --> {_format_srt_time(seg.end)}")
        srt_lines.append(seg.text.strip())
        srt_lines.append("")
    srt_content = "\n".join(srt_lines)

    merged = MergedTranscript(
        title=title,
        total_duration_seconds=total_duration,
        segments=merged_segments,
        full_text=full_text,
        total_cost=total_cost,
        chunk_count=len(transcripts),
    )

    result = merged.model_dump()
    result["srt_content"] = srt_content

    logger.info(
        "merge_transcripts.done",
        chunks=len(transcripts),
        segments=len(merged_segments),
        duration=round(total_duration, 1),
        total_cost=round(total_cost, 4),
    )
    return result


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


# ---------------------------------------------------------------------------
# Step 6 - structure_transcript
# ---------------------------------------------------------------------------


async def _call_section_detector(
    title: str, full_text: str, total_duration: float
) -> tuple[list[dict[str, Any]], float]:
    """Run the section_detector prompt and return (sections, cost)."""
    prompt_def = _prompts.get("cubix/section_detector")
    messages = prompt_def.compile(
        variables={
            "course_title": title,
            "duration_seconds": str(round(total_duration, 1)),
            "transcript_text": full_text,
        }
    )
    result = await _models.generate(
        messages=messages,
        model=config.structuring_model,
        temperature=0.2,
        max_tokens=4096,
    )
    raw = result.output.text or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"sections": []}
    sections = parsed.get("sections", []) if isinstance(parsed, dict) else []
    return sections, result.cost_usd


async def _call_summary_generator(
    title: str, full_text: str, duration_minutes: float
) -> tuple[dict[str, Any], float]:
    """Run the summary_generator prompt and return (summary_dict, cost)."""
    prompt_def = _prompts.get("cubix/summary_generator")
    messages = prompt_def.compile(
        variables={
            "course_title": title,
            "duration_minutes": str(duration_minutes),
            "transcript_text": full_text,
        }
    )
    result = await _models.generate(
        messages=messages,
        model=config.structuring_model,
        temperature=0.3,
        max_tokens=1024,
    )
    raw = result.output.text or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}
    return (parsed if isinstance(parsed, dict) else {}), result.cost_usd


async def _call_vocabulary_extractor(
    title: str, full_text: str
) -> tuple[list[dict[str, Any]], float]:
    """Run the vocabulary_extractor prompt and return (terms, cost)."""
    prompt_def = _prompts.get("cubix/vocabulary_extractor")
    messages = prompt_def.compile(
        variables={
            "course_title": title,
            "transcript_text": full_text,
        }
    )
    result = await _models.generate(
        messages=messages,
        model=config.structuring_model,
        temperature=0.2,
        max_tokens=2048,
    )
    raw = result.output.text or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"terms": []}
    terms = parsed.get("terms", []) if isinstance(parsed, dict) else []
    return terms, result.cost_usd


@step(name="structure_transcript")
async def structure_transcript(data: dict[str, Any]) -> dict[str, Any]:
    """Structure a merged transcript via 3 split prompts running in parallel.

    B4.2 split: section_detector + summary_generator + vocabulary_extractor.
    The 3 calls only depend on the merged transcript text, so we run them
    concurrently to keep latency comparable to the previous monolithic call.
    """
    # Accept either a nested merged_transcript dict or flat data
    merged = data.get("merged_transcript", data)
    full_text = merged.get("full_text", "")
    title = merged.get("title", data.get("title", "Untitled"))
    total_duration = merged.get("total_duration_seconds", 0.0)
    duration_minutes = round(total_duration / 60.0, 1)

    sections_task = _call_section_detector(title, full_text, total_duration)
    summary_task = _call_summary_generator(title, full_text, duration_minutes)
    vocab_task = _call_vocabulary_extractor(title, full_text)

    (
        (sections_raw, sections_cost),
        (summary_dict, summary_cost),
        (
            vocab_raw,
            vocab_cost,
        ),
    ) = await asyncio.gather(sections_task, summary_task, vocab_task)

    # Coerce into the existing StructuredTranscript schema for backward compat
    structured = StructuredTranscript(
        title=title,
        summary=str(summary_dict.get("summary", ""))[:500],
        key_topics=[str(t) for t in (summary_dict.get("key_topics") or []) if t],
        sections=[
            TopicSection(
                title=str(s.get("title", "")),
                start_time=float(s.get("start_time", 0.0) or 0.0),
                end_time=float(s.get("end_time", 0.0) or 0.0),
                summary=str(s.get("summary", "")),
                content=str(s.get("content", "")),
            )
            for s in sections_raw
            if isinstance(s, dict)
        ],
        vocabulary=[
            VocabularyItem(
                term=str(v.get("term", "")),
                definition=str(v.get("definition", "")),
            )
            for v in vocab_raw
            if isinstance(v, dict) and v.get("term")
        ],
        cleaned_text=full_text,
        structuring_cost=sections_cost + summary_cost + vocab_cost,
    )

    logger.info(
        "structure_transcript.done",
        title=title,
        sections=len(structured.sections),
        topics=len(structured.key_topics),
        vocabulary=len(structured.vocabulary),
        cost=round(structured.structuring_cost, 4),
        prompts_used="section_detector+summary_generator+vocabulary_extractor",
    )
    return structured.model_dump()


# ---------------------------------------------------------------------------
# Workflow definition
# ---------------------------------------------------------------------------


@workflow(name="transcript-pipeline", version="1.0.0", skill="cubix_course_capture")
def transcript_pipeline(wf: WorkflowBuilder) -> None:
    """Six-step DAG: probe -> extract -> chunk -> transcribe -> merge -> structure."""
    wf.step(probe_audio)
    wf.step(extract_audio, depends_on=["probe_audio"])
    wf.step(chunk_audio, depends_on=["extract_audio"])
    wf.step(transcribe, depends_on=["chunk_audio"])
    wf.step(merge_transcripts, depends_on=["transcribe"])
    wf.step(structure_transcript, depends_on=["merge_transcripts"])
