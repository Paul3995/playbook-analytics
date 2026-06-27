-- ============================================================
-- KPI: Daily / Weekly / Monthly Active Players (DAP / WAP / MAP)
-- Active = placed at least one bet in the period
-- ============================================================

-- Daily Active Players (DAP)
SELECT
    DATE(placed_ts)         AS activity_date,
    COUNT(DISTINCT user_id) AS daily_active_players
FROM bets
WHERE
    placed_ts >= :start_date
    AND placed_ts < :end_date
GROUP BY DATE(placed_ts)
ORDER BY activity_date DESC;


-- Weekly Active Players (WAP) — ISO week
SELECT
    YEARWEEK(placed_ts, 3)          AS iso_year_week,
    MIN(DATE(placed_ts))            AS week_start,
    COUNT(DISTINCT user_id)         AS weekly_active_players
FROM bets
WHERE
    placed_ts >= :start_date
    AND placed_ts < :end_date
GROUP BY YEARWEEK(placed_ts, 3)
ORDER BY iso_year_week DESC;


-- Monthly Active Players (MAP)
SELECT
    DATE_FORMAT(placed_ts, '%Y-%m') AS year_month,
    COUNT(DISTINCT user_id)         AS monthly_active_players
FROM bets
WHERE
    placed_ts >= :start_date
    AND placed_ts < :end_date
GROUP BY DATE_FORMAT(placed_ts, '%Y-%m')
ORDER BY year_month DESC;
