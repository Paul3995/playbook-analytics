-- ============================================================
-- KPI: Gross Gaming Revenue (GGR) — Daily
-- GGR = Total Stakes - Total Payouts (settled bets only)
-- ============================================================

SELECT
    DATE(settled_ts)                            AS settlement_date,
    COUNT(*)                                    AS settled_bets,
    SUM(stake)                                  AS total_stakes,
    COALESCE(SUM(actual_payout), 0)             AS total_payouts,
    SUM(stake) - COALESCE(SUM(actual_payout), 0) AS ggr,
    ROUND(
        (SUM(stake) - COALESCE(SUM(actual_payout), 0)) / NULLIF(SUM(stake), 0) * 100,
        2
    )                                           AS hold_pct,
    currency
FROM bets
WHERE
    status   IN ('won', 'lost')
    AND settled_ts >= :start_date
    AND settled_ts <  :end_date
GROUP BY
    DATE(settled_ts),
    currency
ORDER BY
    settlement_date DESC,
    currency;
