"""Azure Document Intelligence client - REST API (no SDK needed)."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

__all__ = ["AzureDocIntelligence"]
logger = structlog.get_logger(__name__)


class AzureDocIntelligence:
    """Async client for Azure AI Document Intelligence REST API."""

    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    async def analyze(
        self, content: bytes, model: str = "prebuilt-layout"
    ) -> dict[str, Any]:
        """Analyze a document using Azure DI."""
        url = (
            f"{self.endpoint}/documentintelligence/documentModels/"
            f"{model}:analyze?api-version=2024-11-30"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/octet-stream",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            # Start analysis
            resp = await client.post(url, headers=headers, content=content)
            if resp.status_code != 202:
                raise RuntimeError(
                    f"Azure DI error {resp.status_code}: {resp.text[:200]}"
                )

            # Poll for result
            result_url = resp.headers.get("Operation-Location", "")
            if not result_url:
                raise RuntimeError("No Operation-Location header")

            for _ in range(60):  # Max 60 attempts (2 min)
                await asyncio.sleep(2)
                poll = await client.get(
                    result_url,
                    headers={"Ocp-Apim-Subscription-Key": self.api_key},
                )
                status = poll.json().get("status", "")
                if status == "succeeded":
                    return self._parse_result(
                        poll.json().get("analyzeResult", {})
                    )
                elif status == "failed":
                    raise RuntimeError(
                        f"Azure DI analysis failed: {poll.json()}"
                    )

            raise RuntimeError("Azure DI analysis timed out")

    def _parse_result(self, result: dict) -> dict[str, Any]:
        """Extract text, tables, and key-value pairs from Azure DI result."""
        text = result.get("content", "")

        tables = []
        for table in result.get("tables", []):
            rows: list[list[str]] = []
            for cell in table.get("cells", []):
                while len(rows) <= cell.get("rowIndex", 0):
                    rows.append([])
                row = rows[cell["rowIndex"]]
                while len(row) <= cell.get("columnIndex", 0):
                    row.append("")
                row[cell["columnIndex"]] = cell.get("content", "")
            # Convert to markdown table
            if rows:
                md = "| " + " | ".join(rows[0]) + " |\n"
                md += "| " + " | ".join(["---"] * len(rows[0])) + " |\n"
                for r in rows[1:]:
                    md += "| " + " | ".join(r) + " |\n"
                tables.append(
                    {
                        "markdown": md,
                        "rows": len(rows),
                        "cols": len(rows[0]) if rows else 0,
                    }
                )

        kvps: dict[str, str] = {}
        for kvp in result.get("keyValuePairs", []):
            key = kvp.get("key", {}).get("content", "")
            value = kvp.get("value", {}).get("content", "")
            if key:
                kvps[key] = value

        return {
            "text": text,
            "markdown": text,
            "tables": tables,
            "key_value_pairs": kvps,
        }

    async def is_available(self) -> bool:
        """Check if the Azure DI endpoint is reachable."""
        if not self.endpoint or not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.endpoint}/documentintelligence/info"
                    f"?api-version=2024-11-30",
                    headers={"Ocp-Apim-Subscription-Key": self.api_key},
                )
                return resp.status_code == 200
        except Exception:
            return False
