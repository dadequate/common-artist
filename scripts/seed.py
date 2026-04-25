"""
Seed the database with demo data: 10 artists, 10 booths, 30 days of sales, rent charges.
Run: python scripts/seed.py
"""
import asyncio
import random
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

from app.database import AsyncSessionLocal, engine
from app.models import Artist, Booth, BoothAssignment, RentCharge, Sale, SaleLineItem
from app.models.artist import ArtistStatus

random.seed(42)

ARTISTS = [
    ("Maya Chen",       "maya@example.com",     "Maya Chen Ceramics",    0.25),
    ("James Whitfield", "james@example.com",    "Whitfield Pottery",     0.25),
    ("Priya Nair",      "priya@example.com",    "Priya Nair Studio",     0.20),
    ("Tom Gallagher",   "tom@example.com",      "Gallagher Works",       0.25),
    ("Susan Park",      "susan@example.com",    "Park Clay",             0.30),
    ("Eli Marks",       "eli@example.com",      "Marks Handmade",        0.25),
    ("Cora Flynn",      "cora@example.com",     "Cora Flynn Art",        0.25),
    ("David Osei",      "david@example.com",    "Osei Pottery",          0.20),
    ("Anna Winters",    "anna@example.com",     "Winters Studio",        0.25),
    ("Luis Reyes",      "luis@example.com",     "Reyes Ceramics",        0.30),
]

BOOTHS = [
    ("Booth 1",  "small",   18000),
    ("Booth 2",  "small",   18000),
    ("Booth 3",  "large",   28000),
    ("Booth 4",  "large",   28000),
    ("Booth 5",  "large",   28000),
    ("Wall A",   "wall",    22000),
    ("Wall B",   "wall",    22000),
    ("Corner 1", "special", 35000),
    ("Corner 2", "special", 35000),
    ("Pedestal", "small",   12000),
]

PRODUCTS = [
    ("Mug",          2800),
    ("Bowl",         4500),
    ("Vase",         6500),
    ("Platter",      8500),
    ("Teapot",      14000),
    ("Set of 4 Mugs",9800),
    ("Bud Vase",     3800),
    ("Serving Bowl", 7200),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: None)  # ping — fail fast if no DB

    async with AsyncSessionLocal() as db:
        existing = await db.execute(text("SELECT COUNT(*) FROM artists"))
        if existing.scalar() > 0:
            print("Database already has data — skipping seed.")
            return

        today = date.today()
        period_start = today.replace(day=1)

        # Artists
        artists = []
        for name, email, vendor, rate in ARTISTS:
            a = Artist(
                id=str(uuid.uuid4()),
                name=name,
                email=email,
                pos_vendor_name=vendor,
                commission_rate_override=str(rate),
                status=ArtistStatus.ACTIVE,
            )
            db.add(a)
            artists.append(a)

        # Booths
        booths = []
        for bname, tier, rate_cents in BOOTHS:
            b = Booth(
                id=str(uuid.uuid4()),
                name=bname,
                tier=tier,
                monthly_rate_cents=rate_cents,
            )
            db.add(b)
            booths.append(b)

        await db.flush()

        # Assign each booth an artist (wrap around — 10 artists, 10 booths)
        assign_start = period_start - timedelta(days=45)
        for i, booth in enumerate(booths):
            artist = artists[i % len(artists)]
            assignment = BoothAssignment(
                id=str(uuid.uuid4()),
                booth_id=booth.id,
                artist_id=artist.id,
                started_at=assign_start,
            )
            db.add(assignment)

            rent = RentCharge(
                id=str(uuid.uuid4()),
                artist_id=artist.id,
                booth_id=booth.id,
                period_start=period_start,
                period_end=period_start + timedelta(days=30),
                amount_cents=booth.monthly_rate_cents,
                paid_cents=booth.monthly_rate_cents if i % 3 != 0 else 0,
            )
            db.add(rent)

        await db.flush()

        # Sales — 30 days, 3-8 per day
        for days_ago in range(30, 0, -1):
            day = today - timedelta(days=days_ago)
            num_sales = random.randint(3, 8)
            for _ in range(num_sales):
                artist = random.choice(artists)
                product, price = random.choice(PRODUCTS)
                qty = random.randint(1, 3)
                amount = price * qty
                commission_rate = float(artist.commission_rate_override or 0.25)
                commission = int(amount * commission_rate)
                order_id = f"SEED-{uuid.uuid4().hex[:8].upper()}"
                occurred = datetime(day.year, day.month, day.day,
                                    random.randint(10, 18), random.randint(0, 59),
                                    tzinfo=timezone.utc)

                sale = Sale(
                    id=str(uuid.uuid4()),
                    external_id=order_id,
                    source="manual",
                    occurred_at=occurred,
                )
                db.add(sale)
                await db.flush()

                line = SaleLineItem(
                    id=str(uuid.uuid4()),
                    sale_id=sale.id,
                    external_id=f"{order_id}-1",
                    order_external_id=order_id,
                    artist_id=artist.id,
                    artist_external_id=artist.pos_vendor_name or artist.name,
                    amount_cents=amount,
                    commission_rate=commission_rate,
                    commission_cents=commission,
                    source="manual",
                    raw={"product": product, "qty": qty, "seed": True},
                    occurred_at=occurred,
                )
                db.add(line)

        await db.commit()

    total_sales = 30 * 5  # approx
    print(f"Seeded: {len(artists)} artists, {len(booths)} booths, ~{total_sales} sales")
    print("Login: set ADMIN_PASSWORD in .env and visit /admin/login")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(seed())
