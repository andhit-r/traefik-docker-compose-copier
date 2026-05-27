# traefik-copier — Copilot Instructions

## What this repo is

A **Copier template** that generates a production-ready Traefik v3 Docker Compose
stack. The repo has two distinct layers:

| Layer | Path | Purpose |
|---|---|---|
| Template source | `template/` | Jinja2 files rendered into the user's project |
| Template meta | root (`copier.yml`, `tests/`, `.github/`) | Template config, tests, CI — never copied to destination |

## Architecture

```
copier.yml                  # All questions, types, defaults, when-conditions
template/
  docker-compose.yml.jinja  # Conditionals: auth type, beszel agent, network prefix
  traefik.yml.jinja         # Static config: log level, ACME email, network prefix
  config.yml.jinja          # Dynamic config: middlewares (no user variables)
  Makefile                  # Static – copied verbatim
  .gitignore                # Static – copied verbatim
  certs/.gitkeep            # Placeholder for local TLS certs
tests/
  conftest.py               # Fixtures: template_root, base_answers
  test_template.py          # 38 pytest tests across 6 classes
  scenarios/*.yml           # Documented answer sets for manual copier runs
.github/workflows/test.yml  # CI: lint → pytest (3.11+3.12) → validate-output
```

## Copier conventions

- **`_subdirectory: template`** – only files inside `template/` are rendered into the destination.
- Files with **`.jinja` extension** are processed as Jinja2; the suffix is stripped in output.
- Static files (no `.jinja`) are copied as-is.
- **`when:`** on a question controls whether it is asked; the variable always exists in templates with its default value. Guard template sections with `{% if %}`.
- **`$$`** in YAML string values means a literal `$` — required for htpasswd hashes in Docker Compose labels.

## Template variable reference

| Variable | Type | Default | Notes |
|---|---|---|---|
| `project_name` | str | `traefik` | Container name prefix |
| `network_prefix` | str | `inverseproxy` | Prefix for all three Docker network names |
| `traefik_version` | str | `v3` | Image tag on Docker Hub |
| `traefik_domain` | str | `traefik.example.com` | Dashboard FQDN |
| `acme_email` | str | `admin@example.com` | Let's Encrypt email |
| `log_level` | str | `INFO` | DEBUG/INFO/WARNING/ERROR |
| `trusted_ips` | str | `127.0.0.1/32,…` | CSV of CIDRs for the IP-allowlist middleware |
| `dashboard_auth` | str | `basic` | `none` / `basic` / `authentik` |
| `basic_auth_users` | str | placeholder | htpasswd, `$$`-escaped; only when `dashboard_auth == 'basic'` |
| `authentik_outpost_url` | str | placeholder | Only when `dashboard_auth == 'authentik'` |
| `enable_beszel_agent` | bool | `false` | Adds beszel-agent service + volume |
| `beszel_listen_port` | int | `45876` | Only when `enable_beszel_agent` |
| `beszel_key` | str | placeholder | Only when `enable_beszel_agent` |
| `beszel_token` | str | placeholder | Only when `enable_beszel_agent` |
| `beszel_hub_url` | str | placeholder | Only when `enable_beszel_agent` |

## Three-network rule

Every generated project always has exactly these three networks — names are `{{ network_prefix }}_<suffix>`:

| Key | Suffix | `internal` | Encrypted | Used by |
|---|---|---|---|---|
| `shared` | `_shared` | true | yes | Traefik ↔ backend services |
| `private` | `_private` | true | yes | Traefik ↔ docker-socket-proxy |
| `public` | `_public` | false | no | Traefik ↔ internet |

Do not add or remove networks without updating the test `TestNetworks::test_exactly_three_networks`.

## Dashboard auth patterns

Three mutually exclusive patterns in `docker-compose.yml.jinja`:

- **`none`** – no auth labels; router has no `middlewares=` label.
- **`basic`** – adds `basicauth.users` middleware label + `routers.api.middlewares=dashboard-auth`.
- **`authentik`** – adds `forwardauth.address`, `trustForwardHeader`, `authResponseHeaders` labels + `routers.api.middlewares=authentik`.

## Traefik v3 requirements

- Use `ipAllowList` (not the v2 `ipWhiteList`).
- No `privileged: true` on the `proxy` service — only `dockersocket` may need elevated access.
- Docker socket access is always through `dockersocket` (`tecnativa/docker-socket-proxy`); never mount `/var/run/docker.sock` directly into Traefik.

## Build & test

```bash
pip install -r requirements-dev.txt

# Run all tests
python3 -m pytest tests/ -v

# Manually generate a scenario
copier copy . /tmp/out --defaults --trust --data-file tests/scenarios/with_beszel.yml
```

## Adding a new template variable

1. Add question entry in `copier.yml` (with `type`, `help`, `default`, and `when` if conditional).
2. Use `{% if variable %}` guards in the relevant `.jinja` files.
3. Add assertions to `tests/test_template.py` — at minimum one positive and one negative test.
4. Add or update the relevant `tests/scenarios/*.yml` file.
5. Update the variable reference table in this file.

## Changing the network layout

Do not change the three-network structure without:
1. Updating all three `.jinja` files.
2. Updating `TestNetworks` in `test_template.py`.
3. Updating the three-network rule table above.

## Branch conventions

- Selalu gunakan branch **`master`** sebagai branch utama.
- Jangan membuat branch baru kecuali diminta secara eksplisit.

## Commit conventions

- **Bahasa**: selalu gunakan Bahasa Indonesia untuk pesan commit.
- **Format**: `<tipe>: <ringkasan singkat>` diikuti body jika perlu.
- **Tipe yang digunakan**:
  | Tipe | Kapan dipakai |
  |---|---|
  | `feat` | Menambah fitur atau variabel template baru |
  | `fix` | Memperbaiki bug pada template atau test |
  | `test` | Menambah atau memperbaiki test |
  | `refactor` | Perubahan struktur tanpa mengubah perilaku |
  | `docs` | Perubahan README, copilot-instructions, komentar |
  | `ci` | Perubahan workflow GitHub Actions |
  | `chore` | Pembaruan dependensi, konfigurasi alat bantu |
- **Body** (opsional): jelaskan *apa yang berubah* dan *mengapa*, bukan *bagaimana*. Sertakan nama file atau variabel yang terdampak agar mudah ditelusuri dari log.

Contoh commit yang baik:
```
feat: tambah opsi autentikasi basic auth pada dashboard Traefik

Menambah variabel basic_auth_users di copier.yml dengan kondisi
when: dashboard_auth == 'basic'. Template docker-compose.yml.jinja
diperbarui untuk menyertakan label basicauth.users dan middleware
routers.api.middlewares=dashboard-auth.
```
