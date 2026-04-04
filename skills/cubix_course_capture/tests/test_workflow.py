"""
@test_registry:
    suite: cubix-transcript-unit
    component: skills.cubix_course_capture.workflows.transcript_pipeline
    covers: [skills/cubix_course_capture/workflows/transcript_pipeline.py]
    phase: C
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [cubix, transcript, pipeline, ffmpeg, stt]
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from skills.cubix_course_capture.models import (
    ChunkTranscript,
    StructuredTranscript,
    TopicSection,
    TranscriptSegment,
    VocabularyItem,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_FFPROBE_OUTPUT = {
    "streams": [
        {
            "codec_type": "audio",
            "codec_name": "aac",
            "sample_rate": "44100",
            "channels": 2,
            "bit_rate": "128000",
            "duration": "120.5",
        }
    ],
    "format": {"duration": "120.5", "size": "1920000"},
}


def _make_mock_process(
    stdout: bytes = b"",
    stderr: bytes = b"",
    returncode: int = 0,
) -> AsyncMock:
    """Create a mock asyncio subprocess with communicate()."""
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    return proc


@pytest.fixture()
def ffprobe_stdout() -> bytes:
    return json.dumps(SAMPLE_FFPROBE_OUTPUT).encode()


# ---------------------------------------------------------------------------
# Test 1 - probe_audio parses ffprobe output
# ---------------------------------------------------------------------------


class TestProbeAudio:
    @pytest.mark.asyncio
    async def test_probe_audio_parses_output(
        self, ffprobe_stdout: bytes, tmp_path: Path
    ) -> None:
        """Mock subprocess to return ffprobe JSON with audio stream, verify parsed result."""
        # Create a real temp file so Path.exists() and stat() work
        audio_file = tmp_path / "lecture.mp4"
        audio_file.write_bytes(b"\x00" * 1920000)

        mock_proc = _make_mock_process(stdout=ffprobe_stdout)

        with patch(
            "skills.cubix_course_capture.workflows.transcript_pipeline.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            from skills.cubix_course_capture.workflows.transcript_pipeline import (
                probe_audio,
            )

            result = await probe_audio({"file_path": str(audio_file)})

        assert result["duration_seconds"] == 120.5
        assert result["codec"] == "aac"
        assert result["sample_rate"] == 44100
        assert result["channels"] == 2
        assert result["bitrate"] == 128000
        assert result["file_path"] == str(audio_file)
        assert result["file_size_bytes"] == 1920000

    @pytest.mark.asyncio
    async def test_probe_audio_file_not_found(self) -> None:
        """Input non-existent file path, verify FileNotFoundError."""
        from skills.cubix_course_capture.workflows.transcript_pipeline import (
            probe_audio,
        )

        with pytest.raises(FileNotFoundError, match="Input file not found"):
            await probe_audio({"file_path": "/nonexistent/audio.mp4"})

    @pytest.mark.asyncio
    async def test_probe_audio_ffprobe_failure(self, tmp_path: Path) -> None:
        """ffprobe exits with non-zero code, verify RuntimeError."""
        audio_file = tmp_path / "bad.mp4"
        audio_file.write_bytes(b"\x00" * 100)

        mock_proc = _make_mock_process(
            stderr=b"Invalid data found when processing input",
            returncode=1,
        )

        with patch(
            "skills.cubix_course_capture.workflows.transcript_pipeline.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            from skills.cubix_course_capture.workflows.transcript_pipeline import (
                probe_audio,
            )

            with pytest.raises(RuntimeError, match="ffprobe failed"):
                await probe_audio({"file_path": str(audio_file)})


# ---------------------------------------------------------------------------
# Test 3 - extract_audio builds correct ffmpeg command
# ---------------------------------------------------------------------------


class TestExtractAudio:
    @pytest.mark.asyncio
    async def test_extract_audio_builds_command(self, tmp_path: Path) -> None:
        """Mock subprocess, verify ffmpeg was called with correct args."""
        input_file = tmp_path / "input.mp4"
        input_file.write_bytes(b"\x00" * 500)

        # Patch output_dir so ffmpeg output goes to tmp_path
        output_dir = tmp_path / "output"

        mock_proc = _make_mock_process()

        # The output file must exist for stat()
        def side_effect_create_proc(*args: Any, **kwargs: Any) -> AsyncMock:
            # Create the expected output file before stat() is called
            out = output_dir / "audio" / "input.m4a"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"\x00" * 200)
            return mock_proc

        with (
            patch(
                "skills.cubix_course_capture.workflows.transcript_pipeline.asyncio.create_subprocess_exec",
                side_effect=side_effect_create_proc,
            ),
            patch(
                "skills.cubix_course_capture.workflows.transcript_pipeline.config",
            ) as mock_config,
        ):
            mock_config.ffmpeg_path = "ffmpeg"
            mock_config.ffprobe_path = "ffprobe"
            mock_config.output_dir = str(output_dir)
            mock_config.audio_format = "m4a"
            mock_config.sample_rate = 16000
            mock_config.audio_channels = 1
            mock_config.audio_bitrate = "64k"

            from skills.cubix_course_capture.workflows.transcript_pipeline import (
                extract_audio,
            )

            result = await extract_audio(
                {
                    "file_path": str(input_file),
                    "duration_seconds": 120.5,
                    # Provide streams so extract_audio skips ffprobe re-probe
                    "streams": [{"codec_type": "audio", "codec_name": "aac"}],
                }
            )

        assert result["audio_path"].endswith(".m4a")
        assert result["duration_seconds"] == 120.5
        assert result["file_size_bytes"] == 200


# ---------------------------------------------------------------------------
# Test 4 & 5 - chunk_audio
# ---------------------------------------------------------------------------


class TestChunkAudio:
    @pytest.mark.asyncio
    async def test_chunk_audio_single_chunk(self) -> None:
        """Input small file (< 24MB), verify single chunk returned."""
        from skills.cubix_course_capture.workflows.transcript_pipeline import (
            chunk_audio,
        )

        # Default max_chunk_bytes = 24 * 1024 * 1024 = 25165824
        data = {
            "audio_path": "/tmp/small.m4a",
            "file_size_bytes": 1_000_000,  # ~1MB, well under 24MB
            "duration_seconds": 60.0,
        }

        result = await chunk_audio(data)

        assert result["total_chunks"] == 1
        assert len(result["chunks"]) == 1
        chunk = result["chunks"][0]
        assert chunk["chunk_index"] == 0
        assert chunk["file_path"] == "/tmp/small.m4a"
        assert chunk["start_seconds"] == 0.0
        assert chunk["end_seconds"] == 60.0
        assert chunk["duration_seconds"] == 60.0

    @pytest.mark.asyncio
    async def test_chunk_audio_splits_large(self, tmp_path: Path) -> None:
        """Input large file (> 24MB), verify multiple chunks are created."""
        max_chunk = 24 * 1024 * 1024  # 24MB
        file_size = max_chunk * 3  # ~72MB -> should produce 3 chunks

        mock_proc = _make_mock_process()

        # Track how many times ffmpeg was called
        call_count = 0

        async def mock_create_subprocess(*args: Any, **kwargs: Any) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            return mock_proc

        output_dir = tmp_path / "output"

        with (
            patch(
                "skills.cubix_course_capture.workflows.transcript_pipeline.asyncio.create_subprocess_exec",
                side_effect=mock_create_subprocess,
            ),
            patch(
                "skills.cubix_course_capture.workflows.transcript_pipeline.config",
            ) as mock_config,
        ):
            mock_config.max_chunk_bytes = max_chunk
            mock_config.chunk_overlap_seconds = 2.0
            mock_config.ffmpeg_path = "ffmpeg"
            mock_config.audio_format = "m4a"
            mock_config.output_dir = str(output_dir)

            from skills.cubix_course_capture.workflows.transcript_pipeline import (
                chunk_audio,
            )

            result = await chunk_audio(
                {
                    "audio_path": "/tmp/large.m4a",
                    "file_size_bytes": file_size,
                    "duration_seconds": 360.0,
                }
            )

        assert result["total_chunks"] == 3
        assert len(result["chunks"]) == 3
        assert call_count == 3

        # First chunk starts at 0
        assert result["chunks"][0]["start_seconds"] == 0.0
        assert result["chunks"][0]["chunk_index"] == 0

        # Second chunk starts with overlap
        assert result["chunks"][1]["chunk_index"] == 1
        assert result["chunks"][1]["start_seconds"] > 0.0

        # Last chunk
        assert result["chunks"][2]["chunk_index"] == 2


# ---------------------------------------------------------------------------
# Test 6 & 7 & 8 - merge_transcripts
# ---------------------------------------------------------------------------


def _make_segment(
    id: int, start: float, end: float, text: str, confidence: float = 1.0
) -> dict[str, Any]:
    return TranscriptSegment(
        id=id, start=start, end=end, text=text, confidence=confidence
    ).model_dump()


def _make_chunk_transcript(
    chunk_index: int,
    segments: list[dict[str, Any]],
    full_text: str,
    duration: float = 60.0,
    cost: float = 0.006,
) -> dict[str, Any]:
    return ChunkTranscript(
        chunk_index=chunk_index,
        model="whisper-1",
        language="hu",
        duration_seconds=duration,
        segments=[TranscriptSegment(**s) for s in segments],
        full_text=full_text,
        cost=cost,
    ).model_dump()


class TestMergeTranscripts:
    @pytest.mark.asyncio
    async def test_merge_single_chunk(self) -> None:
        """Single chunk transcript, verify passthrough."""
        from skills.cubix_course_capture.workflows.transcript_pipeline import (
            merge_transcripts,
        )

        segments = [
            _make_segment(0, 0.0, 5.0, "Ez az elso mondat."),
            _make_segment(1, 5.0, 10.0, "Ez a masodik mondat."),
        ]
        ct = _make_chunk_transcript(
            chunk_index=0,
            segments=segments,
            full_text="Ez az elso mondat. Ez a masodik mondat.",
            duration=10.0,
            cost=0.001,
        )

        result = await merge_transcripts(
            {
                "chunk_transcripts": [ct],
                "title": "Test Lecture",
            }
        )

        assert result["title"] == "Test Lecture"
        assert result["chunk_count"] == 1
        assert len(result["segments"]) == 2
        assert result["total_cost"] == 0.001
        assert "elso mondat" in result["full_text"]

    @pytest.mark.asyncio
    async def test_merge_deduplicates_overlap(self) -> None:
        """Two chunks with overlapping segments (similar text near boundary), verify dedup."""
        from skills.cubix_course_capture.workflows.transcript_pipeline import (
            merge_transcripts,
        )

        # Chunk 0: segments at 0-5s and 5-10s
        seg_c0 = [
            _make_segment(0, 0.0, 5.0, "Bevezetes a Python programozasba."),
            _make_segment(1, 5.0, 10.0, "A valtozok es tipusok fontosak."),
        ]
        ct0 = _make_chunk_transcript(
            chunk_index=0,
            segments=seg_c0,
            full_text="Bevezetes a Python programozasba. A valtozok es tipusok fontosak.",
            duration=10.0,
            cost=0.001,
        )

        # Chunk 1: first segment overlaps with last segment of chunk 0
        # (similar text due to overlap region)
        seg_c1 = [
            _make_segment(0, 0.0, 5.0, "A valtozok es tipusok fontosak."),  # duplicate
            _make_segment(1, 5.0, 10.0, "Most nezzuk a fuggvenyeket."),
        ]
        ct1 = _make_chunk_transcript(
            chunk_index=1,
            segments=seg_c1,
            full_text="A valtozok es tipusok fontosak. Most nezzuk a fuggvenyeket.",
            duration=10.0,
            cost=0.001,
        )

        # Provide chunk offset info so merge knows chunk 1 starts at 8.0s
        # (2s overlap with chunk_overlap_seconds=2.0)
        chunks_info = [
            {"chunk_index": 0, "start_seconds": 0.0},
            {"chunk_index": 1, "start_seconds": 8.0},
        ]

        result = await merge_transcripts(
            {
                "chunk_transcripts": [ct0, ct1],
                "chunks": chunks_info,
                "title": "Python Intro",
            }
        )

        # The duplicate segment from chunk 1 should be removed
        texts = [seg["text"] for seg in result["segments"]]
        count_valtozok = sum(
            1 for t in texts if "valtozok es tipusok" in t
        )
        assert count_valtozok == 1, f"Expected 1 occurrence of overlap text, got {count_valtozok}"
        assert any("fuggvenyeket" in t for t in texts)

    @pytest.mark.asyncio
    async def test_merge_adjusts_timestamps(self) -> None:
        """Two chunks, verify second chunk's timestamps are offset correctly."""
        from skills.cubix_course_capture.workflows.transcript_pipeline import (
            merge_transcripts,
        )

        seg_c0 = [_make_segment(0, 0.0, 5.0, "Elso resz.")]
        ct0 = _make_chunk_transcript(
            chunk_index=0,
            segments=seg_c0,
            full_text="Elso resz.",
            duration=5.0,
            cost=0.0005,
        )

        seg_c1 = [_make_segment(0, 0.0, 5.0, "Masodik resz teljesen mas szoveg.")]
        ct1 = _make_chunk_transcript(
            chunk_index=1,
            segments=seg_c1,
            full_text="Masodik resz teljesen mas szoveg.",
            duration=5.0,
            cost=0.0005,
        )

        # Chunk 1 starts at 60s offset (no overlap in this case)
        chunks_info = [
            {"chunk_index": 0, "start_seconds": 0.0},
            {"chunk_index": 1, "start_seconds": 60.0},
        ]

        result = await merge_transcripts(
            {
                "chunk_transcripts": [ct0, ct1],
                "chunks": chunks_info,
                "title": "Offset Test",
            }
        )

        segments = result["segments"]
        assert len(segments) == 2

        # First chunk segment stays at original time
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 5.0

        # Second chunk segment is offset by 60.0
        assert segments[1]["start"] == 60.0
        assert segments[1]["end"] == 65.0

        # Total cost is sum
        assert result["total_cost"] == pytest.approx(0.001)


# ---------------------------------------------------------------------------
# Test 9 - structure_transcript calls LLM
# ---------------------------------------------------------------------------


class TestStructureTranscript:
    @pytest.mark.asyncio
    async def test_structure_calls_llm(self) -> None:
        """Mock ModelClient, verify prompt variables and response_model."""
        # Build the expected structured result
        structured = StructuredTranscript(
            title="",
            summary="Ez egy Python bevezeto kurzus.",
            key_topics=["Python alapok", "Valtozok"],
            sections=[
                TopicSection(
                    title="Bevezetes",
                    start_time=0.0,
                    end_time=60.0,
                    summary="A kurzus bevezetese.",
                    content="Bevezeto szoveg...",
                )
            ],
            vocabulary=[
                VocabularyItem(term="Python", definition="Programozasi nyelv"),
            ],
            cleaned_text="Tisztitott szoveg...",
            structuring_cost=0.0,
        )

        # Mock the _models.generate response (matches ModelCallResult structure)
        mock_output = SimpleNamespace(text="", structured=structured, model_used="test")
        mock_response = SimpleNamespace(output=mock_output, cost_usd=0.0042, model_used="test")

        # Mock prompt definition
        mock_prompt_def = MagicMock()
        mock_prompt_def.compile.return_value = [
            {"role": "system", "content": "You are a structuring assistant."},
            {"role": "user", "content": "Structure this transcript..."},
        ]

        with (
            patch(
                "skills.cubix_course_capture.workflows.transcript_pipeline._models",
            ) as mock_models,
            patch(
                "skills.cubix_course_capture.workflows.transcript_pipeline._prompts",
            ) as mock_prompts,
        ):
            mock_models.generate = AsyncMock(return_value=mock_response)
            mock_prompts.get.return_value = mock_prompt_def

            from skills.cubix_course_capture.workflows.transcript_pipeline import (
                structure_transcript,
            )

            result = await structure_transcript(
                {
                    "full_text": "Ez egy Python bevezeto kurzus szovege.",
                    "title": "Python Alapok",
                    "total_duration_seconds": 3600.0,
                }
            )

        # Verify prompt was fetched with correct key
        mock_prompts.get.assert_called_once_with("cubix/transcript_structurer")

        # Verify compile was called with correct variables
        compile_call = mock_prompt_def.compile.call_args
        variables = compile_call.kwargs.get("variables") or compile_call[1].get("variables")
        assert variables["course_title"] == "Python Alapok"
        assert variables["duration_minutes"] == "60.0"
        assert "Python bevezeto" in variables["transcript_text"]

        # Verify generate was called with correct params
        gen_call = mock_models.generate.call_args
        assert gen_call.kwargs["response_model"] is StructuredTranscript
        assert gen_call.kwargs["temperature"] == 0.3
        assert gen_call.kwargs["max_tokens"] == 8192

        # Verify output
        assert result["title"] == "Python Alapok"
        assert result["structuring_cost"] == 0.0042
        assert len(result["sections"]) == 1
        assert "Python alapok" in result["key_topics"]
        assert result["vocabulary"][0]["term"] == "Python"


# ---------------------------------------------------------------------------
# Test - _format_srt_time helper
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_format_srt_time(self) -> None:
        """Verify SRT timestamp formatting."""
        from skills.cubix_course_capture.workflows.transcript_pipeline import (
            _format_srt_time,
        )

        assert _format_srt_time(0.0) == "00:00:00,000"
        assert _format_srt_time(61.5) == "00:01:01,500"
        assert _format_srt_time(3661.123) == "01:01:01,123"

    def test_segments_overlap_true(self) -> None:
        """Verify _segments_overlap detects similar text."""
        from skills.cubix_course_capture.workflows.transcript_pipeline import (
            _segments_overlap,
        )

        assert _segments_overlap(
            "A valtozok es tipusok fontosak.",
            "A valtozok es tipusok fontosak.",
        )

    def test_segments_overlap_false(self) -> None:
        """Verify _segments_overlap rejects dissimilar text."""
        from skills.cubix_course_capture.workflows.transcript_pipeline import (
            _segments_overlap,
        )

        assert not _segments_overlap(
            "Ez teljesen mas szoveg.",
            "A Python egy programozasi nyelv.",
        )
