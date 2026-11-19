"""Build a validated SQLite warehouse and two portable reporting marts."""
import csv
import sqlite3
import tempfile
from pathlib import Path
from generate import ROOT, RAW, write_csv


def build():
    mart = ROOT / "data/mart"
    mart.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory(dir=mart) as stage:
        stage = Path(stage)
        db = sqlite3.connect(stage / "returns.sqlite")
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript((ROOT / "sql/model.sql").read_text())
            duplicates = 0
            for table in ("catalog", "sales", "returns"):
                with (RAW / f"{table}.csv").open(newline="", encoding="utf-8") as stream:
                    reader = csv.reader(stream)
                    expected = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
                    if next(reader) != expected:
                        raise ValueError(f"Unexpected {table} header")
                    seen = {}
                    for row in reader:
                        if table == "returns" and row[0] in seen:
                            if row != seen[row[0]]:
                                raise ValueError(f"Conflicting return event {row[0]}")
                            duplicates += 1
                            continue
                        if table == "returns":
                            seen[row[0]] = row
                        db.execute(f"INSERT INTO {table} VALUES ({','.join('?' for _ in expected)})", row)
            checks = {
                "over-returned lines": "SELECT COUNT(*) FROM line_economics WHERE returned>units",
                "invalid event dates": """SELECT COUNT(*) FROM events WHERE julianday(received) IS NULL
                    OR julianday(shipped) IS NULL OR julianday(received)-julianday(shipped) NOT BETWEEN 0 AND 30""",
                "unit reconciliation": "SELECT ABS((SELECT SUM(shipped_units) FROM cohorts)-(SELECT SUM(units) FROM sales))",
                "return reconciliation": "SELECT ABS((SELECT SUM(returned_units) FROM cohorts)-(SELECT COUNT(*) FROM returns))",
                "cost reconciliation": "SELECT ABS((SELECT SUM(erosion_c) FROM cohorts)-(SELECT SUM(erosion_c) FROM events))",
            }
            for label, query in checks.items():
                if db.execute(query).fetchone()[0] != 0:
                    raise ValueError(label)
            for view, order in [("cohorts","month, product, channel"),("opportunities","priority, product, channel, reason")]:
                cursor = db.execute(f"SELECT * FROM {view} ORDER BY {order}")
                write_csv(stage / f"{view}.csv", [col[0] for col in cursor.description], cursor)
            db.commit()
            print(f"Removed {duplicates} repeated events. Passed {len(checks)} warehouse checks.")
        finally:
            db.close()
        for path in stage.iterdir():
            path.replace(mart / path.name)


if __name__ == "__main__":
    build()
