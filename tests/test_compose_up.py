"""Integration tests: generate the template and start the Docker Compose stack.

These tests require a running Docker daemon. They are skipped automatically
when Docker is unavailable. Run selectively:

    pytest tests/test_compose_up.py -v
    pytest tests/ -v -m "not docker"   # skip these in fast runs
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
from copier import run_copy

TEMPLATE_ROOT = Path(__file__).parent.parent

pytestmark = pytest.mark.docker


# ── helpers ────────────────────────────────────────────────────────────────


def docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


skip_no_docker = pytest.mark.skipif(
    not docker_available(),
    reason="Docker daemon not available",
)


def generate(tmp_path: Path, answers: dict[str, Any]) -> Path:
    """Run the Copier template into *tmp_path* with the given answers."""
    run_copy(
        src_path=str(TEMPLATE_ROOT),
        dst_path=str(tmp_path),
        data=answers,
        defaults=True,
        overwrite=True,
        unsafe=True,
        quiet=True,
    )
    return tmp_path


def compose_up(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )


def compose_down(cwd: Path) -> None:
    subprocess.run(
        ["docker", "compose", "down", "--volumes", "--remove-orphans"],
        cwd=cwd,
        capture_output=True,
        timeout=60,
    )


def get_running_service_names(cwd: Path) -> list[str]:
    """Return service names that are currently in 'running' state."""
    result = subprocess.run(
        ["docker", "compose", "ps", "--services", "--filter", "status=running"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]


def get_service_logs(cwd: Path, service: str) -> str:
    result = subprocess.run(
        ["docker", "compose", "logs", "--no-log-prefix", service],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout + result.stderr


# ── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture()
def unique_prefix(tmp_path: Path) -> str:
    """Unique network_prefix per test to prevent Docker network name collisions."""
    return f"citest{tmp_path.name[-8:]}"


# ── TestComposeUp ──────────────────────────────────────────────────────────


class TestComposeUp:
    """Generate the stack and verify that all core containers come up healthy."""

    @pytest.fixture(autouse=True)
    def _teardown(self, tmp_path: Path):
        yield
        compose_down(tmp_path)

    @skip_no_docker
    def test_no_auth_core_services_running(self, tmp_path, unique_prefix):
        """docker compose up succeeds and both core services are running (no auth)."""
        answers = {
            "project_name": "ci-traefik",
            "network_prefix": unique_prefix,
            "traefik_version": "v3",
            "traefik_domain": "traefik.localhost",
            "acme_email": "ci@example.com",
            "log_level": "DEBUG",
            "trusted_ips": "127.0.0.1/32,10.0.0.0/8",
            "dashboard_auth": "none",
            "enable_beszel_agent": False,
        }
        out = generate(tmp_path, answers)

        result = compose_up(out)
        assert result.returncode == 0, (
            f"docker compose up failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

        time.sleep(10)

        running = get_running_service_names(out)
        assert "proxy" in running, (
            f"proxy not running. Running services: {running}\n"
            f"Proxy logs:\n{get_service_logs(out, 'proxy')}"
        )
        assert "dockersocket" in running, (
            f"dockersocket not running. Running services: {running}"
        )

    @skip_no_docker
    def test_basic_auth_core_services_running(self, tmp_path, unique_prefix):
        """docker compose up succeeds with basic auth; both core services are running."""
        answers = {
            "project_name": "ci-traefik",
            "network_prefix": unique_prefix,
            "traefik_version": "v3",
            "traefik_domain": "traefik.localhost",
            "acme_email": "ci@example.com",
            "log_level": "DEBUG",
            "trusted_ips": "127.0.0.1/32,10.0.0.0/8",
            "dashboard_auth": "basic",
            "basic_auth_users": "admin:$$2y$$05$$CITestHashPlaceholder0000000000000000000000",
            "enable_beszel_agent": False,
        }
        out = generate(tmp_path, answers)

        result = compose_up(out)
        assert result.returncode == 0, (
            f"docker compose up failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

        time.sleep(10)

        running = get_running_service_names(out)
        assert "proxy" in running, (
            f"proxy not running. Running services: {running}\n"
            f"Proxy logs:\n{get_service_logs(out, 'proxy')}"
        )
        assert "dockersocket" in running, (
            f"dockersocket not running. Running services: {running}"
        )

    @skip_no_docker
    def test_authentik_core_services_running(self, tmp_path, unique_prefix):
        """docker compose up succeeds with authentik auth; Traefik starts even without a live outpost."""
        answers = {
            "project_name": "ci-traefik",
            "network_prefix": unique_prefix,
            "traefik_version": "v3",
            "traefik_domain": "traefik.localhost",
            "acme_email": "ci@example.com",
            "log_level": "DEBUG",
            "trusted_ips": "127.0.0.1/32,10.0.0.0/8",
            "dashboard_auth": "authentik",
            "authentik_outpost_url": "http://authentik-proxy:9000/outpost.goauthentik.io/auth/traefik",
            "enable_beszel_agent": False,
        }
        out = generate(tmp_path, answers)

        result = compose_up(out)
        assert result.returncode == 0, (
            f"docker compose up failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

        time.sleep(10)

        running = get_running_service_names(out)
        # Traefik configures ForwardAuth via labels only — it starts without a live outpost.
        assert "proxy" in running, (
            f"proxy not running. Running services: {running}\n"
            f"Proxy logs:\n{get_service_logs(out, 'proxy')}"
        )
        assert "dockersocket" in running, (
            f"dockersocket not running. Running services: {running}"
        )

    @skip_no_docker
    def test_no_containers_exit_unexpectedly(self, tmp_path, unique_prefix):
        """Verify that no container exits with a non-zero code after startup."""
        answers = {
            "project_name": "ci-traefik",
            "network_prefix": unique_prefix,
            "traefik_version": "v3",
            "traefik_domain": "traefik.localhost",
            "acme_email": "ci@example.com",
            "log_level": "DEBUG",
            "trusted_ips": "127.0.0.1/32,10.0.0.0/8",
            "dashboard_auth": "none",
            "enable_beszel_agent": False,
        }
        out = generate(tmp_path, answers)
        compose_up(out)

        time.sleep(10)

        # Any exited service is a failure
        exited = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=exited"],
            cwd=out,
            capture_output=True,
            text=True,
            timeout=30,
        )
        exited_services = [
            s for s in exited.stdout.strip().splitlines() if s.strip()
        ]
        assert not exited_services, (
            f"Services exited unexpectedly: {exited_services}\n"
            + "\n".join(
                f"--- {s} logs ---\n{get_service_logs(out, s)}"
                for s in exited_services
            )
        )
