"""Sample data generator for CPS Growth Copilot."""
import asyncio
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "user": os.getenv("POSTGRES_USER", "cps_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "cps_password"),
    "database": os.getenv("POSTGRES_DB", "cps_growth"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
}


async def generate_sample_data():
    """Generate 30 days of sample data."""
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # Clear existing data (optional, for clean demo)
        await conn.execute("TRUNCATE TABLE orders, clicks, content_product_map, contents, commission_rules, campaigns, products, taokes, merchants CASCADE")

        # Create merchants
        merchants = []
        for i in range(1, 4):
            merchant_id = await conn.fetchval(
                "INSERT INTO merchants (name) VALUES ($1) RETURNING id",
                f"商家{i}"
            )
            merchants.append(merchant_id)
        print(f"Created {len(merchants)} merchants")

        # Create taokes
        taokes = []
        for i in range(1, 4):
            taoke_id = await conn.fetchval(
                "INSERT INTO taokes (name) VALUES ($1) RETURNING id",
                f"淘客{i}"
            )
            taokes.append(taoke_id)
        print(f"Created {len(taokes)} taokes")

        # Create products
        products = []
        categories = ["电子产品", "服装", "美妆", "食品", "家居"]
        for merchant_id in merchants:
            for i in range(5):
                product_id = await conn.fetchval(
                    """INSERT INTO products (merchant_id, name, price, stock, category)
                       VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                    merchant_id,
                    f"商品{i+1}",
                    Decimal(random.uniform(50, 500)),
                    random.randint(10, 1000),
                    random.choice(categories),
                )
                products.append((product_id, merchant_id))
        print(f"Created {len(products)} products")

        # Create commission rules
        for merchant_id in merchants:
            for taoke_id in taokes:
                for product_id, _ in products:
                    if random.random() > 0.3:  # 70% coverage
                        await conn.execute(
                            """INSERT INTO commission_rules
                               (merchant_id, product_id, taoke_id, commission_rate, commission_type, effective_from)
                               VALUES ($1, $2, $3, $4, $5, $6)""",
                            merchant_id,
                            product_id,
                            taoke_id,
                            Decimal(random.uniform(0.05, 0.25)),  # 5-25%
                            "percentage",
                            date.today() - timedelta(days=60),
                        )
        print("Created commission rules")

        # Generate 30 days of data
        today = date.today()
        contents_map = {}  # taoke_id -> list of content_ids

        for day_offset in range(30, 0, -1):
            target_date = today - timedelta(days=day_offset)
            print(f"Generating data for {target_date}...")

            # Create contents (impressions)
            for taoke_id in taokes:
                merchant_id = random.choice(merchants)
                content_id = await conn.fetchval(
                    """INSERT INTO contents (taoke_id, merchant_id, title, content_type, url)
                       VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                    taoke_id,
                    merchant_id,
                    f"内容素材-{target_date}-{taoke_id}",
                    random.choice(["article", "video", "image"]),
                    f"https://example.com/content/{taoke_id}/{target_date}",
                )

                if taoke_id not in contents_map:
                    contents_map[taoke_id] = []
                contents_map[taoke_id].append(content_id)

                # Link products to content
                linked_products = random.sample(
                    [p[0] for p in products if p[1] == merchant_id],
                    min(3, len([p for p in products if p[1] == merchant_id])),
                )
                for product_id in linked_products:
                    await conn.execute(
                        "INSERT INTO content_product_map (content_id, product_id) VALUES ($1, $2)",
                        content_id,
                        product_id,
                    )

            # Generate clicks (from impressions)
            for taoke_id in taokes:
                if taoke_id not in contents_map:
                    continue

                # CTR: 2-8%
                num_clicks = max(1, int(len(contents_map[taoke_id]) * random.uniform(0.02, 0.08)))

                for _ in range(num_clicks):
                    content_id = random.choice(contents_map[taoke_id])
                    # Get products linked to this content
                    product_rows = await conn.fetch(
                        "SELECT product_id FROM content_product_map WHERE content_id = $1",
                        content_id,
                    )
                    if not product_rows:
                        continue

                    product_id = random.choice([r["product_id"]for r in product_rows])
                    merchant_id = next(p[1] for p in products if p[0] == product_id)

                    click_id = await conn.fetchval(
                        """INSERT INTO clicks (taoke_id, content_id, product_id, merchant_id, clicked_at, ip_address)
                           VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
                        taoke_id,
                        content_id,
                        product_id,
                        merchant_id,
                        datetime.combine(target_date, datetime.min.time()) + timedelta(
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59),
                        ),
                        f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
                    )

                    # Generate orders (CVR: 1-5%)
                    if random.random() < random.uniform(0.01, 0.05):
                        # Get product price
                        product_price = await conn.fetchval(
                            "SELECT price FROM products WHERE id = $1", product_id
                        )

                        # Get commission rate
                        commission_rate = await conn.fetchval(
                            """SELECT commission_rate FROM commission_rules
                               WHERE merchant_id = $1 AND product_id = $2 AND taoke_id = $3
                               ORDER BY effective_from DESC LIMIT 1""",
                            merchant_id,
                            product_id,
                            taoke_id,
                        )
                        if commission_rate is None:
                            commission_rate = Decimal("0.10")  # Default 10%

                        order_amount = product_price * Decimal(random.uniform(0.9, 1.1))
                        commission_amount = order_amount * commission_rate

                        # Order status
                        status_weights = [("paid", 0.7), ("pending", 0.2), ("refunded", 0.1)]
                        status = random.choices(
                            [s[0] for s in status_weights],
                            weights=[s[1] for s in status_weights],
                        )[0]

                        ordered_at = datetime.combine(target_date, datetime.min.time()) + timedelta(
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59),
                        )

                        paid_at = None
                        refunded_at = None
                        if status == "paid":
                            paid_at = ordered_at + timedelta(hours=random.randint(1, 24))
                        elif status == "refunded":
                            refunded_at = ordered_at + timedelta(days=random.randint(1, 7))

                        await conn.execute(
                            """INSERT INTO orders
                               (taoke_id, merchant_id, product_id, click_id, order_amount, commission_amount, status, ordered_at, paid_at, refunded_at)
                               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                            taoke_id,
                            merchant_id,
                            product_id,
                            click_id,
                            order_amount,
                            commission_amount,
                            status,
                            ordered_at,
                            paid_at,
                            refunded_at,
                        )

        print("\n✅ Sample data generation completed!")
        print(f"   - Merchants: {len(merchants)}")
        print(f"   - Taokes: {len(taokes)}")
        print(f"   - Products: {len(products)}")
        print(f"   - 30 days of data generated")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(generate_sample_data())

