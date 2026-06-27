-- ============================================================
-- Analytics: Sport & Competition Performance
-- ============================================================

-- GGR and margin by sport (last 30 days)
SELECT
    s.name                                                           AS sport,
    COUNT(DISTINCT e.event_id)                                       AS events,
    COUNT(b.bet_id)                                                  AS bets,
    ROUND(SUM(b.stake), 2)                                           AS total_staked,
    ROUND(SUM(b.stake) - COALESCE(SUM(b.actual_payout), 0), 2)      AS ggr,
    ROUND(
        (SUM(b.stake) - COALESCE(SUM(b.actual_payout), 0))
        / NULLIF(SUM(b.stake), 0) * 100, 2
    )                                                                AS hold_pct,
    ROUND(AVG(b.stake), 2)                                           AS avg_stake
FROM bets b
JOIN bet_selections bs  ON bs.bet_id = b.bet_id
JOIN selections sel     ON sel.selection_id = bs.selection_id
JOIN markets m          ON m.market_id   = sel.market_id
JOIN events e           ON e.event_id    = m.event_id
JOIN competitions c     ON c.competition_id = e.competition_id
JOIN sports s           ON s.sport_id    = c.sport_id
WHERE b.status     IN ('won', 'lost')
  AND b.settled_ts >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY s.name
ORDER BY ggr DESC;


-- Top competitions by betting volume
SELECT
    s.name                          AS sport,
    c.name                          AS competition,
    c.country_code,
    COUNT(b.bet_id)                 AS bet_count,
    COUNT(DISTINCT b.user_id)       AS unique_bettors,
    ROUND(SUM(b.stake), 2)          AS total_staked
FROM bets b
JOIN bet_selections bs  ON bs.bet_id = b.bet_id
JOIN selections sel     ON sel.selection_id = bs.selection_id
JOIN markets m          ON m.market_id   = sel.market_id
JOIN events e           ON e.event_id    = m.event_id
JOIN competitions c     ON c.competition_id = e.competition_id
JOIN sports s           ON s.sport_id    = c.sport_id
WHERE b.placed_ts >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY s.name, c.name, c.country_code
ORDER BY total_staked DESC
LIMIT 20;


-- Live vs prematch bet split
SELECT
    CASE
        WHEN e.status = 'live' THEN 'in_play'
        ELSE 'prematch'
    END                             AS bet_category,
    COUNT(b.bet_id)                 AS bets,
    ROUND(SUM(b.stake), 2)          AS total_staked,
    ROUND(
        SUM(b.stake) / (SELECT SUM(stake) FROM bets WHERE placed_ts >= DATE_SUB(NOW(), INTERVAL 30 DAY)) * 100,
        1
    )                               AS pct_of_total_stakes
FROM bets b
JOIN bet_selections bs ON bs.bet_id = b.bet_id
JOIN selections sel    ON sel.selection_id = bs.selection_id
JOIN markets m         ON m.market_id = sel.market_id
JOIN events e          ON e.event_id  = m.event_id
WHERE b.placed_ts >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY bet_category;
