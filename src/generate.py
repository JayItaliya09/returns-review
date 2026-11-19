"""Generate repeatable, fictional extracts from a retailer and its returns desk."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def generate():
    rng = random.Random(7301)
    products = [
        ("FW01", "Trail runner", "Footwear", 8900, 3900, .23),
        ("FW02", "City sneaker", "Footwear", 6900, 2900, .16),
        ("AP01", "Rain shell", "Apparel", 9900, 4500, .14),
        ("AP02", "Merino tee", "Apparel", 4900, 2150, .12),
        ("HM01", "Stoneware set", "Home", 5900, 2800, .10),
        ("HM02", "Reading lamp", "Home", 7900, 3450, .06),
        ("AC01", "Daypack", "Accessories", 6500, 2600, .07),
        ("AC02", "Steel bottle", "Accessories", 2900, 1100, .04),
    ]
    write_csv(RAW / "catalog.csv", ["sku","product","category","list_c","cost_c"],
              [p[:5] for p in products])
    sales, returns = [], []
    start = date(2025, 1, 1)
    for day in range(365):
        shipped = start + timedelta(days=day)
        count = rng.randint(26, 48) + (18 if shipped.month in (11, 12) else 0)
        for _ in range(count):
            sku, _, category, price, _, probability = rng.choice(products)
            channel = rng.choices(["Web", "Store"], weights=[7, 3])[0]
            units = rng.choices([1, 2, 3], weights=[83, 14, 3])[0]
            line_id = f"L{len(sales)+1:06d}"
            price = price * rng.choice([100, 100, 100, 90, 85]) // 100
            sales.append((line_id, shipped, sku, channel, units, price))
            for _ in range(units):
                if rng.random() >= probability * (1 if channel == "Web" else .64):
                    continue
                reason = rng.choices(
                    ["Fit", "Damage", "Changed mind", "Description"],
                    weights={"Footwear":[71,5,14,10], "Apparel":[60,6,18,16],
                             "Home":[0,58,22,20], "Accessories":[0,9,61,30]}[category])[0]
                received = shipped + timedelta(days=rng.randint(2, 30))
                restock = rng.random() < (.12 if reason == "Damage" else .92)
                returns.append((f"R{len(returns)+1:05d}", line_id, received, reason,
                                "Restock" if restock else "Write-off", rng.choice([450,550,650])))
    write_csv(RAW / "sales.csv", ["line_id","shipped","sku","channel","units","unit_price_c"], sales)
    write_csv(RAW / "returns.csv", ["return_id","line_id","received","reason","disposition","handling_c"],
              returns + returns[:12])  # Simulate an overlapping export batch.


if __name__ == "__main__":
    generate()
