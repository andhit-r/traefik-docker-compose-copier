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

### Prerequisites

- Authentik is already running and accessible (e.g., at `https://auth.example.com`).
- Authentik's embedded outpost **or** a dedicated proxy outpost is deployed and reachable by Traefik.
- The Authentik container/outpost must be on the **`<network_prefix>_shared`** Docker network so Traefik can reach it. Add the network to your Authentik Compose file:

  ```yaml
  networks:
    inverseproxy_shared:
      external: true
  ```

  Then attach the outpost service to it:

  ```yaml
  services:
    authentik-proxy:   # your outpost service name
      networks:
        - inverseproxy_shared
  ```

---

### Step 1 — Create an Application

1. Go to **Admin Interface → Applications → Applications → Create**.
2. Fill in:
   - **Name**: e.g., `Traefik Dashboard`
   - **Slug**: e.g., `traefik-dashboard`
   - **Provider**: leave empty for now (we'll create it next).
3. Save.

---

### Step 2 — Create a Proxy Provider

1. Go to **Admin Interface → Applications → Providers → Create**.
2. Choose **Proxy Provider**.
3. Fill in:
   - **Name**: e.g., `traefik-dashboard-provider`
   - **Authorization flow**: choose your preferred flow (e.g., `default-provider-authorization-implicit-consent`)
   - **Mode**: choose one:

     | Mode | When to use |
     |------|-------------|
     | **Forward auth (single application)** | Protect only the Traefik dashboard URL |
     | **Forward auth (domain level)** | Protect all subdomains under a single domain via one outpost |

   - For **single application** mode, set **External Host** to `https://traefik.example.com` (your `traefik_domain`).
   - For **domain level** mode, set **Cookie domain** to `example.com` (your top-level domain).
4. Save, then go back to the Application you created and assign this provider to it.

---

### Step 3 — Assign the Provider to an Outpost

1. Go to **Admin Interface → Applications → Outposts**.
2. Either edit an existing **Proxy** outpost or create a new one:
   - **Type**: Proxy
   - **Integration**: Docker (if managed by Authentik) or External (if you run it manually).
3. Under **Applications**, add the `Traefik Dashboard` application.
4. Save — Authentik will deploy or update the outpost automatically if using Docker integration.

> **Tip:** For a self-hosted outpost running inside Docker Compose, see
> [Authentik outpost documentation](https://docs.goauthentik.io/docs/add-secure-apps/outposts/).

---

### Step 4 — Get the Outpost URL

1. Go to **Admin Interface → Applications → Outposts**.
2. Click **View Setup** on your outpost.
3. Copy the **traefik** URL — it looks like:

   ```
   https://auth.example.com/outpost.goauthentik.io/auth/traefik
   ```

   This is the value you will use for `authentik_outpost_url`.

> **Note:** If the outpost runs as a separate container on the shared network,
> use the container's internal URL instead, e.g.:
> `http://authentik-proxy:9000/outpost.goauthentik.io/auth/traefik`

---

### Step 5 — Run Copier

When running `copier copy`, select `authentik` as the auth method and paste the URL:

```
dashboard_auth: authentik
authentik_outpost_url: https://auth.example.com/outpost.goauthentik.io/auth/traefik
```

---

### What gets generated

The template adds these labels to the Traefik container:

```yaml
# ForwardAuth middleware pointing at the Authentik outpost
- "traefik.http.middlewares.authentik.forwardauth.address=<authentik_outpost_url>"
- "traefik.http.middlewares.authentik.forwardauth.trustForwardHeader=true"
- "traefik.http.middlewares.authentik.forwardauth.authResponseHeaders=\
    X-authentik-username,X-authentik-groups,X-authentik-email,\
    X-authentik-name,X-authentik-uid,X-authentik-jwt,\
    X-authentik-meta-jwks,X-authentik-meta-outpost,\
    X-authentik-meta-provider,X-authentik-meta-app,X-authentik-meta-version"

# Dashboard router using the authentik middleware
- "traefik.http.routers.api.middlewares=authentik"
```

| Label | Purpose |
|-------|---------|
| `forwardauth.address` | URL Traefik calls to verify each request |
| `trustForwardHeader` | Pass `X-Forwarded-*` headers upstream to the outpost |
| `authResponseHeaders` | Headers Authentik returns that Traefik forwards to the backend |

---

### Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `401 Unauthorized` on all requests | Outpost URL wrong or unreachable | Check `authentik_outpost_url`; ensure the outpost is on the shared network |
| Redirect loop between Traefik and Authentik | Dashboard domain not excluded in Authentik provider | In the provider, add `traefik_domain` to the **Unauthenticated Paths** regex |
| `500` from outpost | Outpost cannot reach Authentik core | Verify `AUTHENTIK_HOST` env var on the outpost container |
| Cookie not set after login | Domain mismatch | For domain-level mode, ensure **Cookie domain** in the provider matches your domain |

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
