"""Shared pytest fixtures for the traefik-copier template tests."""

from pathlib import Path

import pytest


TEMPLATE_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="session")
def template_root() -> Path:
    """Return the absolute path to the Copier template root directory."""
    return TEMPLATE_ROOT


@pytest.fixture()
def base_answers() -> dict:
    """Minimal valid answers that produce a working template output."""
    return {
        "project_name": "test-traefik",
        "network_prefix": "testnet",
        "traefik_version": "v3",
        "traefik_domain": "traefik.test.example.com",
        "acme_email": "test@example.com",
        "log_level": "INFO",
        "trusted_ips": "127.0.0.1/32,10.0.0.0/8",
        "dashboard_auth": "none",
        "enable_beszel_agent": False,
    }
