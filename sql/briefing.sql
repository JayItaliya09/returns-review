-- Weekly analyst briefing. Currency fields here are converted to euros.
SELECT channel, SUM(shipped_units) AS shipped, SUM(returned_units) AS returned,
       ROUND(100.0*SUM(returned_units)/SUM(shipped_units),2) AS return_rate_pct,
       ROUND(SUM(erosion_c)/100.,2) AS erosion_eur
FROM cohorts GROUP BY channel;

SELECT priority, product, channel, reason, events, erosion_c/100.0 AS erosion_eur,
       share_pct FROM opportunities ORDER BY priority LIMIT 10;

-- A delayed January receipt still belongs to the original December shipment cohort.
SELECT substr(shipped,1,7) AS shipment_month, substr(received,1,7) AS receipt_month,
       COUNT(*) AS units FROM events
WHERE substr(shipped,1,7) <> substr(received,1,7)
GROUP BY 1,2 ORDER BY 1,2;
