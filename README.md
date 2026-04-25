# CommonArtist

Open source co-op gallery management. For artist collectives, consignment galleries, and maker spaces.

Built from the ground up at [Maine Pottery Co.](https://mainepottery.com) — running in production across 3 galleries with 55+ artists before it was open source.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/commonartist)

---

## What it does

- **Artist management** — onboarding, applications queue, status tracking, W-9 on file
- **Booth & space management** — assignments, rent charges, payment tracking, overdue alerts
- **POS sync** — Shopify sales sync to artist ledgers automatically; manual entry always available
- **Payout engine** — calculate commissions, deduct rent, review, mark paid; supports check or Stripe ACH
- **Artist portal** — magic-link login, self-service sales history, payout statements
- **Monitor dashboard** — sync health, error log, overdue rent, and an embedded Claude AI assistant
- **Public apply form** — artists submit applications; admins review and approve with one click

## Quick start

```bash
git clone https://github.com/dadequate/common-artist
cd common-artist
cp .env.example .env
# Edit .env — set SECRET_KEY, ADMIN_PASSWORD, DATABASE_URL at minimum
docker compose up
```

App runs at `http://localhost:8000`. Log in at `/admin/login`.

### Minimal .env for local dev

```
SECRET_KEY=any-long-random-string
ADMIN_PASSWORD=yourpassword
DATABASE_URL=postgresql://commonartist:commonartist@db:5432/commonartist
GALLERY_NAME=My Co-op Gallery
POS_PROVIDER=manual
EMAIL_PROVIDER=log
```

`EMAIL_PROVIDER=log` prints magic links to stdout so you can test the artist portal without configuring SMTP.

## Deploy to Railway

1. Fork this repo
2. Create a new Railway project, connect your fork
3. Add a Postgres database service
4. Set these environment variables:
   - `SECRET_KEY` — long random string
   - `ADMIN_PASSWORD` — your admin password
   - `DATABASE_URL` — Railway auto-fills this when you link the Postgres service
   - `GALLERY_NAME` — your gallery name (shows in all templates)
   - `BASE_URL` — your Railway public URL
5. Deploy — Railway runs `alembic upgrade head` then starts the app automatically

## Stack

- **Backend:** FastAPI + SQLAlchemy 2 (async) + PostgreSQL
- **Frontend:** Jinja2 templates + Alpine.js
- **Observability:** structlog (JSON), built-in monitor dashboard
- **POS adapters:** Shopify (live), manual entry (always available)
- **Payments:** check workflow (default) or Stripe Connect Express
- **AI assistant:** Claude Haiku on the monitor page (optional, needs `ANTHROPIC_API_KEY`)

## Development

```bash
pip install -r requirements-dev.txt
pytest                   # 17 smoke tests, no Postgres needed (SQLite in-memory)
```

Tests use SQLite with StaticPool — no database setup required.

## Environment variables

See [.env.example](.env.example) for the full list with comments. Key variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | yes | — | JWT signing key |
| `ADMIN_PASSWORD` | yes | — | Admin login password |
| `DATABASE_URL` | yes | — | PostgreSQL connection string |
| `GALLERY_NAME` | no | CommonArtist Gallery | Shown in all templates |
| `BASE_URL` | no | http://localhost:8000 | Used in magic link emails |
| `POS_PROVIDER` | no | manual | `shopify` or `manual` |
| `EMAIL_PROVIDER` | no | log | `log`, `smtp`, or `brevo` |
| `ANTHROPIC_API_KEY` | no | — | Enables AI assistant on monitor page |

## License

MIT — use it, fork it, run it for free forever.

## Status

v0.1 — feature-complete for the core consignment workflow. See [PRD](docs/plans/OPEN_SOURCE_COOP_PRD.md) for the full roadmap.

What's working:
- Admin auth (password + JWT cookie)
- Artist CRUD, applications queue, public apply form
- Booth management, rent charges, payment recording
- Shopify POS sync + manual sales entry
- Payout engine (draft → review → paid)
- Artist portal (magic link, sales history, payout statements)
- Monitor dashboard + AI assistant
- Railway deploy, Docker Compose, Alembic migrations, seed script
