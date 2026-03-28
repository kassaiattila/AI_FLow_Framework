"""Kroki diagram rendering - Mermaid/BPMN code to SVG/PNG/PDF.

Encodes diagram source via zlib + base64url, sends an HTTP GET to a
Kroki instance, and returns the raw rendered bytes.  The renderer is
intentionally stateless apart from the httpx client so it can be
injected via DI into any step or agent.
"""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

import httpx
import structlog

__all__ = ["KrokiRenderer"]

logger = structlog.get_logger(__name__)


class KrokiRenderer:
    """Render diagram code (Mermaid, BPMN, PlantUML, ...) to images via Kroki.

    Kroki is expected to run as a Docker service (see docker-compose.yml).
    Default URL is ``http://localhost:8000`` which matches the standard
    Kroki container port.
    """

    def __init__(
        self,
        kroki_url: str = "http://localhost:8000",
        *,
        timeout: float = 30.0,
    ) -> None:
        self.kroki_url = kroki_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def render(
        self,
        diagram_code: str,
        output_format: str = "svg",
        diagram_type: str = "mermaid",
    ) -> bytes:
        """Render diagram source to image bytes via Kroki HTTP GET.

        Args:
            diagram_code: Raw diagram source (Mermaid, BPMN XML, etc.).
            output_format: Target format - ``svg``, ``png``, or ``pdf``.
            diagram_type: Kroki diagram type identifier, e.g.
                ``mermaid``, ``bpmn``, ``plantuml``.

        Returns:
            Raw image bytes in the requested format.

        Raises:
            httpx.HTTPStatusError: If Kroki returns a non-2xx response.
            httpx.ConnectError: If the Kroki service is unreachable.
        """
        encoded = self._encode_kroki(diagram_code)
        url = f"{self.kroki_url}/{diagram_type}/{output_format}/{encoded}"

        logger.info(
            "kroki_render_start",
            diagram_type=diagram_type,
            output_format=output_format,
            code_length=len(diagram_code),
        )

        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.ConnectError:
            logger.error(
                "kroki_unavailable",
                url=self.kroki_url,
                hint="Is the Kroki Docker container running?",
            )
            raise
        except httpx.HTTPStatusError as exc:
            logger.error(
                "kroki_render_failed",
                status=exc.response.status_code,
                body=exc.response.text[:500],
            )
            raise

        logger.info(
            "kroki_render_ok",
            output_format=output_format,
            bytes_returned=len(response.content),
        )
        return response.content

    async def render_to_file(
        self,
        diagram_code: str,
        output_path: Path,
        output_format: str = "svg",
        diagram_type: str = "mermaid",
    ) -> Path:
        """Render diagram and persist result to *output_path*.

        Parent directories are created automatically.

        Args:
            diagram_code: Raw diagram source.
            output_path: Destination file (e.g. ``outputs/flow.svg``).
            output_format: Target format passed to Kroki.
            diagram_type: Kroki diagram type identifier.

        Returns:
            The resolved *output_path* after writing.
        """
        image_bytes = await self.render(
            diagram_code,
            output_format=output_format,
            diagram_type=diagram_type,
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)

        logger.info("kroki_file_saved", path=str(output_path))
        return output_path

    async def is_available(self) -> bool:
        """Return ``True`` if the Kroki service is reachable.

        Performs a lightweight GET against the root endpoint.  Any
        non-exception 2xx/3xx response counts as "available".
        """
        try:
            response = await self._client.get(self.kroki_url)
            available = response.is_success
        except httpx.HTTPError:
            available = False

        logger.debug("kroki_health_check", available=available, url=self.kroki_url)
        return available

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> KrokiRenderer:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_kroki(diagram_code: str) -> str:
        """Compress + base64url-encode diagram source for Kroki URL path."""
        compressed = zlib.compress(diagram_code.encode("utf-8"), 9)
        return base64.urlsafe_b64encode(compressed).decode("ascii")
