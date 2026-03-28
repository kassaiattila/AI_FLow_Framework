"""Pydantic models for the Cubix Course Capture transcript pipeline.

Defines typed I/O models for each stage of the pipeline:
audio probing, extraction, chunking, transcription, merging, and structuring.
Also includes course structure, lesson tracking, and pipeline state models.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AudioProbeResult(BaseModel):
    """Result of probing an audio/video file with ffprobe."""

    file_path: str
    duration_seconds: float
    codec: str = "aac"
    sample_rate: int = 16000
    channels: int = 1
    bitrate: int = 64000
    file_size_bytes: int = 0


class ExtractAudioOutput(BaseModel):
    """Output of the audio extraction step."""

    audio_path: str
    duration_seconds: float
    file_size_bytes: int


class ChunkInfo(BaseModel):
    """Metadata for a single audio chunk."""

    chunk_index: int
    file_path: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float


class ChunkOutput(BaseModel):
    """Output of the chunking step."""

    chunks: list[ChunkInfo]
    total_chunks: int


class TranscriptSegment(BaseModel):
    """A single timed segment within a transcript."""

    id: int
    start: float
    end: float
    text: str
    confidence: float = 1.0


class ChunkTranscript(BaseModel):
    """Transcript result for a single audio chunk."""

    chunk_index: int
    model: str
    language: str = "hu"
    duration_seconds: float = 0.0
    segments: list[TranscriptSegment]
    full_text: str = ""
    cost: float = 0.0


class MergedTranscript(BaseModel):
    """Merged transcript from all chunks."""

    title: str
    total_duration_seconds: float = 0.0
    segments: list[TranscriptSegment]
    full_text: str = ""
    total_cost: float = 0.0
    chunk_count: int = 1


class TopicSection(BaseModel):
    """A thematic section identified within the transcript."""

    title: str
    start_time: float = 0.0
    end_time: float = 0.0
    summary: str = ""
    content: str = ""


class VocabularyItem(BaseModel):
    """A technical term extracted from the transcript with its definition."""

    term: str
    definition: str = ""


class StructuredTranscript(BaseModel):
    """Final structured output of the transcript pipeline."""

    title: str
    summary: str = ""
    key_topics: list[str] = Field(default_factory=list)
    sections: list[TopicSection] = Field(default_factory=list)
    vocabulary: list[VocabularyItem] = Field(default_factory=list)
    cleaned_text: str = ""
    structuring_cost: float = 0.0


# === Course Structure Models (RPA) ===


class CourseConfig(BaseModel):
    """Parameterizable course configuration."""

    course_name: str  # "Cubix_ML_Course" - directory + DB key
    course_url: str
    fallback_url: str = ""
    platform: str = "cubixedu"  # cubixedu | udemy | coursera
    credentials_env_prefix: str = "CUBIX"  # -> CUBIX_EMAIL, CUBIX_PASSWORD
    language: str = "hu"
    output_base_dir: str = "./output"  # output/{course_name}/ becomes root
    version: str = "v1"


class LessonInfo(BaseModel):
    """A single lesson within a course week."""

    index: int
    title: str
    url: str
    has_video: bool = False
    has_download: bool = False
    slug: str = ""
    video_url: str = ""
    lesson_id: str = ""
    duration: str = ""  # "MM:SS" or "HH:MM:SS"
    duration_seconds: float = 0.0
    downloadable_materials: list[str] = Field(default_factory=list)


class WeekInfo(BaseModel):
    """A course week/chapter containing lessons."""

    index: int
    title: str
    number: str = ""
    lesson_count: int = 0
    lessons: list[LessonInfo] = Field(default_factory=list)


class CourseStructure(BaseModel):
    """Full course structure from platform scan."""

    title: str = ""
    url: str = ""
    platform: str = "cubixedu"
    weeks: list[WeekInfo] = Field(default_factory=list)
    total_lessons: int = 0
    total_video_lessons: int = 0
    scanned_at: str = ""


class LessonResult(BaseModel):
    """Processing result for a single lesson."""

    week_index: int
    lesson_index: int
    slug: str
    title: str = ""
    status: str = "pending"  # pending | completed | failed | skipped
    error: str = ""
    video_path: str = ""
    audio_path: str = ""
    transcript_path: str = ""
    structured_path: str = ""
    srt_path: str = ""
    cost_usd: float = 0.0


# === Processing State Models ===


class StageStatus(StrEnum):
    """Status of a single processing stage."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FileProcessingState(BaseModel):
    """Per-file processing state with stage tracking."""

    global_index: int
    slug: str
    title: str
    week_index: int = 0
    lesson_index: int = 0

    # Stage statuses
    probe: StageStatus = StageStatus.PENDING
    extract: StageStatus = StageStatus.PENDING
    chunk: StageStatus = StageStatus.PENDING
    transcribe: StageStatus = StageStatus.PENDING
    merge: StageStatus = StageStatus.PENDING
    structure: StageStatus = StageStatus.PENDING

    # Paths
    video_path: str = ""
    audio_path: str = ""
    chunk_count: int = 0
    transcript_path: str = ""
    structured_path: str = ""
    srt_path: str = ""

    # Costs
    duration_seconds: float = 0.0
    stt_cost: float = 0.0
    structuring_cost: float = 0.0
    total_cost: float = 0.0
    last_error: str = ""

    def get_first_incomplete_stage(self) -> str | None:
        """Return the name of the first stage that is not completed, or None."""
        for stage in ["probe", "extract", "chunk", "transcribe", "merge", "structure"]:
            if getattr(self, stage) != StageStatus.COMPLETED:
                return stage
        return None


class PipelineState(BaseModel):
    """Full pipeline state - saved as JSON for resume support."""

    course_name: str = ""
    course_url: str = ""
    course_title: str = ""
    version: str = "v1"
    started_at: str = ""
    updated_at: str = ""
    files: dict[str, FileProcessingState] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0


__all__ = [
    # Transcript pipeline models
    "AudioProbeResult",
    "ExtractAudioOutput",
    "ChunkInfo",
    "ChunkOutput",
    "TranscriptSegment",
    "ChunkTranscript",
    "MergedTranscript",
    "TopicSection",
    "VocabularyItem",
    "StructuredTranscript",
    # Course structure models
    "CourseConfig",
    "LessonInfo",
    "WeekInfo",
    "CourseStructure",
    "LessonResult",
    # Processing state models
    "StageStatus",
    "FileProcessingState",
    "PipelineState",
]
