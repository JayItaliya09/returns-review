CREATE TABLE catalog (
    sku TEXT PRIMARY KEY, product TEXT NOT NULL, category TEXT NOT NULL,
    list_c INTEGER NOT NULL CHECK(list_c>0), cost_c INTEGER NOT NULL CHECK(cost_c>=0)
);
CREATE TABLE sales (
    line_id TEXT PRIMARY KEY, shipped TEXT NOT NULL, sku TEXT NOT NULL REFERENCES catalog,
    channel TEXT NOT NULL, units INTEGER NOT NULL CHECK(units>0),
    unit_price_c INTEGER NOT NULL CHECK(unit_price_c>0)
);
CREATE TABLE returns (
    return_id TEXT PRIMARY KEY, line_id TEXT NOT NULL REFERENCES sales,
    received TEXT NOT NULL, reason TEXT NOT NULL, disposition TEXT NOT NULL
    CHECK(disposition IN ('Restock','Write-off')), handling_c INTEGER NOT NULL CHECK(handling_c>=0)
);
-- A return event represents one unit. Recover inventory cost only on restocked units.
CREATE VIEW events AS
SELECT r.*, s.sku, s.channel, s.shipped, c.product, c.category, s.unit_price_c AS refund_c,
       s.unit_price_c - CASE WHEN disposition='Restock' THEN cost_c ELSE 0 END
       + handling_c AS erosion_c
FROM returns r JOIN sales s USING(line_id) JOIN catalog c USING(sku);

-- Roll the many return events up BEFORE joining them to shipment lines.
CREATE VIEW line_economics AS
WITH by_line AS (
    SELECT line_id, COUNT(*) AS returned, SUM(refund_c) AS refund_c,
           SUM(erosion_c) AS erosion_c FROM events GROUP BY line_id
)
SELECT s.*, c.product, c.category, COALESCE(r.returned,0) AS returned,
       COALESCE(r.refund_c,0) AS refund_c, COALESCE(r.erosion_c,0) AS erosion_c,
       s.units * (s.unit_price_c - c.cost_c) AS initial_margin_c
FROM sales s JOIN catalog c USING(sku) LEFT JOIN by_line r USING(line_id);

CREATE VIEW cohorts AS
SELECT substr(shipped,1,7) AS month, category, product, channel,
       SUM(units) AS shipped_units, SUM(returned) AS returned_units,
       SUM(refund_c) AS refund_c, SUM(initial_margin_c) AS initial_margin_c,
       SUM(erosion_c) AS erosion_c
FROM line_economics GROUP BY 1,2,3,4;

CREATE VIEW opportunities AS
WITH groups AS (
    SELECT product, channel, reason, COUNT(*) AS events, SUM(erosion_c) AS erosion_c
    FROM events GROUP BY 1,2,3
)
SELECT DENSE_RANK() OVER (ORDER BY erosion_c DESC) AS priority, *,
       ROUND(100.0 * erosion_c / SUM(erosion_c) OVER (),2) AS share_pct
FROM groups;
