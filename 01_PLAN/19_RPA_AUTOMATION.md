# AIFlow - RPA es Feluleti Automatizacios Skill-ek

## 1. Miert Kell RPA az AIFlow-ban?

Az AIFlow eddig **AI-logika** workflow-kra fokuszalt (classify, extract, generate).
De vallalati automatizacio **feluleti interakciot** is igenyel:
- Weboldalak adatgyujtese (scraping, form kitoltes)
- Dokumentum letoltes kulso rendszerekbol
- Operatori lepesel vegyitett automatizaciok (hybrid)
- Fajl feldolgozasi pipeline-ok (audio, video, PDF konverzio)

### Meglevo POC-ok (BestIx Kft)

**1. Cubix EDU Course Capture** (`automation/`)
- Temporal workflow + Robot Framework + Playwright
- Kurzus struktura felterkepezes, videok rogzitese, SRT gyujtese
- Operatori lepesek (Clipchamp rogzites) + automatikus feldolgozas
- Output: strukturalt mappa (HTML, video, SRT, anyagok)

**2. Transcript Pipeline** (`transcript_pipeline/`)
- Typer CLI + Pydantic + OpenAI STT + GPT strukturalas
- Video -> audio kinyeres (ffmpeg) -> STT (whisper) -> LLM strukturalas
- 6 fázisú pipeline: probe -> extract -> chunk -> transcribe -> merge -> structure
- Resumable state management, koltseg tracking

**Tanulsag:** Ezek a mintak **tucatjaval** ismetlodnek mas kontextusban
(mas weboldalak, mas dokumentumok, mas AI feldolgozas).

---

## 2. RPA Skill Architektura az AIFlow-ban

### 2.1 Uj Skill Tipus: RPA Skill

```yaml
# skills/cubix_course_capture/skill.yaml
name: cubix_course_capture
display_name: "Web Course Capture & Transcription"
version: "1.0.0"
skill_type: rpa                          # UJ: rpa | ai | hybrid
framework_requires: ">=1.0.0"

capabilities:
  - web_navigation
  - file_collection
  - video_processing
  - speech_to_text
  - llm_structuring
  - operator_assisted                    # Human-in-the-loop (operatori lepesek)

required_tools:                          # UJ szekció: kulso eszkok
  - name: playwright
    version: ">=1.40"
  - name: ffmpeg
    version: ">=6.0"
  - name: ffprobe
    version: ">=6.0"

required_models:
  - name: "openai/whisper-1"
    type: speech_to_text
    usage: "Magyar nyelvű átírás"
  - name: "openai/gpt-4.1-mini"
    type: llm
    usage: "Transzkript strukturálás"

workflows:
  - course-capture                       # Teljes kurzus gyujtes
  - transcript-processing                # Hanganyag feldolgozas
```

### 2.2 Workflow DAG: Course Capture

```python
@workflow(name="course-capture", version="1.0.0", skill="cubix_course_capture")
def course_capture(wf: WorkflowBuilder):
    # Web navigacio
    wf.step(resolve_url)                          # Playwright: URL feloldas
    wf.step(login_if_needed, depends_on=["resolve_url"])  # Playwright: bejelentkezes
    wf.step(scan_structure, depends_on=["login_if_needed"])  # Playwright: kurzus terkep

    # Per-hetes feldolgozas (sub-workflow)
    wf.step(get_weeks, depends_on=["scan_structure"])
    wf.parallel_map(                               # LangGraph "Send" minta!
        source="get_weeks",
        target_workflow="week-processing",
        input_mapping={"week": "item"},
    )

    # Osszesites
    wf.step(generate_report, depends_on=["parallel_map"])
```

```python
@workflow(name="week-processing", version="1.0.0", skill="cubix_course_capture")
def week_processing(wf: WorkflowBuilder):
    wf.step(save_week_metadata)

    # Per-lecke feldolgozas
    wf.step(get_lessons, depends_on=["save_week_metadata"])
    wf.for_each(
        source="get_lessons",
        steps=[
            "save_lesson_page",        # Playwright: HTML mentes
            "download_materials",       # Playwright: PDF/pptx letoltes
        ],
    )

    # Video leckek (ha vannak)
    wf.step(filter_video_lessons, depends_on=["for_each"])
    wf.branch(
        on="filter_video_lessons",
        when={"output.has_videos": ["process_videos"]},
        otherwise="finish",
    )

    # Video feldolgozas (operatori lepes!)
    wf.step(open_video_in_browser)      # Playwright: video megnyitas
    wf.step(notify_operator_record,     # HITL: "Inditsa el a rogzitest!"
            depends_on=["open_video_in_browser"],
            human_loop=True)            # Pauzal amig az operator jelez
    wf.step(collect_video_file,         # File: video osszegyujtese
            depends_on=["notify_operator_record"])
    wf.step(collect_transcript,         # File: SRT gyujtese
            depends_on=["collect_video_file"])
```

### 2.3 Workflow DAG: Transcript Processing

```python
@workflow(name="transcript-processing", version="1.0.0", skill="cubix_course_capture")
def transcript_processing(wf: WorkflowBuilder):
    wf.step(probe_audio)                # ffprobe: metadata
    wf.step(extract_audio,              # ffmpeg: video -> m4a
            depends_on=["probe_audio"])
    wf.step(chunk_if_needed,            # ffmpeg: split ha > 24MB
            depends_on=["extract_audio"])
    wf.step(transcribe_chunks,          # OpenAI STT: whisper-1
            depends_on=["chunk_if_needed"],
            retry=RetryPolicy(max_retries=3, backoff_base=2.0))
    wf.step(merge_transcripts,          # Dedup + merge
            depends_on=["transcribe_chunks"])
    wf.step(structure_with_llm,         # GPT: strukturalas
            depends_on=["merge_transcripts"],
            retry=RetryPolicy(max_retries=2))
    wf.step(generate_outputs,           # SRT + JSON + Markdown
            depends_on=["structure_with_llm"])
```

---

## 3. RPA Step Tipusok (Uj Framework Bovites)

### 3.1 Playwright Step

```python
# src/aiflow/contrib/playwright/step.py

@step(
    name="navigate_and_extract",
    output_types={"html": str, "data": dict},
    timeout=60,
    step_type="playwright",              # UJ: step tipus jelzes
)
async def navigate_and_extract(
    input_data: NavigateInput,
    ctx: ExecutionContext,
    browser: PlaywrightBrowser,          # DI: Playwright browser instance
) -> NavigateOutput:
    page = await browser.new_page()
    await page.goto(input_data.url)
    await page.wait_for_selector(input_data.selector)
    html = await page.content()
    data = await page.evaluate(input_data.js_extract)
    await page.close()
    return NavigateOutput(html=html, data=data)
```

### 3.2 Shell/FFmpeg Step

```python
# src/aiflow/contrib/shell/step.py

@step(
    name="extract_audio",
    output_types={"audio_path": str, "duration_seconds": float},
    timeout=300,
    step_type="shell",
)
async def extract_audio(
    input_data: ExtractAudioInput,
    ctx: ExecutionContext,
    shell: ShellExecutor,                # DI: sandboxed shell
) -> ExtractAudioOutput:
    result = await shell.run(
        f"ffmpeg -i {input_data.video_path} -vn -ar 16000 -ac 1 {input_data.output_path}"
    )
    duration = await shell.run(
        f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {input_data.output_path}"
    )
    return ExtractAudioOutput(audio_path=input_data.output_path, duration_seconds=float(duration.stdout))
```

### 3.3 Operator Step (Human-in-the-Loop)

```python
@step(
    name="operator_record_video",
    output_types={"approved": bool, "notes": str},
    timeout=3600,                        # 1 ora varakozas operatorra
    step_type="human",
)
async def operator_record_video(
    input_data: OperatorInput,
    ctx: ExecutionContext,
) -> OperatorOutput:
    # A WorkflowRunner automatikusan:
    # 1. Letrehozza a HumanReviewRequest-et
    # 2. Pauzalja a workflow-t (status="awaiting_review")
    # 3. Notification megy (Slack/email/UI)
    # 4. Operator az UI-on/API-n "approve"-ol
    # 5. Workflow folytatodik
    raise HumanReviewRequiredError(
        question=f"Inditsa el a video rogzitest: {input_data.lesson_title}",
        context={"url": input_data.video_url, "lesson": input_data.lesson_title},
        options=["Rogzites kesz", "Kihagyas"],
        priority="medium",
        deadline_minutes=60,
    )
```

---

## 4. Altalanositott RPA Mintak

### 4.1 Web Scraping Skill Template

```
skills/web_scraper_template/
    skill.yaml
    workflow.py                  # navigate -> extract -> transform -> store
    agents/
        navigator.py             # Playwright: login, navigate, wait
        extractor.py             # Playwright: DOM data extraction
        transformer.py           # AI: strukturalas, klasszifikacio
    config/
        selectors.yaml           # CSS/XPath selectors per oldal
        credentials.yaml.enc     # Titkositott credentials
    tests/
```

### 4.2 Document Processing Skill Template

```
skills/document_processor_template/
    skill.yaml
    workflow.py                  # discover -> download -> parse -> ai_process -> store
    agents/
        discoverer.py            # Fajlok felderitese (S3, SharePoint, lokalis)
        downloader.py            # Letoltes + deduplikacio (hash check)
        parser.py                # PDF/DOCX/audio/video -> text
        processor.py             # AI: STT, classification, extraction
        storer.py                # Output mentes (DB, fajlrendszer, vector store)
```

### 4.3 Hybrid (Operator-Assisted) Skill Template

```
skills/hybrid_automation_template/
    skill.yaml
    workflow.py                  # auto_steps -> operator_step -> auto_steps
    agents/
        auto_navigator.py        # Automatikus web navigacio
        operator_notifier.py     # HITL: operator ertesites + varakozas
        auto_collector.py        # Automatikus eredmeny gyujtes
        ai_processor.py          # AI feldolgozas
```

---

## 5. Framework Bovitesek (src/aiflow/contrib/)

### 5.1 Playwright Integracio

```
src/aiflow/contrib/playwright/
    __init__.py
    browser.py               # PlaywrightBrowser DI service
    context.py               # BrowserContext management (session, cookies)
    page_actions.py          # Kozos muveletek (login, navigate, wait, extract)
    screenshot.py            # Debug screenshot mentes
    config.py                # Playwright settings (headless, timeout, viewport)
```

```python
# src/aiflow/contrib/playwright/browser.py
class PlaywrightBrowser:
    """DI-injectable Playwright browser service."""

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self._playwright = None
        self._browser = None

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)

    async def new_page(self, **kwargs) -> Page:
        context = await self._browser.new_context(**kwargs)
        return await context.new_page()

    async def stop(self):
        if self._browser: await self._browser.close()
        if self._playwright: await self._playwright.stop()
```

**DI Container bovites:**
```python
class Container:
    # ... meglevo szolgaltatasok ...
    playwright_browser: PlaywrightBrowser  # UJ: RPA skill-eknek
    shell_executor: ShellExecutor          # UJ: ffmpeg, script futtatás
```

### 5.2 Shell Executor (Sandboxed)

```
src/aiflow/contrib/shell/
    __init__.py
    executor.py              # ShellExecutor: async subprocess wrapper
    sandbox.py               # Sandboxing (allowed commands, path restrictions)
    config.py                # Shell settings (timeout, allowed_commands)
```

```python
class ShellExecutor:
    """Sandboxed shell command executor."""

    ALLOWED_COMMANDS = {"ffmpeg", "ffprobe", "pandoc", "wkhtmltopdf", "python"}

    async def run(self, command: str, timeout: int = 300) -> ShellResult:
        # Validate command against allowlist
        cmd_name = command.split()[0]
        if cmd_name not in self.ALLOWED_COMMANDS:
            raise SecurityError(f"Command '{cmd_name}' not in allowlist")
        # Execute
        proc = await asyncio.create_subprocess_shell(command, ...)
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return ShellResult(returncode=proc.returncode, stdout=stdout, stderr=stderr)
```

---

## 6. Valos Skill Pelda: Cubix Course Capture

### Skill Manifest

```yaml
name: cubix_course_capture
display_name: "Cubix EDU Course Capture & Transcription"
version: "1.0.0"
skill_type: hybrid                       # RPA + AI + operator
framework_requires: ">=1.0.0"

capabilities:
  - web_navigation
  - video_capture
  - speech_to_text
  - llm_structuring
  - operator_assisted

required_tools:
  - {name: playwright, version: ">=1.40"}
  - {name: ffmpeg, version: ">=6.0"}

required_models:
  - {name: "openai/whisper-1", type: speech_to_text}
  - {name: "openai/gpt-4.1-mini", type: llm, usage: "Transcript structuring"}

workflows:
  - course-capture
  - transcript-processing

estimated_cost_per_run: 3.00             # ~$2.71 STT + $0.30 structuring

tags: [education, video, transcription, hungarian, rpa]
```

### Konyvtar

```
skills/cubix_course_capture/
    skill.yaml
    __init__.py
    workflows/
        course_capture.py         # Teljes kurzus gyujtes (web + operator)
        transcript_processing.py  # Audio -> STT -> structured output
    agents/
        web_navigator.py          # Playwright: URL feloldas, login, scan
        page_saver.py             # Playwright: HTML mentes
        material_downloader.py    # Playwright: PDF/pptx letoltes
        video_opener.py           # Playwright: video megnyitas
        audio_extractor.py        # ffmpeg: video -> m4a
        chunker.py                # ffmpeg: audio split
        transcriber.py            # OpenAI STT: whisper-1
        merger.py                 # Transcript merge + dedup
        structurer.py             # GPT: strukturalt output
    models/
        course.py                 # CourseStructure, Week, Lesson
        transcript.py             # TranscriptSegment, StructuredTranscript
    config/
        selectors.yaml            # CSS selectors a Cubix EDU oldalhoz
    prompts/
        structurer.yaml           # LLM prompt a transzkript strukturalashoz
    tests/
        test_workflow.py
        test_transcriber.py
        datasets/
            sample_course.json    # Teszt kurzus struktura
            sample_audio.m4a      # Rovid teszt audio
```

---

## 7. Tobb Tucat RPA Automatizacio Menedzselse

### 7.1 Skill Catalog Bovites

```
aiflow skill list --type rpa
# cubix_course_capture    v1.0.0  hybrid   Cubix EDU kurzus gyujtes
# invoice_scraper         v1.2.0  rpa      Szamla letoltes portal
# hr_report_generator     v1.0.0  rpa      HR riportok automatikus generalasa
# contract_monitor        v1.1.0  hybrid   Szerzodesi hataridok figyelese
# email_attachment_proc   v2.0.0  rpa      Email mellekletek feldolgozasa
```

### 7.2 Operator Dashboard RPA bovites

Az UI Operator Dashboard-on uj RPA szekció:
- **Aktiv RPA job-ok:** Melyik automatizacio fut, hanyadik lepesnel tart
- **Operator varakozo lista:** Mely job-ok varnak emberi beavatkozasra
- **Playwright screenshot:** Utolso screenshot az aktualis oldalrol (debug)
- **Schedule:** Melyik RPA mikor fut (cron, event trigger)

---

## 8. Implementacios Bovites

| Meglevo Fazis | RPA Bovites |
|---------------|-------------|
| Phase 2 (Engine) | `parallel_map()` es `for_each()` WorkflowBuilder metodus |
| Phase 3 (Agents) | operator_step human_loop minta |
| Phase 5 (API) | `contrib/playwright/`, `contrib/shell/` |
| Phase 7 (Production) | RPA skill template-ek, Cubix skill portalas |

## 9. Uj Fuggosegek

```toml
[project.optional-dependencies]
rpa = [
    "playwright>=1.40",
    "robotframework>=7.0",         # Opcionalis (ha Robot Framework kell)
    "rpaframework>=28.0",          # Opcionalis
]
shell = [
    # ffmpeg, ffprobe: system dependency (Docker image-ben)
]
stt = [
    "openai>=1.30",                # Mar benne van
]
```

```dockerfile
# Dockerfile.rpa - RPA worker-ekhez
FROM mcr.microsoft.com/playwright/python:v1.40.0
RUN apt-get update && apt-get install -y ffmpeg
COPY . /app
RUN pip install -e ".[rpa,stt]"
RUN playwright install chromium
```
