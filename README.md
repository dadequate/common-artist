# CommonArtist

Open source co-op gallery management. For artist collectives, consignment galleries, and maker spaces.

Built from the ground up at [Maine Pottery Co.](https://mainepottery.com) — running in production across 3 galleries with 55+ artists before it was open source.

---

## What it does

- Artist onboarding, applications, and digital agreements
- Booth/space management with rent tracking and automated holds
- Shopify POS integration — sales sync to artist ledgers automatically
- Monthly payout calculation, review, and statement generation
- Artist portal — self-service sales history, payout statements, and real-time sale notifications
- Shift calendar for co-op staffing requirements
- Built-in monitor — structured logging, health checks, and alert rules watching every critical path

## Quick start

```bash
cp .env.example .env
# Edit .env with your settings
docker compose up
```

App is at `http://localhost:8000`. Health check at `http://localhost:8000/health`.

## Stack

- **Backend:** FastAPI + SQLAlchemy 2 (async) + PostgreSQL
- **Frontend:** Jinja2 templates + Alpine.js
- **Observability:** structlog (JSON), built-in monitor dashboard, alerting via email/Slack webhook
- **Payments:** Stripe Connect Express (ACH payouts)
- **POS adapters:** Shopify (Phase 2), Square (Phase 4), manual entry always available

## License

MIT — use it, fork it, run it for free forever.

## Status

Phase 0 — foundation scaffolded. See [PRD](docs/plans/OPEN_SOURCE_COOP_PRD.md) for the full roadmap.
