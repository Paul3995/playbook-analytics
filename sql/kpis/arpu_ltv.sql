-- ============================================================
-- KPI: ARPU (Average Revenue Per User) & Player LTV
-- ============================================================

-- Monthly ARPU
WITH monthly_ggr AS (
    SELECT
        DATE_FORMAT(settled_ts, '%Y-%m')    AS yr_month,
        user_id,
        SUM(stake) - COALESCE(SUM(actual_payout), 0) AS player_ggr
    FROM bets
    WHERE status IN ('won', 'lost')
    GROUP BY DATE_FORMAT(settled_ts, '%Y-%m'), user_id
),
monthly_active AS (
    SELECT
        DATE_FORMAT(placed_ts, '%Y-%m')     AS yr_month,
        COUNT(DISTINCT user_id)             AS active_players
    FROM bets
    GROUP BY DATE_FORMAT(placed_ts, '%Y-%m')
)
SELECT
    g.yr_month,
    ma.active_players,
    ROUND(SUM(g.player_ggr), 2)                                 AS total_ggr,
    ROUND(SUM(g.player_ggr) / NULLIF(ma.active_players, 0), 2)  AS arpu
FROM monthly_ggr g
JOIN monthly_active ma ON ma.yr_month = g.yr_month
GROUP BY g.yr_month, ma.active_players
ORDER BY g.yr_month DESC;


-- Player Lifetime Value (LTV) — cumulative GGR per player since registration
SELECT
    u.user_id,
    u.username,
    u.country_code,
    u.vip_tier,
    u.registration_ts,
    DATEDIFF(NOW(), u.registration_ts)                              AS days_active,
    COUNT(b.bet_id)                                                 AS total_bets,
    ROUND(SUM(b.stake), 2)                                          AS total_staked,
    ROUND(SUM(b.stake) - COALESCE(SUM(b.actual_payout), 0), 2)     AS lifetime_ggr,
    ROUND(
        (SUM(b.stake) - COALESCE(SUM(b.actual_payout), 0))
        / NULLIF(DATEDIFF(NOW(), u.registration_ts), 0), 2
    )                                                               AS daily_ggr_rate
FROM users u
LEFT JOIN bets b ON b.user_id = u.user_id AND b.status IN ('won', 'lost')
GROUP BY
    u.user_id, u.username, u.country_code, u.vip_tier, u.registration_ts
ORDER BY lifetime_ggr DESC;
