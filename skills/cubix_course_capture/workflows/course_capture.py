"""Cubix Course Capture - full RPA + AI pipeline.

Orchestrates: login -> scan -> download -> record -> transcribe -> structure

Usage:
    From test script or CLI, call process_course() with a CourseConfig:

    config = CourseConfig(
        course_name="Cubix_ML_Course",
        course_url="https://cubixedu.com/kepzes/ml-engineer-26q1",
    )
    result = await process_course(config)
"""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from skills.cubix_course_capture.models import (
    CourseConfig,
    CourseStructure,
    LessonInfo,
    LessonResult,
    PipelineState,
    StageStatus,
    WeekInfo,
)
from skills.cubix_course_capture.platforms import get_platform_config
from skills.cubix_course_capture.state import FileStateManager

from aiflow.engine.step import step
from aiflow.engine.workflow import WorkflowBuilder, workflow

# Robot Framework runner (optional - for RF-based RPA)
try:
    from aiflow.tools.robotframework_runner import RobotFrameworkRunner, RobotResult
    _rf_runner = RobotFrameworkRunner()
    _RF_AVAILABLE = True
except ImportError:
    _RF_AVAILABLE = False
    _rf_runner = None  # type: ignore[assignment]

# Transcript pipeline steps are imported for per-video processing
from skills.cubix_course_capture.workflows.transcript_pipeline import (
    chunk_audio,
    extract_audio,
    merge_transcripts,
    probe_audio,
    structure_transcript,
    transcribe,
)

__all__ = [
    "resolve_and_login",
    "scan_course_structure",
    "process_all_lessons",
    "generate_course_report",
    "process_course",
    "course_capture",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[áàâä]", "a", slug)
    slug = re.sub(r"[éèêë]", "e", slug)
    slug = re.sub(r"[íìîï]", "i", slug)
    slug = re.sub(r"[óòôöő]", "o", slug)
    slug = re.sub(r"[úùûüű]", "u", slug)
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug[:80] or "untitled"


def _lesson_dir(base: Path, week_idx: int, lesson_idx: int, slug: str) -> Path:
    """Build the output directory for a single lesson."""
    return base / f"week_{week_idx:02d}" / f"lesson_{lesson_idx:02d}_{slug}"


def _find_latest_file(directory: Path, pattern: str) -> Path | None:
    """Return the most recently modified file matching *pattern* in *directory*."""
    if not directory.exists():
        return None
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


async def _resolve_and_login_rf(data: dict[str, Any], robot_dir: Path) -> dict[str, Any]:
    """Execute login via Robot Framework .robot files."""
    cred_prefix = data.get("credentials_env_prefix", "CUBIX")
    email = os.getenv(f"{cred_prefix}_EMAIL", "")
    password = os.getenv(f"{cred_prefix}_PASSWORD", "")
    course_url = data["course_url"]
    fallback_url = data.get("fallback_url", "")
    output_base = Path(data.get("output_base_dir", "./output"))
    course_name = data.get("course_name", "course")
    course_dir = output_base / course_name
    output_dir = course_dir / "robot_logs"
    output_dir.mkdir(parents=True, exist_ok=True)

    variables = {
        "CUBIX_EMAIL": email,
        "CUBIX_PASSWORD": password,
        "COURSE_URL": course_url,
        "START_URL": course_url,
        "FALLBACK_URL": fallback_url,
        "OUTPUT_DIR": str(course_dir),
    }

    # Step 1: Navigate and resolve course page
    navigate_robot = robot_dir / "navigate_course.robot"
    if navigate_robot.exists():
        result = await _rf_runner.run_task(
            task_name="Resolve_Course_Page",
            robot_file=navigate_robot,
            variables=variables,
            output_dir=output_dir / "navigate",
        )
        logger.info("rf_navigate_done", success=result.success, rc=result.return_code)
    else:
        # Fallback: login.robot
        result = await _rf_runner.run_task(
            task_name="Login_If_Needed",
            robot_file=robot_dir / "login.robot",
            variables=variables,
            output_dir=output_dir / "login",
        )
        logger.info("rf_login_done", success=result.success, rc=result.return_code)

    # Read resolved URL from metadata if available
    resolved_url_path = course_dir / "metadata" / "resolved_url.json"
    if resolved_url_path.exists():
        resolved = json.loads(resolved_url_path.read_text(encoding="utf-8"))
        course_url = resolved.get("course_url", course_url)

    storage_path = course_dir / "metadata" / "auth_state.json"

    return {
        "course_url": course_url,
        "logged_in": result.success,
        "storage_state_path": str(storage_path) if storage_path.exists() else "",
        "rf_mode": True,
    }


async def _scan_structure_rf(data: dict[str, Any], robot_dir: Path) -> dict[str, Any]:
    """Execute course structure scan via Robot Framework."""
    cred_prefix = data.get("credentials_env_prefix", "CUBIX")
    course_url = data.get("course_url", "")
    output_base = Path(data.get("output_base_dir", "./output"))
    course_name = data.get("course_name", "course")
    course_dir = output_base / course_name
    output_dir = course_dir / "robot_logs"

    variables = {
        "CUBIX_EMAIL": os.getenv(f"{cred_prefix}_EMAIL", ""),
        "CUBIX_PASSWORD": os.getenv(f"{cred_prefix}_PASSWORD", ""),
        "COURSE_URL": course_url,
        "OUTPUT_DIR": str(course_dir),
    }

    result = await _rf_runner.run_task(
        task_name="Scan_Weekly_Structure",
        robot_file=robot_dir / "scan_structure.robot",
        variables=variables,
        output_dir=output_dir / "scan",
    )
    logger.info("rf_scan_done", success=result.success, rc=result.return_code)

    # Read scanned structure
    structure_path = course_dir / "metadata" / "course_structure.json"
    if structure_path.exists():
        raw = json.loads(structure_path.read_text(encoding="utf-8"))
        structure = CourseStructure(
            title=course_name,
            url=course_url,
            weeks=[WeekInfo(**w) for w in raw.get("weeks", [])],
            total_lessons=sum(len(w.get("lessons", [])) for w in raw.get("weeks", [])),
        )
        return {"structure": structure.model_dump(mode="json")}

    return {"structure": CourseStructure().model_dump(mode="json"), "error": "Scan failed"}


async def _save_page_html(browser: Any, url: str, output_path: Path) -> None:
    """Navigate to *url* and save the page HTML."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    await browser.navigate(url, wait_until="domcontentloaded")
    html = await browser.page.content()
    output_path.write_text(html, encoding="utf-8")
    logger.info("page_html_saved", url=url, path=str(output_path))


async def _download_materials(
    browser: Any, lesson: LessonInfo, output_dir: Path
) -> list[str]:
    """Download lesson materials (PDFs, presentations) to *output_dir*.

    Returns list of saved file paths.
    """
    saved: list[str] = []
    materials_dir = output_dir / "materials"

    for mat_url in lesson.downloadable_materials:
        if not mat_url:
            continue
        try:
            materials_dir.mkdir(parents=True, exist_ok=True)
            async with browser.page.expect_download() as download_info:
                await browser.page.goto(mat_url)
            download = await download_info.value
            dest = materials_dir / download.suggested_filename
            await download.save_as(str(dest))
            saved.append(str(dest))
            logger.info("material_downloaded", url=mat_url, dest=str(dest))
        except Exception as exc:
            logger.warning("material_download_failed", url=mat_url, error=str(exc))

    return saved


# ---------------------------------------------------------------------------
# Step 1 - resolve_and_login
# ---------------------------------------------------------------------------


@step(name="resolve_and_login", step_type="playwright")
async def resolve_and_login(data: dict[str, Any]) -> dict[str, Any]:
    """Navigate to course URL, handle login if required, and persist session.

    Supports two modes:
    1. Robot Framework (.robot files) - if RF is available and robot files exist
    2. Direct Playwright (async Python) - fallback

    Input:
        course_url, platform, credentials_env_prefix, output_base_dir, course_name
        use_robot_framework: bool (optional, default True if RF available)

    Returns:
        {"course_url": str, "logged_in": bool, "storage_state_path": str}
    """
    use_rf = data.get("use_robot_framework", _RF_AVAILABLE)
    robot_dir = Path(__file__).parent.parent / "robot"

    # --- Robot Framework path ---
    if use_rf and _RF_AVAILABLE and (robot_dir / "login.robot").exists():
        return await _resolve_and_login_rf(data, robot_dir)

    # --- Direct Playwright path ---
    try:
        from aiflow.contrib.playwright import PlaywrightBrowser
        from aiflow.contrib.playwright.browser import BrowserConfig
    except ImportError:
        logger.error("no_rpa_backend", rf=_RF_AVAILABLE, playwright=False)
        return {
            "course_url": data["course_url"],
            "logged_in": False,
            "storage_state_path": "",
            "error": "Neither Robot Framework nor Playwright available",
        }

    platform = data.get("platform", "cubixedu")
    platform_cfg = get_platform_config(platform)
    cred_prefix = data.get("credentials_env_prefix", "CUBIX")
    output_base = Path(data.get("output_base_dir", "./output"))
    course_name = data.get("course_name", "course")
    course_dir = output_base / course_name

    # Check for existing storage state
    storage_path = course_dir / "metadata" / "storage_state.json"
    browser_cfg = BrowserConfig(
        headless=False,  # RPA mode: visible browser
        storage_state_path=str(storage_path) if storage_path.exists() else None,
    )

    browser = PlaywrightBrowser(config=browser_cfg)
    try:
        await browser.launch()

        # Navigate to course URL
        course_url = data["course_url"]
        logger.info("navigating_to_course", url=course_url)
        await browser.navigate(course_url, wait_until="domcontentloaded")

        # Dismiss cookie consent popup
        cookie_sel = platform_cfg.cookie_consent.selectors.get("accept_button", "")
        if cookie_sel:
            await browser.dismiss_cookie_popup(selector=cookie_sel)

        # Check if we landed on a login page (URL changed to login)
        current_url = browser.page.url
        logged_in = False

        needs_login = (
            platform_cfg.login_url in current_url
            or "/login" in current_url.lower()
            or "/bejelentkezes" in current_url.lower()
        )

        if needs_login:
            logger.info("login_required", login_url=current_url)

            email = os.getenv(f"{cred_prefix}_EMAIL", "")
            password = os.getenv(f"{cred_prefix}_PASSWORD", "")

            if not email or not password:
                logger.error(
                    "credentials_not_configured",
                    env_email=f"{cred_prefix}_EMAIL",
                    env_password=f"{cred_prefix}_PASSWORD",
                )
                return {
                    "course_url": course_url,
                    "logged_in": False,
                    "storage_state_path": "",
                    "error": f"Set {cred_prefix}_EMAIL and {cred_prefix}_PASSWORD env vars",
                }

            # Fill login form
            login_sel = platform_cfg.login.selectors
            email_field = login_sel.get("email_field", 'input[type="email"]')
            password_field = login_sel.get("password_field", 'input[type="password"]')

            await browser.fill(email_field, email)
            await browser.fill(password_field, password)

            # Check "remember me" if available
            remember_sel = login_sel.get("remember_me", "")
            if remember_sel:
                try:
                    await browser.check(remember_sel)
                except Exception:
                    logger.debug("remember_me_not_found", selector=remember_sel)

            # Click login
            login_btn = login_sel.get("login_button", 'button[type="submit"]')
            await browser.click(login_btn)

            # Wait for navigation after login
            try:
                await browser.page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                await browser.page.wait_for_load_state("domcontentloaded", timeout=10000)

            # Dismiss cookie popup again after login
            if cookie_sel:
                await browser.dismiss_cookie_popup(selector=cookie_sel)

            # Check if login succeeded by looking for logged-in indicator
            indicator_sel = login_sel.get("logged_in_indicator", "")
            if indicator_sel:
                try:
                    await browser.wait_for(indicator_sel, timeout=5000)
                    logged_in = True
                except Exception:
                    logger.warning("login_indicator_not_found", selector=indicator_sel)
                    # May still be logged in - check if URL changed away from login
                    logged_in = platform_cfg.login_url not in browser.page.url
            else:
                logged_in = platform_cfg.login_url not in browser.page.url

            if logged_in:
                # Navigate to course page (we may be on dashboard after login)
                await browser.navigate(course_url, wait_until="domcontentloaded")
                if cookie_sel:
                    await browser.dismiss_cookie_popup(selector=cookie_sel)
        else:
            # Already logged in (session restored from storage state)
            logged_in = True
            logger.info("session_restored", url=current_url)

        resolved_url = browser.page.url

        # Save storage state for next run
        await browser.save_storage_state(storage_path)

        # Take a screenshot for debugging
        screenshot_dir = course_dir / "metadata" / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        await browser.screenshot(screenshot_dir / "after_login.png")

        logger.info(
            "resolve_and_login.done",
            resolved_url=resolved_url,
            logged_in=logged_in,
        )

        return {
            "course_url": resolved_url,
            "logged_in": logged_in,
            "storage_state_path": str(storage_path),
        }

    finally:
        await browser.close()


# ---------------------------------------------------------------------------
# Step 2 - scan_course_structure
# ---------------------------------------------------------------------------


@step(name="scan_course_structure", step_type="playwright")
async def scan_course_structure(data: dict[str, Any]) -> dict[str, Any]:
    """Scan the course page DOM to extract the full structure.

    Supports Robot Framework or direct Playwright.

    Input:
        course_url, platform, storage_state_path, output_base_dir, course_name

    Returns:
        {"structure": dict, "total_lessons": int, "video_lessons": int}
    """
    use_rf = data.get("use_robot_framework", data.get("rf_mode", _RF_AVAILABLE))
    robot_dir = Path(__file__).parent.parent / "robot"

    if use_rf and _RF_AVAILABLE and (robot_dir / "scan_structure.robot").exists():
        return await _scan_structure_rf(data, robot_dir)

    try:
        from aiflow.contrib.playwright import PlaywrightBrowser
        from aiflow.contrib.playwright.browser import BrowserConfig
    except ImportError:
        logger.error("no_rpa_backend")
        return {"structure": {}, "total_lessons": 0, "video_lessons": 0}

    platform = data.get("platform", "cubixedu")
    platform_cfg = get_platform_config(platform)
    output_base = Path(data.get("output_base_dir", "./output"))
    course_name = data.get("course_name", "course")
    course_dir = output_base / course_name

    storage_path = data.get("storage_state_path", "")

    browser_cfg = BrowserConfig(
        headless=True,
        storage_state_path=storage_path if storage_path else None,
    )

    browser = PlaywrightBrowser(config=browser_cfg)
    try:
        await browser.launch()

        # Navigate to course page
        course_url = data["course_url"]
        await browser.navigate(course_url, wait_until="domcontentloaded")

        # Dismiss cookie consent
        cookie_sel = platform_cfg.cookie_consent.selectors.get("accept_button", "")
        if cookie_sel:
            await browser.dismiss_cookie_popup(selector=cookie_sel)

        # Execute JS to extract course structure
        js_code = platform_cfg.scan_structure_js
        if not js_code:
            logger.error("no_scan_structure_js", platform=platform)
            return {"structure": {}, "total_lessons": 0, "video_lessons": 0}

        raw_result = await browser.evaluate_js(f"({js_code})()")

        # Parse JS result (may be JSON string or dict depending on platform)
        if isinstance(raw_result, str):
            weeks_data = json.loads(raw_result)
        else:
            weeks_data = raw_result

        # Handle result format: may be a list of weeks or a dict with weeks key
        if isinstance(weeks_data, dict):
            course_title = weeks_data.get("title", course_name)
            raw_weeks = weeks_data.get("weeks", [])
        else:
            course_title = course_name
            raw_weeks = weeks_data

        # Build typed models
        weeks: list[WeekInfo] = []
        total_lessons = 0
        video_lessons = 0

        for w in raw_weeks:
            lessons: list[LessonInfo] = []
            for ls in w.get("lessons", []):
                lesson = LessonInfo(
                    index=ls.get("index", 0),
                    title=ls.get("title", ""),
                    url=ls.get("url", ""),
                    has_video=ls.get("has_video", False),
                    has_download=ls.get("has_download", False),
                    slug=ls.get("slug", "") or _slugify(ls.get("title", "")),
                    duration=ls.get("duration", ""),
                    duration_seconds=ls.get("duration_seconds", 0.0),
                    lesson_id=ls.get("lesson_id", ""),
                    video_url=ls.get("video_url", ""),
                    downloadable_materials=ls.get("downloadable_materials", []),
                )
                lessons.append(lesson)
                total_lessons += 1
                if lesson.has_video:
                    video_lessons += 1

            week = WeekInfo(
                index=w.get("index", 0),
                title=w.get("title", ""),
                number=w.get("number", ""),
                lesson_count=len(lessons),
                lessons=lessons,
            )
            weeks.append(week)

        structure = CourseStructure(
            title=course_title,
            url=course_url,
            platform=platform,
            weeks=weeks,
            total_lessons=total_lessons,
            total_video_lessons=video_lessons,
            scanned_at=datetime.now(UTC).isoformat(),
        )

        # Save structure to metadata
        meta_dir = course_dir / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        structure_path = meta_dir / "course_structure.json"
        structure_path.write_text(
            json.dumps(structure.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Screenshot
        screenshots_dir = meta_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        await browser.screenshot(screenshots_dir / "course_structure.png")

        logger.info(
            "scan_course_structure.done",
            title=course_title,
            weeks=len(weeks),
            total_lessons=total_lessons,
            video_lessons=video_lessons,
        )

        return {
            "structure": structure.model_dump(mode="json"),
            "total_lessons": total_lessons,
            "video_lessons": video_lessons,
        }

    finally:
        await browser.close()


# ---------------------------------------------------------------------------
# Step 3 - process_all_lessons (loop over structure)
# ---------------------------------------------------------------------------


@step(name="process_all_lessons", step_type="playwright")
async def process_all_lessons(data: dict[str, Any]) -> dict[str, Any]:
    """Process each lesson: save HTML, download materials, handle videos.

    For video lessons:
      - Opens video in browser
      - Requests operator approval (human-in-the-loop)
      - Collects recorded video from Clipchamp output
      - Collects SRT transcript
      - Runs transcript pipeline on the video

    Input:
        structure (dict), output_base_dir, course_name, platform,
        storage_state_path, clipchamp_output_dir

    Returns:
        {"results": list[LessonResult], "completed": int, "failed": int,
         "total_cost_usd": float}
    """
    try:
        from aiflow.contrib.playwright import PlaywrightBrowser
        from aiflow.contrib.playwright.browser import BrowserConfig
    except ImportError:
        logger.error("playwright_not_available_for_lessons")
        return {"results": [], "completed": 0, "failed": 0, "total_cost_usd": 0.0}

    from aiflow.contrib.human_loop import HumanLoopManager

    # Parse inputs
    structure_data = data.get("structure", {})
    structure = CourseStructure.model_validate(structure_data)
    platform_name = data.get("platform", "cubixedu")
    platform_cfg = get_platform_config(platform_name)
    output_base = Path(data.get("output_base_dir", "./output"))
    course_name = data.get("course_name", "course")
    course_dir = output_base / course_name
    storage_path = data.get("storage_state_path", "")
    clipchamp_dir = Path(
        data.get("clipchamp_output_dir", str(Path.home() / "Videos" / "Clipchamp"))
    )

    # Initialize state manager
    state_mgr = FileStateManager(output_dir=str(course_dir))
    state = state_mgr.load()
    state.course_name = course_name
    state.course_url = structure.url
    state.course_title = structure.title
    if not state.started_at:
        state.started_at = datetime.now(UTC).isoformat()

    # Human loop for operator approvals
    signals_dir = course_dir / "signals"
    human_loop = HumanLoopManager(signals_dir=signals_dir)

    results: list[LessonResult] = []
    global_index = 0

    for week in structure.weeks:
        for lesson in week.lessons:
            slug = lesson.slug or _slugify(lesson.title)
            lesson_output = _lesson_dir(course_dir, week.index, lesson.index, slug)
            lesson_result = LessonResult(
                week_index=week.index,
                lesson_index=lesson.index,
                slug=slug,
                title=lesson.title,
            )

            # Initialize file state for resume tracking
            state_mgr.init_file(
                state,
                global_index=global_index,
                slug=slug,
                title=lesson.title,
                week_index=week.index,
                lesson_index=lesson.index,
            )

            logger.info(
                "processing_lesson",
                week=week.index,
                lesson=lesson.index,
                title=lesson.title,
                has_video=lesson.has_video,
                slug=slug,
            )

            try:
                # --- Sub-step 3a: Save lesson page HTML ---
                browser_cfg = BrowserConfig(
                    headless=True,
                    storage_state_path=storage_path if storage_path else None,
                )
                async with PlaywrightBrowser(config=browser_cfg) as browser:
                    if lesson.url:
                        html_path = lesson_output / f"{slug}.html"
                        await _save_page_html(browser, lesson.url, html_path)

                    # --- Sub-step 3b: Download materials ---
                    if lesson.has_download and lesson.downloadable_materials:
                        await _download_materials(browser, lesson, lesson_output)

                # --- Sub-step 3c: Video processing ---
                if lesson.has_video:
                    video_result = await _process_video_lesson(
                        lesson=lesson,
                        week=week,
                        slug=slug,
                        lesson_output=lesson_output,
                        course_dir=course_dir,
                        platform_cfg=platform_cfg,
                        storage_path=storage_path,
                        clipchamp_dir=clipchamp_dir,
                        human_loop=human_loop,
                        state_mgr=state_mgr,
                        state=state,
                    )
                    lesson_result.video_path = video_result.get("video_path", "")
                    lesson_result.audio_path = video_result.get("audio_path", "")
                    lesson_result.transcript_path = video_result.get("transcript_path", "")
                    lesson_result.structured_path = video_result.get("structured_path", "")
                    lesson_result.srt_path = video_result.get("srt_path", "")
                    lesson_result.cost_usd = video_result.get("cost_usd", 0.0)

                lesson_result.status = "completed"

            except Exception as exc:
                logger.error(
                    "lesson_processing_failed",
                    week=week.index,
                    lesson=lesson.index,
                    slug=slug,
                    error=str(exc),
                )
                lesson_result.status = "failed"
                lesson_result.error = str(exc)

            results.append(lesson_result)
            global_index += 1

            # Save state after every lesson
            state_mgr.save(state)

    # Final state save
    state_mgr.save(state)

    completed = sum(1 for r in results if r.status == "completed")
    failed = sum(1 for r in results if r.status == "failed")
    total_cost = sum(r.cost_usd for r in results)

    logger.info(
        "process_all_lessons.done",
        total=len(results),
        completed=completed,
        failed=failed,
        total_cost_usd=round(total_cost, 4),
    )

    return {
        "results": [r.model_dump() for r in results],
        "completed": completed,
        "failed": failed,
        "total_cost_usd": total_cost,
    }


# ---------------------------------------------------------------------------
# Video lesson sub-workflow
# ---------------------------------------------------------------------------


async def _process_video_lesson(
    *,
    lesson: LessonInfo,
    week: WeekInfo,
    slug: str,
    lesson_output: Path,
    course_dir: Path,
    platform_cfg: Any,
    storage_path: str,
    clipchamp_dir: Path,
    human_loop: Any,
    state_mgr: FileStateManager,
    state: PipelineState,
) -> dict[str, Any]:
    """Handle a single video lesson: open -> notify operator -> collect -> transcribe.

    Returns a dict with paths to video, audio, transcript, structured output, SRT,
    and cost information.
    """
    try:
        from aiflow.contrib.playwright import PlaywrightBrowser
        from aiflow.contrib.playwright.browser import BrowserConfig
    except ImportError:
        return {"error": "playwright not installed"}

    result: dict[str, Any] = {}

    # --- Open video in browser (visible mode for operator) ---
    video_browser_cfg = BrowserConfig(
        headless=False,  # Must be visible for operator screen recording
        storage_state_path=storage_path if storage_path else None,
    )

    video_url = lesson.video_url or lesson.url
    if not video_url:
        logger.warning("no_video_url", slug=slug)
        return result

    async with PlaywrightBrowser(config=video_browser_cfg) as browser:
        await browser.navigate(video_url, wait_until="domcontentloaded")

        # Dismiss cookie consent
        cookie_sel = platform_cfg.cookie_consent.selectors.get("accept_button", "")
        if cookie_sel:
            await browser.dismiss_cookie_popup(selector=cookie_sel)

        # Wait for video player to load
        video_sel = platform_cfg.video.selectors.get("player_container", "")
        if video_sel:
            try:
                await browser.wait_for(video_sel, timeout=10000)
            except Exception:
                logger.warning("video_player_not_found", selector=video_sel, slug=slug)

        # Take screenshot of video player
        screenshots_dir = lesson_output / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        await browser.screenshot(screenshots_dir / "video_player.png")

        # Get video info via JS
        get_info_js = platform_cfg.get_video_info_js
        if get_info_js:
            try:
                video_info_raw = await browser.evaluate_js(f"({get_info_js})()")
                if isinstance(video_info_raw, str):
                    video_info = json.loads(video_info_raw)
                else:
                    video_info = video_info_raw or {}
                logger.info("video_info", slug=slug, info=video_info)
            except Exception as exc:
                logger.warning("video_info_js_failed", error=str(exc))

        # --- Request operator to start recording ---
        logger.info(
            "requesting_operator_recording",
            slug=slug,
            title=lesson.title,
            video_url=video_url,
        )

        approval = await human_loop.request_approval(
            question=(
                f"Start screen recording for lesson: {lesson.title}\n"
                f"URL: {video_url}\n"
                f"Week {week.index}, Lesson {lesson.index}\n\n"
                f"1. Start Clipchamp/OBS screen recording\n"
                f"2. Play the video in the browser\n"
                f"3. When done, stop recording and select 'Done'"
            ),
            context={
                "slug": slug,
                "lesson_title": lesson.title,
                "video_url": video_url,
                "week": week.index,
                "lesson": lesson.index,
            },
            options=["Done", "Skip"],
            timeout_minutes=120,
            poll_interval_seconds=10,
        )

    if not approval.approved:
        logger.info("video_recording_skipped", slug=slug, notes=approval.operator_notes)
        return result

    # --- Collect recorded video from Clipchamp output ---
    video_path = _find_latest_file(clipchamp_dir, "*.mp4")
    if not video_path:
        logger.warning("no_recorded_video_found", clipchamp_dir=str(clipchamp_dir))
        return result

    # Move video to lesson output
    video_dest = lesson_output / f"{slug}.mp4"
    video_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(video_path), str(video_dest))
    result["video_path"] = str(video_dest)
    logger.info("video_collected", source=str(video_path), dest=str(video_dest))

    # --- Collect SRT if available from external captioning ---
    srt_source = _find_latest_file(clipchamp_dir, "*.srt")
    if srt_source:
        srt_dest = lesson_output / f"{slug}.srt"
        shutil.move(str(srt_source), str(srt_dest))
        result["srt_path"] = str(srt_dest)
        logger.info("srt_collected", source=str(srt_source), dest=str(srt_dest))

    # --- Run transcript pipeline on the video ---
    try:
        transcript_result = await _run_transcript_pipeline(
            video_path=str(video_dest),
            slug=slug,
            title=lesson.title,
            lesson_output=lesson_output,
            state_mgr=state_mgr,
            state=state,
        )
        result.update(transcript_result)
    except Exception as exc:
        logger.error("transcript_pipeline_failed", slug=slug, error=str(exc))
        state_mgr.set_stage(state, slug, "transcribe", StageStatus.FAILED, error=str(exc))

    return result


# ---------------------------------------------------------------------------
# Transcript pipeline integration
# ---------------------------------------------------------------------------


async def _run_transcript_pipeline(
    *,
    video_path: str,
    slug: str,
    title: str,
    lesson_output: Path,
    state_mgr: FileStateManager,
    state: PipelineState,
) -> dict[str, Any]:
    """Run the six-step transcript pipeline on a single video file.

    Delegates to the steps defined in transcript_pipeline.py:
    probe -> extract -> chunk -> transcribe -> merge -> structure

    Tracks state at each step for resume support.
    """
    result: dict[str, Any] = {}
    file_state = state.files.get(slug)

    # Determine where to resume from
    resume_stage = file_state.get_first_incomplete_stage() if file_state else "probe"

    # --- Stage 1: Probe ---
    if resume_stage in ("probe", None):
        state_mgr.set_stage(state, slug, "probe", StageStatus.IN_PROGRESS)
        state_mgr.save(state)

        probe_result = await probe_audio({"file_path": video_path})
        if file_state:
            file_state.duration_seconds = probe_result.get("duration_seconds", 0.0)

        state_mgr.set_stage(state, slug, "probe", StageStatus.COMPLETED)
        state_mgr.save(state)
    else:
        # Load existing probe data (we need duration for downstream steps)
        probe_result = {"file_path": video_path, "duration_seconds": 0.0}
        if file_state:
            probe_result["duration_seconds"] = file_state.duration_seconds

    # --- Stage 2: Extract audio ---
    if resume_stage in ("probe", "extract", None):
        state_mgr.set_stage(state, slug, "extract", StageStatus.IN_PROGRESS)
        state_mgr.save(state)

        extract_result = await extract_audio({
            "file_path": video_path,
            "duration_seconds": probe_result.get("duration_seconds", 0.0),
        })

        audio_path = extract_result["audio_path"]
        result["audio_path"] = audio_path
        if file_state:
            file_state.audio_path = audio_path

        state_mgr.set_stage(state, slug, "extract", StageStatus.COMPLETED)
        state_mgr.save(state)
    else:
        audio_path = file_state.audio_path if file_state else ""
        extract_result = {"audio_path": audio_path, "file_size_bytes": 0, "duration_seconds": 0.0}

    # --- Stage 3: Chunk audio ---
    if resume_stage in ("probe", "extract", "chunk", None):
        state_mgr.set_stage(state, slug, "chunk", StageStatus.IN_PROGRESS)
        state_mgr.save(state)

        chunk_result = await chunk_audio({
            "audio_path": extract_result["audio_path"],
            "file_size_bytes": extract_result.get("file_size_bytes", 0),
            "duration_seconds": extract_result.get("duration_seconds", 0.0),
        })

        if file_state:
            file_state.chunk_count = chunk_result.get("total_chunks", 0)

        state_mgr.set_stage(state, slug, "chunk", StageStatus.COMPLETED)
        state_mgr.save(state)
    else:
        chunk_result = {"chunks": [], "total_chunks": 0}

    # --- Stage 4: Transcribe ---
    if resume_stage in ("probe", "extract", "chunk", "transcribe", None):
        state_mgr.set_stage(state, slug, "transcribe", StageStatus.IN_PROGRESS)
        state_mgr.save(state)

        transcribe_result = await transcribe({
            "chunks": chunk_result["chunks"],
        })

        # Calculate STT cost
        stt_cost = sum(
            ct.get("cost", 0.0)
            for ct in transcribe_result.get("chunk_transcripts", [])
        )
        state_mgr.update_cost(state, slug, stt_cost=stt_cost)

        state_mgr.set_stage(state, slug, "transcribe", StageStatus.COMPLETED)
        state_mgr.save(state)
    else:
        transcribe_result = {"chunk_transcripts": []}

    # --- Stage 5: Merge transcripts ---
    if resume_stage in ("probe", "extract", "chunk", "transcribe", "merge", None):
        state_mgr.set_stage(state, slug, "merge", StageStatus.IN_PROGRESS)
        state_mgr.save(state)

        merge_result = await merge_transcripts({
            "chunk_transcripts": transcribe_result["chunk_transcripts"],
            "chunks": chunk_result.get("chunks", []),
            "title": title,
        })

        # Save SRT file
        srt_content = merge_result.get("srt_content", "")
        if srt_content:
            srt_path = lesson_output / f"{slug}_whisper.srt"
            srt_path.parent.mkdir(parents=True, exist_ok=True)
            srt_path.write_text(srt_content, encoding="utf-8")
            result["srt_path"] = str(srt_path)
            if file_state:
                file_state.srt_path = str(srt_path)

        # Save merged transcript JSON
        transcript_path = lesson_output / f"{slug}_transcript.json"
        transcript_path.write_text(
            json.dumps(merge_result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        result["transcript_path"] = str(transcript_path)
        if file_state:
            file_state.transcript_path = str(transcript_path)

        state_mgr.set_stage(state, slug, "merge", StageStatus.COMPLETED)
        state_mgr.save(state)
    else:
        merge_result = {}

    # --- Stage 6: Structure transcript ---
    if resume_stage in ("probe", "extract", "chunk", "transcribe", "merge", "structure", None):
        state_mgr.set_stage(state, slug, "structure", StageStatus.IN_PROGRESS)
        state_mgr.save(state)

        structured_result = await structure_transcript({
            "merged_transcript": merge_result,
            "title": title,
        })

        # Save structured output
        structured_path = lesson_output / f"{slug}_structured.json"
        structured_path.write_text(
            json.dumps(structured_result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        result["structured_path"] = str(structured_path)
        if file_state:
            file_state.structured_path = str(structured_path)

        structuring_cost = structured_result.get("structuring_cost", 0.0)
        state_mgr.update_cost(state, slug, structuring_cost=structuring_cost)

        state_mgr.set_stage(state, slug, "structure", StageStatus.COMPLETED)
        state_mgr.save(state)

    # Total cost
    if file_state:
        result["cost_usd"] = file_state.total_cost

    return result


# ---------------------------------------------------------------------------
# Step 4 - generate_course_report
# ---------------------------------------------------------------------------


@step(name="generate_course_report")
async def generate_course_report(data: dict[str, Any]) -> dict[str, Any]:
    """Aggregate results and generate batch report and cost summary.

    Input:
        results (list[dict]), completed, failed, total_cost_usd,
        output_base_dir, course_name, structure (dict)

    Returns:
        {"report_path": str, "cost_summary_path": str, "summary": dict}
    """
    output_base = Path(data.get("output_base_dir", "./output"))
    course_name = data.get("course_name", "course")
    course_dir = output_base / course_name
    meta_dir = course_dir / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)

    results_raw: list[dict[str, Any]] = data.get("results", [])
    results = [LessonResult.model_validate(r) for r in results_raw]
    completed = data.get("completed", 0)
    failed = data.get("failed", 0)
    total_cost = data.get("total_cost_usd", 0.0)

    structure_data = data.get("structure", {})
    course_title = structure_data.get("title", course_name)

    now = datetime.now(UTC).isoformat()

    # --- Generate batch_report.md ---
    report_lines: list[str] = [
        f"# Course Capture Report: {course_title}",
        "",
        f"**Generated:** {now}",
        f"**Course:** {course_title}",
        f"**URL:** {structure_data.get('url', 'N/A')}",
        f"**Platform:** {structure_data.get('platform', 'N/A')}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total lessons | {len(results)} |",
        f"| Completed | {completed} |",
        f"| Failed | {failed} |",
        f"| Skipped | {len(results) - completed - failed} |",
        f"| Total cost (USD) | ${total_cost:.4f} |",
        "",
        "## Lesson Details",
        "",
        "| Week | Lesson | Title | Status | Cost | Error |",
        "|------|--------|-------|--------|------|-------|",
    ]

    for r in results:
        error_text = r.error[:40] + "..." if len(r.error) > 40 else r.error
        report_lines.append(
            f"| {r.week_index} | {r.lesson_index} | {r.title[:40]} | "
            f"{r.status} | ${r.cost_usd:.4f} | {error_text} |"
        )

    report_lines.extend([
        "",
        "## Failed Lessons",
        "",
    ])

    failed_results = [r for r in results if r.status == "failed"]
    if failed_results:
        for r in failed_results:
            report_lines.append(
                f"- **Week {r.week_index}, Lesson {r.lesson_index}** ({r.title}): {r.error}"
            )
    else:
        report_lines.append("No failed lessons.")

    report_text = "\n".join(report_lines) + "\n"
    report_path = meta_dir / "batch_report.md"
    report_path.write_text(report_text, encoding="utf-8")

    # --- Generate cost_summary.json ---
    cost_summary = {
        "course_name": course_name,
        "course_title": course_title,
        "generated_at": now,
        "total_lessons": len(results),
        "completed": completed,
        "failed": failed,
        "total_cost_usd": round(total_cost, 6),
        "per_lesson_costs": [
            {
                "week": r.week_index,
                "lesson": r.lesson_index,
                "slug": r.slug,
                "title": r.title,
                "cost_usd": round(r.cost_usd, 6),
                "status": r.status,
            }
            for r in results
        ],
        "cost_breakdown": {
            "stt_estimated_usd": round(total_cost * 0.85, 6),
            "structuring_estimated_usd": round(total_cost * 0.15, 6),
        },
    }

    cost_path = meta_dir / "cost_summary.json"
    cost_path.write_text(
        json.dumps(cost_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary = {
        "course_title": course_title,
        "total_lessons": len(results),
        "completed": completed,
        "failed": failed,
        "total_cost_usd": total_cost,
    }

    logger.info(
        "generate_course_report.done",
        report_path=str(report_path),
        cost_path=str(cost_path),
        **summary,
    )

    return {
        "report_path": str(report_path),
        "cost_summary_path": str(cost_path),
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# High-level orchestrator
# ---------------------------------------------------------------------------


async def process_course(config: CourseConfig) -> dict[str, Any]:
    """Main entry point -- processes an entire course end-to-end.

    1. Initialize state manager
    2. Load or create pipeline state
    3. Login and scan course structure (if not already done)
    4. Process each lesson (with resume support)
    5. For video lessons: run transcript pipeline
    6. Generate final report

    Args:
        config: Course configuration (name, URL, platform, credentials).

    Returns:
        Final report dict with summary, paths, and cost information.
    """
    output_dir = Path(config.output_base_dir) / config.course_name
    state_mgr = FileStateManager(output_dir=str(output_dir))
    state = state_mgr.load()

    common_data = {
        "course_name": config.course_name,
        "course_url": config.course_url,
        "platform": config.platform,
        "credentials_env_prefix": config.credentials_env_prefix,
        "output_base_dir": config.output_base_dir,
    }

    # --- Step 1: Login ---
    logger.info("process_course.start", course_name=config.course_name, url=config.course_url)

    login_result = await resolve_and_login({
        **common_data,
    })

    if not login_result.get("logged_in") and not login_result.get("storage_state_path"):
        logger.error("login_failed", result=login_result)
        return {"error": "Login failed", "login_result": login_result}

    # --- Step 2: Scan structure ---
    scan_result = await scan_course_structure({
        **common_data,
        "storage_state_path": login_result.get("storage_state_path", ""),
        "course_url": login_result.get("course_url", config.course_url),
    })

    if not scan_result.get("structure"):
        logger.error("scan_failed", result=scan_result)
        return {"error": "Course structure scan failed", "scan_result": scan_result}

    # --- Step 3: Process all lessons ---
    lessons_result = await process_all_lessons({
        **common_data,
        "structure": scan_result["structure"],
        "storage_state_path": login_result.get("storage_state_path", ""),
    })

    # --- Step 4: Generate report ---
    report_result = await generate_course_report({
        **common_data,
        "results": lessons_result.get("results", []),
        "completed": lessons_result.get("completed", 0),
        "failed": lessons_result.get("failed", 0),
        "total_cost_usd": lessons_result.get("total_cost_usd", 0.0),
        "structure": scan_result["structure"],
    })

    logger.info(
        "process_course.done",
        course_name=config.course_name,
        summary=report_result.get("summary"),
    )

    return {
        "login": login_result,
        "scan": scan_result,
        "lessons": lessons_result,
        "report": report_result,
    }


# ---------------------------------------------------------------------------
# Workflow definition
# ---------------------------------------------------------------------------


@workflow(name="course-capture", version="1.0.0", skill="cubix_course_capture")
def course_capture(wf: WorkflowBuilder) -> None:
    """RPA + AI hybrid: login -> scan -> download -> record -> transcribe -> structure."""
    wf.step(resolve_and_login)
    wf.step(scan_course_structure, depends_on=["resolve_and_login"])
    wf.step(process_all_lessons, depends_on=["scan_course_structure"])
    wf.step(generate_course_report, depends_on=["process_all_lessons"])
