-- ============================================================
-- KPI: Bet Volume, Stakes & Margins by Sport / Market
-- ============================================================

-- Daily bet volume and stakes by sport
SELECT
    DATE(b.placed_ts)       AS bet_date,
    s.name                  AS sport,
    b.bet_type,
    COUNT(b.bet_id)         AS bet_count,
    COUNT(DISTINCT b.user_id) AS unique_bettors,
    ROUND(SUM(b.stake), 2)  AS total_stakes,
    ROUND(AVG(b.stake), 2)  AS avg_stake,
    ROUND(MAX(b.stake), 2)  AS max_stake
FROM bets b
JOIN bet_selections bs ON bs.bet_id = b.bet_id
JOIN selections sel    ON sel.selection_id = bs.selection_id
JOIN markets m         ON m.market_id = sel.market_id
JOIN events e          ON e.event_id  = m.event_id
JOIN competitions c    ON c.competition_id = e.competition_id
JOIN sports s          ON s.sport_id  = c.sport_id
WHERE b.placed_ts >= :start_date
  AND b.placed_ts <  :end_date
GROUP BY DATE(b.placed_ts), s.name, b.bet_type
ORDER BY bet_date DESC, total_stakes DESC;


-- Market margin (theoretical hold) by market type
SELECT
    m.market_type,
    COUNT(DISTINCT m.market_id)     AS markets_offered,
    COUNT(sel.selection_id)         AS selections,
    ROUND(
        AVG(1.0 / sel.odds) * 100, 2
    )                               AS avg_implied_prob_pct,
    ROUND(
        (AVG(1.0 / sel.odds) - (1.0 / COUNT(sel.selection_id))) * 100, 2
    )                               AS theoretical_margin_pct
FROM markets m
JOIN selections sel ON sel.market_id = m.market_id
GROUP BY m.market_type
ORDER BY theoretical_margin_pct DESC;
