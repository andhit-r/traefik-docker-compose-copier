# traefik-copier

A [Copier](https://copier.readthedocs.io) template for deploying Traefik as a
Docker Compose reverse proxy, with optional dashboard authentication and Beszel
monitoring.

## Features

- **Traefik v3** (configurable tag)
- **Three Docker networks** with a configurable prefix
  - `<prefix>_shared` – internal, encrypted; attach other services here
  - `<prefix>_private` – internal, encrypted; socket proxy only
  - `<prefix>_public` – external-facing
- **Secure Docker socket access** via `tecnativa/docker-socket-proxy`
- **Dashboard authentication** – choose one:
  - `none` – no auth (development only)
  - `basic` – HTTP Basic Auth (htpasswd)
  - `authentik` – ForwardAuth via an [Authentik](https://goauthentik.io) outpost
- **Beszel monitoring agent** – optional inclusion
- **Let's Encrypt** TLS via ACME `tlsChallenge`

---

## Requirements

| Tool | Minimum version |
|------|----------------|
| [Copier](https://copier.readthedocs.io) | 9.3 |
| Python | 3.11 |
| Docker + Compose plugin | 24 |

Install Copier:

```bash
pip install copier
# or
pipx install copier
```

---

## Usage

### Generate a new project

```bash
copier copy gh:your-org/traefik-copier ./my-traefik
```

Or from a local clone:

```bash
copier copy /path/to/traefik-copier ./my-traefik
```

Copier will ask a series of questions. Press **Enter** to accept the default
shown in brackets.

### Questions overview

| Question | Default | Description |
|----------|---------|-------------|
| `project_name` | `traefik` | Container / volume name prefix |
| `network_prefix` | `inverseproxy` | Docker network name prefix |
| `traefik_version` | `v3` | Traefik image tag |
| `traefik_domain` | `traefik.example.com` | Dashboard FQDN |
| `acme_email` | `admin@example.com` | Let's Encrypt notification e-mail |
| `log_level` | `INFO` | Traefik log verbosity |
| `trusted_ips` | `127.0.0.1/32,172.16.0.0/12,10.0.0.0/8` | IP allowlist CIDRs |
| `dashboard_auth` | `basic` | Auth method: `none` / `basic` / `authentik` |
| `basic_auth_users` | *(placeholder)* | htpasswd string (only when `basic`) |
| `authentik_outpost_url` | *(placeholder)* | Authentik outpost URL (only when `authentik`) |
| `enable_beszel_agent` | `false` | Include Beszel monitoring agent |
| `beszel_listen_port` | `45876` | Agent listen port (only when enabled) |
| `beszel_key` | *(placeholder)* | SSH public key from Beszel hub |
| `beszel_token` | *(placeholder)* | Registration token from Beszel hub |
| `beszel_hub_url` | *(placeholder)* | Beszel hub base URL |

### Update an existing project

```bash
# Run inside the previously generated directory
copier update
```

---

## Generated project structure

```
my-traefik/
├── .copier-answers.yml   # Answers file for future copier update
├── .gitignore
├── Makefile              # Helper targets: up, down, logs, validate …
├── certs/                # Local TLS certificate files (git-ignored)
│   └── .gitkeep
├── config.yml            # Traefik dynamic configuration
├── docker-compose.yml    # Main Compose file
└── traefik.yml           # Traefik static configuration
```

### Common commands (in generated directory)

```bash
make up          # Start services
make down        # Stop services
make logs        # Follow all logs
make validate    # Validate compose file syntax
make update      # Pull images + recreate containers
```

---

## Basic Auth: generating credentials

```bash
# Install apache2-utils (Debian/Ubuntu) or httpd-tools (RHEL/Fedora)
sudo apt install apache2-utils

# Generate hash and escape $ for Docker Compose
echo $(htpasswd -nB admin) | sed -e 's/\$/\$\$/g'
```

Paste the output as the value for `basic_auth_users`.

---

## Authentik setup

1. In Authentik, create a **Proxy Provider** in *Forward auth (single application)*
   or *Forward auth (domain level)* mode for the Traefik dashboard application.
2. Assign it to an **Outpost**.
3. Copy the outpost URL from **Applications → Outposts → [outpost] → View Setup** –
   it ends with `/outpost.goauthentik.io/auth/traefik`.
4. Paste that URL as `authentik_outpost_url` when running Copier.

---

## Contributing / development

```bash
git clone https://github.com/your-org/traefik-copier
cd traefik-copier

pip install -r requirements-dev.txt

# Run the full test suite
pytest tests/ -v
```

### Test matrix

Tests cover all three auth modes and both Beszel states across Python 3.11 and
3.12. The GitHub Actions workflow runs on every push to `master` / `main` and on
pull requests targeting those branches.

---

## License

MIT
