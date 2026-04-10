"""
Seed the development SQLite database with realistic sample data.

Tables created:
  - categories  (product categories)
  - products    (items for sale)
  - users       (customers)
  - orders      (purchase records)
  - order_items (line items per order)

Usage:
    python scripts/seed_sample_db.py
"""

from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    text,
)

DB_PATH = Path(__file__).parent.parent / "db" / "sample.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
meta = MetaData()

# ── Schema ──────────────────────────────────────────────────────────────────

categories = Table(
    "categories", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(100), nullable=False, unique=True),
    Column("description", Text),
)

products = Table(
    "products", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(200), nullable=False),
    Column("category_id", Integer, ForeignKey("categories.id")),
    Column("price", Float, nullable=False),
    Column("stock", Integer, default=0),
    Column("created_at", DateTime, default=datetime.utcnow),
)

users = Table(
    "users", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(150), nullable=False),
    Column("email", String(200), nullable=False, unique=True),
    Column("state", String(50)),
    Column("city", String(100)),
    Column("joined_at", DateTime, default=datetime.utcnow),
)

orders = Table(
    "orders", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("status", String(30), default="completed"),
    Column("total", Float, nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)

order_items = Table(
    "order_items", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("order_id", Integer, ForeignKey("orders.id")),
    Column("product_id", Integer, ForeignKey("products.id")),
    Column("quantity", Integer, nullable=False),
    Column("unit_price", Float, nullable=False),
)

# ── Seed data ────────────────────────────────────────────────────────────────

CATEGORIES = [
    ("Electronics", "Gadgets and devices"),
    ("Clothing", "Apparel and accessories"),
    ("Books", "Physical and digital books"),
    ("Home & Garden", "Furniture, tools, and plants"),
    ("Sports", "Fitness and outdoor equipment"),
]

PRODUCTS = [
    ("Wireless Headphones", 1, 79.99, 200),
    ("Mechanical Keyboard", 1, 129.99, 150),
    ("USB-C Hub", 1, 49.99, 300),
    ("Smart Watch", 1, 199.99, 80),
    ("Laptop Stand", 1, 39.99, 250),
    ("Running Shoes", 2, 89.99, 180),
    ("Hoodie", 2, 49.99, 300),
    ("Yoga Mat", 5, 34.99, 400),
    ("Python Cookbook", 3, 29.99, 500),
    ("Design Patterns", 3, 34.99, 220),
    ("Coffee Table Book", 3, 24.99, 100),
    ("Desk Lamp", 4, 44.99, 160),
    ("Plant Pot Set", 4, 19.99, 350),
    ("Resistance Bands", 5, 22.99, 600),
    ("Water Bottle", 5, 17.99, 800),
]

STATES = ["California", "Texas", "New York", "Florida", "Washington",
          "Illinois", "Georgia", "Colorado", "Oregon", "Nevada"]
CITIES = ["San Francisco", "Austin", "New York City", "Miami", "Seattle",
          "Chicago", "Atlanta", "Denver", "Portland", "Las Vegas"]

STATUS_CHOICES = ["completed", "completed", "completed", "pending", "cancelled"]


def random_date(days_back: int = 365) -> datetime:
    return datetime.utcnow() - timedelta(days=random.randint(0, days_back))


def seed() -> None:
    meta.drop_all(engine)
    meta.create_all(engine)

    with engine.begin() as conn:
        # Categories
        cat_ids: list[int] = []
        for name, desc in CATEGORIES:
            r = conn.execute(categories.insert().values(name=name, description=desc))
            cat_ids.append(r.inserted_primary_key[0])

        # Products
        prod_ids: list[int] = []
        for name, cat_idx, price, stock in PRODUCTS:
            r = conn.execute(products.insert().values(
                name=name,
                category_id=cat_ids[cat_idx - 1],
                price=price,
                stock=stock,
                created_at=random_date(730),
            ))
            prod_ids.append(r.inserted_primary_key[0])

        # Users (100)
        user_ids: list[int] = []
        first_names = ["Alice", "Bob", "Carol", "David", "Eva",
                       "Frank", "Grace", "Henry", "Iris", "James"]
        last_names  = ["Smith", "Johnson", "Williams", "Brown", "Jones",
                       "Garcia", "Miller", "Davis", "Wilson", "Martinez"]
        used_emails: set[str] = set()
        for i in range(100):
            fn = random.choice(first_names)
            ln = random.choice(last_names)
            email_base = f"{fn.lower()}.{ln.lower()}"
            email = f"{email_base}{i}@example.com"
            while email in used_emails:
                email = f"{email_base}{i}_{random.randint(1,99)}@example.com"
            used_emails.add(email)
            state_idx = random.randint(0, len(STATES) - 1)
            r = conn.execute(users.insert().values(
                name=f"{fn} {ln}",
                email=email,
                state=STATES[state_idx],
                city=CITIES[state_idx],
                joined_at=random_date(730),
            ))
            user_ids.append(r.inserted_primary_key[0])

        # Orders + order_items (300 orders)
        for _ in range(300):
            user_id = random.choice(user_ids)
            n_items = random.randint(1, 4)
            selected = random.sample(range(len(prod_ids)), n_items)
            total = 0.0
            order_date = random_date(365)

            r = conn.execute(orders.insert().values(
                user_id=user_id,
                status=random.choice(STATUS_CHOICES),
                total=0.0,
                created_at=order_date,
            ))
            order_id = r.inserted_primary_key[0]

            for pi in selected:
                prod_price = PRODUCTS[pi][2]
                qty = random.randint(1, 3)
                total += prod_price * qty
                conn.execute(order_items.insert().values(
                    order_id=order_id,
                    product_id=prod_ids[pi],
                    quantity=qty,
                    unit_price=prod_price,
                ))

            conn.execute(
                orders.update().where(orders.c.id == order_id).values(total=round(total, 2))
            )

    print(f"Database seeded at {DB_PATH}")
    print(f"  {len(CATEGORIES)} categories, {len(PRODUCTS)} products, "
          f"100 users, 300 orders")


if __name__ == "__main__":
    seed()
