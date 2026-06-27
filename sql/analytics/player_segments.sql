-- ============================================================
-- Analytics: Player Segmentation (RFM & Value Tiers)
-- Recency / Frequency / Monetary analysis
-- ============================================================

WITH rfm_base AS (
    SELECT
        user_id,
        DATEDIFF(NOW(), MAX(placed_ts))     AS recency_days,
        COUNT(bet_id)                        AS frequency,
        SUM(stake)                           AS monetary
    FROM bets
    WHERE placed_ts >= DATE_SUB(NOW(), INTERVAL 90 DAY)
    GROUP BY user_id
),
rfm_scored AS (
    SELECT
        user_id,
        recency_days,
        frequency,
        ROUND(monetary, 2)                  AS monetary,
        NTILE(5) OVER (ORDER BY recency_days ASC)   AS r_score,   -- 5 = most recent
        NTILE(5) OVER (ORDER BY frequency   DESC)   AS f_score,
        NTILE(5) OVER (ORDER BY monetary    DESC)   AS m_score
    FROM rfm_base
)
SELECT
    user_id,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    (r_score + f_score + m_score)       AS rfm_total,
    CASE
        WHEN (r_score + f_score + m_score) >= 13 THEN 'Champions'
        WHEN (r_score + f_score + m_score) >= 10 THEN 'Loyal Players'
        WHEN r_score >= 4 AND f_score >= 3       THEN 'Potential Loyalists'
        WHEN r_score >= 4 AND f_score < 3        THEN 'New Players'
        WHEN r_score <= 2 AND f_score >= 4       THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2       THEN 'Churned'
        ELSE 'Occasional'
    END                                 AS segment
FROM rfm_scored
ORDER BY rfm_total DESC;


-- Segment summary for reporting
WITH rfm_base AS (
    SELECT
        user_id,
        DATEDIFF(NOW(), MAX(placed_ts))     AS recency_days,
        COUNT(bet_id)                        AS frequency,
        SUM(stake)                           AS monetary
    FROM bets
    WHERE placed_ts >= DATE_SUB(NOW(), INTERVAL 90 DAY)
    GROUP BY user_id
),
rfm_scored AS (
    SELECT
        user_id, recency_days, frequency, monetary,
        NTILE(5) OVER (ORDER BY recency_days ASC)  AS r_score,
        NTILE(5) OVER (ORDER BY frequency DESC)    AS f_score,
        NTILE(5) OVER (ORDER BY monetary DESC)     AS m_score
    FROM rfm_base
),
segmented AS (
    SELECT *,
        CASE
            WHEN (r_score + f_score + m_score) >= 13 THEN 'Champions'
            WHEN (r_score + f_score + m_score) >= 10 THEN 'Loyal Players'
            WHEN r_score >= 4 AND f_score >= 3       THEN 'Potential Loyalists'
            WHEN r_score >= 4 AND f_score < 3        THEN 'New Players'
            WHEN r_score <= 2 AND f_score >= 4       THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2       THEN 'Churned'
            ELSE 'Occasional'
        END AS segment
    FROM rfm_scored
)
SELECT
    segment,
    COUNT(*)                            AS player_count,
    ROUND(AVG(recency_days), 1)         AS avg_recency_days,
    ROUND(AVG(frequency), 1)            AS avg_bets,
    ROUND(AVG(monetary), 2)             AS avg_spend,
    ROUND(SUM(monetary), 2)             AS total_spend,
    ROUND(SUM(monetary) / (SELECT SUM(monetary) FROM rfm_base) * 100, 1) AS pct_revenue
FROM segmented
GROUP BY segment
ORDER BY total_spend DESC;
