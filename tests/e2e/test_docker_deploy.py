"""
Docker production stack deployment E2E tests.

These tests validate the full Docker production deployment:
- nginx serves the SPA
- API health accessible via nginx proxy
- UI health endpoint
- Login + dashboard flow in Docker environment

@test_registry:
    suite: e2e-docker
    component: docker-deploy
    covers: [docker-compose.prod.yml, aiflow-admin/Dockerfile, aiflow-admin/nginx.conf]
    phase: B9
    priority: critical
    estimated_duration_ms: 30000
    requires_services: [docker]
    tags: [e2e, docker, deploy]
"""

from __future__ import annotations

import subprocess

import httpx
import pytest
from playwright.sync_api import Page

# Production stack runs on port 80 (or UI_PORT env var)
DOCKER_BASE_URL = "http://localhost"


def _docker_stack_running() -> bool:
    """Check if the Docker production stack is running."""
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", "docker-compose.prod.yml", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and "aiflow" in result.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


docker_required = pytest.mark.skipif(
    not _docker_stack_running(),
    reason="Docker production stack not running (start with: make deploy)",
)


@docker_required
class TestDockerDeploy:
    """Tests that run against the Docker production stack."""

    def test_ui_health_endpoint(self) -> None:
        """nginx /health-ui returns 200 ok."""
        resp = httpx.get(f"{DOCKER_BASE_URL}/health-ui", timeout=5)
        assert resp.status_code == 200
        assert resp.text.strip() == "ok"

    def test_ui_serves_index(self) -> None:
        """nginx serves SPA index.html at root."""
        resp = httpx.get(DOCKER_BASE_URL, timeout=5, follow_redirects=True)
        assert resp.status_code == 200
        assert "AIFlow" in resp.text or "<!DOCTYPE html>" in resp.text

    def test_api_health_through_proxy(self) -> None:
        """API health accessible via nginx /health proxy."""
        resp = httpx.get(f"{DOCKER_BASE_URL}/health", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_api_health_live_through_proxy(self) -> None:
        """API /health/live accessible via nginx proxy."""
        resp = httpx.get(f"{DOCKER_BASE_URL}/health/live", timeout=10)
        assert resp.status_code == 200

    def test_spa_fallback_routes(self) -> None:
        """nginx returns index.html for SPA routes (not 404)."""
        for path in ["/emails", "/documents", "/runs", "/rag"]:
            resp = httpx.get(f"{DOCKER_BASE_URL}{path}", timeout=5, follow_redirects=True)
            assert resp.status_code == 200, f"SPA fallback failed for {path}"

    def test_login_and_dashboard(self, page: Page) -> None:
        """Full login flow in Docker environment."""
        page.goto(f"{DOCKER_BASE_URL}/#/login")
        page.wait_for_load_state("networkidle")

        # Login form should be visible
        email_input = page.locator("input#email")
        email_input.wait_for(state="visible", timeout=10000)

        # Fill credentials and submit
        email_input.fill("admin@bestix.hu")
        page.fill("input#password", "admin")
        page.click('button[type="submit"]')

        # Dashboard should load (sidebar visible)
        page.locator("nav").wait_for(state="visible", timeout=15000)
        assert "Dashboard" in page.content() or "AIFlow" in page.content()

    def test_scan_mailbox_button_visible(self, page: Page) -> None:
        """Scan Mailbox button visible on Emails page."""
        # Login first
        page.goto(f"{DOCKER_BASE_URL}/#/login")
        page.wait_for_load_state("networkidle")
        email_input = page.locator("input#email")
        email_input.wait_for(state="visible", timeout=10000)
        email_input.fill("admin@bestix.hu")
        page.fill("input#password", "admin")
        page.click('button[type="submit"]')
        page.locator("nav").wait_for(state="visible", timeout=15000)

        # Navigate to emails
        page.goto(f"{DOCKER_BASE_URL}/#/emails")
        page.wait_for_load_state("networkidle")

        # Scan Mailbox button should exist
        scan_btn = page.get_by_text("Scan Mailbox").or_(page.get_by_text("Levelada szkenneles"))
        scan_btn.wait_for(state="visible", timeout=10000)
