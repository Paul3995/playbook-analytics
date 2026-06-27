-- ============================================================
-- KPI: Player Retention & Churn
-- Day-1, Day-7, Day-30 retention cohorts
-- ============================================================

-- Cohort retention: % of players who return after first bet
WITH first_bet AS (
    SELECT
        user_id,
        MIN(DATE(placed_ts)) AS cohort_date
    FROM bets
    GROUP BY user_id
),
activity AS (
    SELECT DISTINCT
        b.user_id,
        DATE(b.placed_ts)   AS activity_date
    FROM bets b
),
cohort_activity AS (
    SELECT
        f.cohort_date,
        f.user_id,
        DATEDIFF(a.activity_date, f.cohort_date) AS days_since_first
    FROM first_bet f
    JOIN activity a ON a.user_id = f.user_id
)
SELECT
    cohort_date,
    COUNT(DISTINCT CASE WHEN days_since_first = 0  THEN user_id END) AS day_0,
    COUNT(DISTINCT CASE WHEN days_since_first = 1  THEN user_id END) AS retained_day_1,
    COUNT(DISTINCT CASE WHEN days_since_first = 7  THEN user_id END) AS retained_day_7,
    COUNT(DISTINCT CASE WHEN days_since_first = 30 THEN user_id END) AS retained_day_30,
    ROUND(
        COUNT(DISTINCT CASE WHEN days_since_first = 1  THEN user_id END) * 100.0
        / NULLIF(COUNT(DISTINCT CASE WHEN days_since_first = 0 THEN user_id END), 0), 1
    ) AS day_1_retention_pct,
    ROUND(
        COUNT(DISTINCT CASE WHEN days_since_first = 7  THEN user_id END) * 100.0
        / NULLIF(COUNT(DISTINCT CASE WHEN days_since_first = 0 THEN user_id END), 0), 1
    ) AS day_7_retention_pct,
    ROUND(
        COUNT(DISTINCT CASE WHEN days_since_first = 30 THEN user_id END) * 100.0
        / NULLIF(COUNT(DISTINCT CASE WHEN days_since_first = 0 THEN user_id END), 0), 1
    ) AS day_30_retention_pct
FROM cohort_activity
WHERE cohort_date >= :start_date
GROUP BY cohort_date
ORDER BY cohort_date;


-- 30-day rolling churn: players active in prior month but not current month
WITH monthly_active AS (
    SELECT
        DATE_FORMAT(placed_ts, '%Y-%m') AS yr_month,
        user_id
    FROM bets
    GROUP BY DATE_FORMAT(placed_ts, '%Y-%m'), user_id
)
SELECT
    curr.yr_month,
    COUNT(DISTINCT curr.user_id)                   AS active_players,
    COUNT(DISTINCT prev.user_id)                   AS prev_month_active,
    COUNT(DISTINCT CASE WHEN curr.user_id IS NULL
                        THEN prev.user_id END)      AS churned_players,
    ROUND(
        COUNT(DISTINCT CASE WHEN curr.user_id IS NULL
                            THEN prev.user_id END) * 100.0
        / NULLIF(COUNT(DISTINCT prev.user_id), 0), 1
    )                                              AS churn_rate_pct
FROM monthly_active curr
RIGHT JOIN monthly_active prev
    ON prev.user_id   = curr.user_id
   AND prev.yr_month  = DATE_FORMAT(DATE_SUB(STR_TO_DATE(CONCAT(curr.yr_month, '-01'), '%Y-%m-%d'), INTERVAL 1 MONTH), '%Y-%m')
GROUP BY curr.yr_month
ORDER BY curr.yr_month DESC;
