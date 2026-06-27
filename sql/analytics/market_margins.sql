-- ============================================================
-- Analytics: Market Margins, Odds Accuracy & Settlement
-- ============================================================

-- Actual hold vs theoretical margin by market type
WITH settled_markets AS (
    SELECT
        m.market_type,
        b.bet_id,
        b.stake,
        b.actual_payout,
        b.status
    FROM bets b
    JOIN bet_selections bs ON bs.bet_id = b.bet_id
    JOIN selections sel    ON sel.selection_id = bs.selection_id
    JOIN markets m         ON m.market_id = sel.market_id
    WHERE b.status IN ('won', 'lost')
      AND b.settled_ts >= :start_date
)
SELECT
    market_type,
    COUNT(*)                                                        AS settled_bets,
    ROUND(SUM(stake), 2)                                            AS total_staked,
    ROUND(SUM(stake) - COALESCE(SUM(actual_payout), 0), 2)         AS ggr,
    ROUND(
        (SUM(stake) - COALESCE(SUM(actual_payout), 0))
        / NULLIF(SUM(stake), 0) * 100, 2
    )                                                               AS actual_hold_pct,
    ROUND(
        COUNT(CASE WHEN status = 'won' THEN 1 END) * 100.0
        / NULLIF(COUNT(*), 0), 1
    )                                                               AS win_rate_pct
FROM settled_markets
GROUP BY market_type
ORDER BY total_staked DESC;


-- Odds accuracy: compare implied probability to actual outcome rate
SELECT
    CASE
        WHEN bs.odds_at_place < 1.5   THEN '< 1.50 (heavy fav)'
        WHEN bs.odds_at_place < 2.0   THEN '1.50 – 1.99'
        WHEN bs.odds_at_place < 3.0   THEN '2.00 – 2.99'
        WHEN bs.odds_at_place < 5.0   THEN '3.00 – 4.99'
        WHEN bs.odds_at_place < 10.0  THEN '5.00 – 9.99'
        ELSE '10.00+'
    END                                                 AS odds_bracket,
    COUNT(*)                                            AS selections,
    ROUND(AVG(1.0 / bs.odds_at_place) * 100, 1)        AS implied_prob_pct,
    ROUND(
        COUNT(CASE WHEN sel.result = 'win' THEN 1 END) * 100.0
        / NULLIF(COUNT(*), 0), 1
    )                                                   AS actual_win_pct,
    ROUND(
        COUNT(CASE WHEN sel.result = 'win' THEN 1 END) * 100.0
        / NULLIF(COUNT(*), 0)
        - AVG(1.0 / bs.odds_at_place) * 100, 2
    )                                                   AS calibration_delta
FROM bet_selections bs
JOIN selections sel ON sel.selection_id = bs.selection_id
WHERE sel.result IS NOT NULL
GROUP BY odds_bracket
ORDER BY AVG(bs.odds_at_place);
