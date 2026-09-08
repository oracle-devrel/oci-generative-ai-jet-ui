"""Seed MongoDB with a synthetic product reviews corpus.

500 products, 5-15 reviews each. Categories, prices, ratings, verified flags
are tuned so the demo aggregation question returns a meaningful chart.
"""

import random
from datetime import datetime, timedelta

from data_migration_harness.environment import mongo_db

CATEGORIES = ["Audio", "Wearables", "Home", "Kitchen", "Outdoor", "Office"]
ADJECTIVES = ["Pro", "Lite", "Max", "Mini", "Plus", "Studio", "Classic"]
NOUNS = {
    "Audio": ["Headphones", "Earbuds", "Speaker", "Soundbar"],
    "Wearables": ["Watch", "Band", "Ring", "Tracker"],
    "Home": ["Lamp", "Vacuum", "Diffuser", "Thermostat"],
    "Kitchen": ["Kettle", "Blender", "Toaster", "Scale"],
    "Outdoor": ["Bottle", "Backpack", "Lantern", "Stove"],
    "Office": ["Mouse", "Keyboard", "Stand", "Lamp"],
}
REVIEW_TEMPLATES = [
    "Great {noun}, exceeded expectations.",
    "The {noun} is solid but the battery life could be better.",
    "Honestly the best {noun} I have owned at this price.",
    "Disappointed with the {noun}; build feels cheap.",
    "Customer service was excellent when my {noun} arrived damaged.",
    "Bought this {noun} on sale and have no regrets.",
    "{noun} is loud and clear; my partner loves it.",
    "Returned the {noun} after one week; not for me.",
]


def generate():
    random.seed(42)
    products = []
    now = datetime(2026, 5, 1)
    for _ in range(500):
        cat = random.choice(CATEGORIES)
        noun = random.choice(NOUNS[cat])
        adj = random.choice(ADJECTIVES)
        name = f"{adj} {noun}"
        price = round(random.uniform(15, 250), 2)
        released = now - timedelta(days=random.randint(0, 365))
        reviews = []
        for _ in range(random.randint(5, 15)):
            tmpl = random.choice(REVIEW_TEMPLATES).format(noun=noun.lower())
            reviews.append(
                {
                    "reviewer_id": f"u_{random.randint(1000, 9999)}",
                    "rating": random.choices([1, 2, 3, 4, 5], weights=[1, 2, 5, 10, 8])[0],
                    "verified_buyer": random.random() < 0.7,
                    "text": tmpl,
                    "posted_at": now - timedelta(days=random.randint(0, 120)),
                }
            )
        products.append(
            {
                "name": name,
                "category": cat,
                "price": price,
                "description": f"A {adj.lower()} {noun.lower()} for everyday use.",
                "vendor": {
                    "name": f"Vendor{random.randint(1, 50)}",
                    "country": random.choice(["UK", "US", "DE", "JP", "FR"]),
                },
                "tags": random.sample(["new", "popular", "eco", "premium", "budget"], k=2),
                "released_at": released,
                "reviews": reviews,
            }
        )
    return products


def main():
    db = mongo_db()
    db.products.drop()
    products = generate()
    db.products.insert_many(products)
    print(f"Inserted {db.products.count_documents({})} products")
    sample = db.products.find_one({"category": "Audio"})
    if sample:
        print(
            f"Sample: {sample['name']} ({sample['category']}) {sample['price']} with {len(sample['reviews'])} reviews"
        )


if __name__ == "__main__":
    main()
