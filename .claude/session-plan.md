# CommonArtist — Build Plan
**Created:** 2026-04-25
**Status:** Active
**PRD:** memo-payouts/docs/plans/OPEN_SOURCE_COOP_PRD.md v0.2

---

## What You'll End Up With

A self-hostable open source co-op gallery management platform:
- Artists onboard and manage their booth + consignment
- Gallery manager runs monthly payouts with one review screen
- Artist portal (mobile-first) shows live sales, history, and statements
- Built-in monitor catches problems before users do
- MPC running on it in production. One non-MPC gallery running as beta.
- GitHub repo open and community-ready.

---

## Phase Weights

```
DISCOVER    ░░░░░░░░░░░░░░░░░░░░  5%   (research done — research doc exists)
DEFINE      ████░░░░░░░░░░░░░░░░ 15%   (PRD locked, scope clear)
DEVELOP     ████████████████░░░░ 65%   (this is a build project)
DELIVER     ████░░░░░░░░░░░░░░░░ 15%   (MPC payout cycle + beta gallery gate)
```

---

## Execution Plan

### NOW — Immediate (this session or next)

**1. GitHub repo**
- Create `dadequate/common-artist` on GitHub (public from day one)
- Push the scaffold we built today
- Add Railway deploy button to README
- Enable Dependabot, branch protection on main

**2. Domain model spike — most important work**
- Before writing any payout or portal code, nail the data model
- Key entities: `Artist`, `Booth`, `BoothAssignment`, `RentCharge`, `Sale`, `SaleItem`, `PayoutRun`, `PayoutLine`, `Agreement`
- Write `app/models/` with full SQLAlchemy models
- Write Alembic migration
- Write `make seed` that loads 10 fake artists, 10 booths, 30 days of fake sales
- **Why first:** every other feature depends on this being right. A wrong model costs 10x to fix later.

**3. Shopify sync spike (2-week timebox)**
- This is the hardest v0.1 problem — do it before anything else depends on it
- Map Shopify `vendor` field → Artist
- Handle: multi-artist orders, returns, exchanges, gift card redemptions, split tenders
- Output: `SaleItem` records per artist per order
- Define what "broken sync" looks like so the monitor can detect it
- If this can't be solved cleanly in 2 weeks → document the constraint and ship manual-entry-only v0.1

---

### v0.1 — Core Loop

**Goal:** MPC completes one real payout cycle on CommonArtist.

**Build order (dependency-ordered):**

1. **Models + migrations** — Artist, Booth, Sale, Payout, Agreement, User
2. **Admin auth** — single admin login (env var password for v0.1, upgrade in v0.2)
3. **Artist management** — profile CRUD, application form, approval workflow, agreement signing
4. **Booth management** — booth registry, tier pricing, assignment, rent ledger
5. **Shopify sync** — order pull, SKU→artist mapping, SaleItem creation, sync error logging
6. **Manual sale entry** — for non-Shopify fallback (always works, Shopify is optional)
7. **Payout engine** — calculation, rent hold logic, review screen, mark-as-paid
8. **Payout statements** — PDF generation (WeasyPrint or similar, no Chrome dependency)
9. **Artist portal** — magic link login, dashboard, sales history, payout history
10. **Monitor foundation** — health endpoint, ping, error log table, structlog wired everywhere

**v0.1 done when:** MPC runs real October/November payout on CommonArtist. Not staging. Real data.

---

### v0.2 — Self-Service + Visibility

1. Sale notifications (email on Shopify webhook)
2. Artist portal: settings, notification prefs, help form
3. Shift calendar: slots, sign-up, requirements tracking, no-show fee
4. Alert rules engine + default rules (each feature ships its own rules)
5. Monitor dashboard (admin-only live feed)
6. Multi-user admin roles (Owner, Manager, Staff)
7. Activity log
8. Minimum payout threshold + seasonal rates

---

### v0.3 — Payments + Beta Gate

1. Stripe Connect Express onboarding
2. ACH payouts via Stripe Connect
3. Year-end tax export
4. Data export / GDPR tools
5. Portal: price change requests, inventory view
6. Full test coverage on payout engine and sync paths

**v1.0 GATE (required before open source launch):**
- Recruit 1 non-MPC gallery as beta user
- They complete full onboarding (artists loaded, Shopify connected, one payout cycle)
- **Without help from the CommonArtist team**
- Document every blocker they hit — fix them all before v1.0

---

### v1.0 — Open Source Launch

1. Fix all beta gallery blockers
2. Security review (OWASP, dependency audit)
3. Self-hosting docs (Railway, VPS Docker Compose, upgrade guide)
4. Demo mode: `make seed` with realistic fake data
5. CONTRIBUTING.md, issue templates, GitHub Discussions
6. MPC fully migrated off memo-payouts (memo-payouts kept read-only for 60 days)
7. Public announcement

---

## Key Engineering Decisions (locked)

| Decision | Chosen | Rationale |
|---|---|---|
| Shopify is reference impl, not adapter | Reference impl | Don't abstract before understanding the domain |
| Square is v0.4 port | Port from Shopify model | Build what generalizes, then generalize |
| Stripe Connect in v0.3 | After payout logic proven | Connect onboarding is irreversible; prove correctness first |
| Monitor grows with features | Incremental | Alert fatigue prevention; no orphaned rules |
| Artist portal is mobile-first | 390px-first | Dana uses this on her phone |
| MIT license | MIT | Adoption > defensibility in this niche |
| Railway easy deploy | Primary non-technical path | Ship `railway.json` + deploy button |
| Non-MPC beta gates v1.0 | Hard gate | MPC-specific assumptions = the project's blind spot |

---

## Debate Checkpoints

Before merging Shopify sync to main:
- Does the SKU→artist mapping handle all edge cases (returns, gift cards, multi-artist orders)?

Before v0.3 Stripe Connect work begins:
- Has v0.1 payout engine survived one full real-world payout cycle without errors?

Before v1.0 launch:
- Can a stranger onboard their gallery without our help?

---

## Success Criteria

1. MPC runs one payout cycle on CommonArtist (v0.1)
2. Non-MPC gallery onboards independently (v0.3 gate)
3. MPC fully migrated off memo-payouts (v1.0)
4. GitHub: 200+ stars at 6 months post-launch
5. Community PRs from non-MPC contributors

---

## Next Actions (ordered)

- [ ] Create GitHub repo `dadequate/common-artist` (public)
- [ ] Push scaffold, add Railway deploy button
- [ ] Write `app/models/` — full domain model
- [ ] Write Alembic migration + `make seed`
- [ ] Start Shopify sync spike (2-week timebox)
- [ ] Admin auth + artist management (while sync spike runs)
