"""Tests for the traefik-copier Copier template.

Each test class covers a specific dimension of the template:
  - TestFileGeneration  : required files are created
  - TestNetworks        : three networks with correct properties
  - TestDashboardAuth   : none / basic / authentik auth variants
  - TestBeszelAgent     : optional beszel-agent inclusion
  - TestTraefikYml      : static Traefik configuration file
  - TestConfigYml       : dynamic Traefik configuration file
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from copier import run_copy

TEMPLATE_ROOT = Path(__file__).parent.parent


# ── helpers ────────────────────────────────────────────────────────────────


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


def load_yaml(path: Path) -> Any:
    with path.open() as fh:
        return yaml.safe_load(fh)


def read_text(path: Path) -> str:
    return path.read_text()


# ── TestFileGeneration ─────────────────────────────────────────────────────


class TestFileGeneration:
    def test_required_files_exist(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        for name in ("docker-compose.yml", "traefik.yml", "config.yml", "Makefile"):
            assert (out / name).exists(), f"Expected file not found: {name}"

    def test_certs_directory_exists(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        assert (out / "certs").is_dir()

    def test_gitignore_exists(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        assert (out / ".gitignore").exists()

    def test_copier_answers_file_exists(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        assert (out / ".copier-answers.yml").exists()

    def test_copier_answers_contains_expected_keys(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        data = load_yaml(out / ".copier-answers.yml")
        for key in ("project_name", "network_prefix", "traefik_domain", "dashboard_auth"):
            assert key in data, f"Expected key not found in .copier-answers.yml: {key}"

    def test_docker_compose_is_valid_yaml(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        data = load_yaml(out / "docker-compose.yml")
        assert isinstance(data, dict)

    def test_traefik_yml_is_valid_yaml(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        data = load_yaml(out / "traefik.yml")
        assert isinstance(data, dict)

    def test_config_yml_is_valid_yaml(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        data = load_yaml(out / "config.yml")
        assert isinstance(data, dict)


# ── TestNetworks ───────────────────────────────────────────────────────────


class TestNetworks:
    def test_exactly_three_networks(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        data = load_yaml(out / "docker-compose.yml")
        assert len(data["networks"]) == 3

    def test_network_keys_present(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        networks = load_yaml(out / "docker-compose.yml")["networks"]
        assert set(networks.keys()) == {"shared", "private", "public"}

    def test_shared_network_name_uses_prefix(self, tmp_path, base_answers):
        answers = {**base_answers, "network_prefix": "myproxy"}
        out = generate(tmp_path, answers)
        networks = load_yaml(out / "docker-compose.yml")["networks"]
        assert networks["shared"]["name"] == "myproxy_shared"

    def test_private_network_name_uses_prefix(self, tmp_path, base_answers):
        answers = {**base_answers, "network_prefix": "myproxy"}
        out = generate(tmp_path, answers)
        networks = load_yaml(out / "docker-compose.yml")["networks"]
        assert networks["private"]["name"] == "myproxy_private"

    def test_public_network_name_uses_prefix(self, tmp_path, base_answers):
        answers = {**base_answers, "network_prefix": "myproxy"}
        out = generate(tmp_path, answers)
        networks = load_yaml(out / "docker-compose.yml")["networks"]
        assert networks["public"]["name"] == "myproxy_public"

    def test_shared_network_is_internal(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        networks = load_yaml(out / "docker-compose.yml")["networks"]
        assert networks["shared"].get("internal") is True

    def test_private_network_is_internal(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        networks = load_yaml(out / "docker-compose.yml")["networks"]
        assert networks["private"].get("internal") is True

    def test_public_network_is_not_internal(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        networks = load_yaml(out / "docker-compose.yml")["networks"]
        assert networks["public"].get("internal", False) is False

    def test_default_prefix_is_inverseproxy(self, tmp_path):
        # Omit network_prefix to fall back to the copier default
        answers = {
            "project_name": "test-traefik",
            "traefik_domain": "traefik.test.example.com",
            "acme_email": "test@example.com",
            "dashboard_auth": "none",
            "enable_beszel_agent": False,
        }
        out = generate(tmp_path, answers)
        networks = load_yaml(out / "docker-compose.yml")["networks"]
        assert networks["shared"]["name"] == "inverseproxy_shared"


# ── TestDashboardAuth ──────────────────────────────────────────────────────


class TestDashboardAuth:
    def test_no_auth_omits_middleware_labels(self, tmp_path, base_answers):
        answers = {**base_answers, "dashboard_auth": "none"}
        out = generate(tmp_path, answers)
        text = read_text(out / "docker-compose.yml")
        assert "basicauth" not in text
        assert "forwardauth" not in text

    def test_no_auth_router_has_no_middleware(self, tmp_path, base_answers):
        answers = {**base_answers, "dashboard_auth": "none"}
        out = generate(tmp_path, answers)
        text = read_text(out / "docker-compose.yml")
        assert "routers.api.middlewares" not in text

    def test_basic_auth_label_present(self, tmp_path, base_answers):
        answers = {
            **base_answers,
            "dashboard_auth": "basic",
            "basic_auth_users": "admin:$$2y$$05$$TestHash000000000000000000000000000000000000",
        }
        out = generate(tmp_path, answers)
        text = read_text(out / "docker-compose.yml")
        assert "basicauth.users" in text

    def test_basic_auth_router_middleware_set(self, tmp_path, base_answers):
        answers = {
            **base_answers,
            "dashboard_auth": "basic",
            "basic_auth_users": "admin:$$2y$$05$$TestHash000000000000000000000000000000000000",
        }
        out = generate(tmp_path, answers)
        text = read_text(out / "docker-compose.yml")
        assert "routers.api.middlewares=dashboard-auth" in text

    def test_authentik_forwardauth_label_present(self, tmp_path, base_answers):
        answers = {
            **base_answers,
            "dashboard_auth": "authentik",
            "authentik_outpost_url": "https://auth.example.com/outpost.goauthentik.io/auth/traefik",
        }
        out = generate(tmp_path, answers)
        text = read_text(out / "docker-compose.yml")
        assert "forwardauth.address" in text
        assert "auth.example.com" in text

    def test_authentik_router_middleware_set(self, tmp_path, base_answers):
        answers = {
            **base_answers,
            "dashboard_auth": "authentik",
            "authentik_outpost_url": "https://auth.example.com/outpost.goauthentik.io/auth/traefik",
        }
        out = generate(tmp_path, answers)
        text = read_text(out / "docker-compose.yml")
        assert "routers.api.middlewares=authentik" in text

    def test_authentik_no_basicauth_labels(self, tmp_path, base_answers):
        answers = {
            **base_answers,
            "dashboard_auth": "authentik",
            "authentik_outpost_url": "https://auth.example.com/outpost.goauthentik.io/auth/traefik",
        }
        out = generate(tmp_path, answers)
        text = read_text(out / "docker-compose.yml")
        assert "basicauth" not in text


# ── TestBeszelAgent ────────────────────────────────────────────────────────


class TestBeszelAgent:
    def test_disabled_by_default(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        data = load_yaml(out / "docker-compose.yml")
        assert "beszel-agent" not in data["services"]

    def test_disabled_omits_beszel_volume(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        data = load_yaml(out / "docker-compose.yml")
        assert "beszel_agent_data" not in (data.get("volumes") or {})

    def test_enabled_adds_service(self, tmp_path, base_answers):
        answers = {
            **base_answers,
            "enable_beszel_agent": True,
            "beszel_listen_port": 45876,
            "beszel_key": "ssh-ed25519 AAAATESTKEY",
            "beszel_token": "test-token-abc",
            "beszel_hub_url": "https://beszel.example.com",
        }
        out = generate(tmp_path, answers)
        data = load_yaml(out / "docker-compose.yml")
        assert "beszel-agent" in data["services"]

    def test_enabled_adds_volume(self, tmp_path, base_answers):
        answers = {
            **base_answers,
            "enable_beszel_agent": True,
            "beszel_listen_port": 45876,
            "beszel_key": "ssh-ed25519 AAAATESTKEY",
            "beszel_token": "test-token-abc",
            "beszel_hub_url": "https://beszel.example.com",
        }
        out = generate(tmp_path, answers)
        data = load_yaml(out / "docker-compose.yml")
        assert "beszel_agent_data" in (data.get("volumes") or {})

    def test_enabled_sets_listen_port(self, tmp_path, base_answers):
        answers = {
            **base_answers,
            "enable_beszel_agent": True,
            "beszel_listen_port": 12345,
            "beszel_key": "ssh-ed25519 AAAATESTKEY",
            "beszel_token": "tok",
            "beszel_hub_url": "https://beszel.example.com",
        }
        out = generate(tmp_path, answers)
        data = load_yaml(out / "docker-compose.yml")
        env = data["services"]["beszel-agent"]["environment"]
        assert env["LISTEN"] == 12345

    def test_enabled_sets_hub_url(self, tmp_path, base_answers):
        answers = {
            **base_answers,
            "enable_beszel_agent": True,
            "beszel_listen_port": 45876,
            "beszel_key": "ssh-ed25519 AAAATESTKEY",
            "beszel_token": "tok",
            "beszel_hub_url": "https://my-beszel.example.com",
        }
        out = generate(tmp_path, answers)
        data = load_yaml(out / "docker-compose.yml")
        env = data["services"]["beszel-agent"]["environment"]
        assert env["HUB_URL"] == "https://my-beszel.example.com"


# ── TestTraefikYml ─────────────────────────────────────────────────────────


class TestTraefikYml:
    def test_entrypoints_defined(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        data = load_yaml(out / "traefik.yml")
        assert "http" in data["entryPoints"]
        assert "https" in data["entryPoints"]

    def test_certificate_resolver_defined(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        data = load_yaml(out / "traefik.yml")
        assert "letsencrypt" in data["certificatesResolvers"]

    def test_acme_email_applied(self, tmp_path, base_answers):
        answers = {**base_answers, "acme_email": "devops@mycompany.io"}
        out = generate(tmp_path, answers)
        data = load_yaml(out / "traefik.yml")
        assert data["certificatesResolvers"]["letsencrypt"]["acme"]["email"] == "devops@mycompany.io"

    def test_log_level_applied(self, tmp_path, base_answers):
        answers = {**base_answers, "log_level": "DEBUG"}
        out = generate(tmp_path, answers)
        data = load_yaml(out / "traefik.yml")
        assert data["log"]["level"] == "DEBUG"

    def test_docker_provider_uses_socket_proxy(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        data = load_yaml(out / "traefik.yml")
        assert data["providers"]["docker"]["endpoint"] == "http://dockersocket:2375"

    def test_docker_provider_network_uses_prefix(self, tmp_path, base_answers):
        answers = {**base_answers, "network_prefix": "pfx"}
        out = generate(tmp_path, answers)
        data = load_yaml(out / "traefik.yml")
        assert data["providers"]["docker"]["network"] == "pfx_shared"

    def test_traefik_version_applied(self, tmp_path, base_answers):
        answers = {**base_answers, "traefik_version": "v3.3"}
        out = generate(tmp_path, answers)
        data = load_yaml(out / "docker-compose.yml")
        assert data["services"]["proxy"]["image"] == "traefik:v3.3"


# ── TestConfigYml ──────────────────────────────────────────────────────────


class TestConfigYml:
    def test_http_section_present(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        data = load_yaml(out / "config.yml")
        assert "http" in data

    def test_standard_middlewares_present(self, tmp_path, base_answers):
        out = generate(tmp_path, base_answers)
        middlewares = load_yaml(out / "config.yml")["http"]["middlewares"]
        for name in ("buffering", "compress", "secure-headers", "nocrawlers", "doodba", "localhost-only"):
            assert name in middlewares, f"Middleware not found: {name}"

    def test_ipallowlist_used_not_ipwhitelist(self, tmp_path, base_answers):
        """Ensure Traefik v3 ipAllowList is used instead of deprecated ipWhiteList."""
        out = generate(tmp_path, base_answers)
        text = read_text(out / "config.yml")
        assert "ipAllowList" in text
        assert "ipWhiteList" not in text
