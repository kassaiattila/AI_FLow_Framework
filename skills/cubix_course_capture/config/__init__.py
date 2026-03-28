"""Configuration for the Cubix Course Capture transcript pipeline."""

from __future__ import annotations

from pydantic import BaseModel


class TranscriptPipelineConfig(BaseModel):
    """Pipeline configuration for audio extraction, chunking, transcription, and structuring."""

    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    stt_model: str = "whisper-1"
    stt_fallback_model: str = "gpt-4o-mini-transcribe"
    stt_language: str = "hu"
    max_chunk_bytes: int = 24 * 1024 * 1024  # 24MB
    chunk_overlap_seconds: float = 2.0
    sample_rate: int = 16000
    audio_channels: int = 1
    audio_bitrate: str = "64k"
    audio_format: str = "m4a"
    structuring_model: str = "openai/gpt-4o-mini"
    output_dir: str = "./output"


__all__ = [
    "TranscriptPipelineConfig",
]
