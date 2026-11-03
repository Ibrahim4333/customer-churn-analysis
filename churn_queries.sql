
-- Churn analysis queries (SQLite syntax; table: customers, built by 01_cleaning.py)
-- Open data/churn.db in DB Browser for SQLite, or run via Python's sqlite3.
-- churn_value: 1 = churned, 0 = stayed

-- Q1. Overall churn rate and customer base
SELECT
    COUNT(*)                                          AS total_customers,
    SUM(churn_value)                                  AS churned_customers,
    ROUND(100.0 * SUM(churn_value) / COUNT(*), 1)     AS churn_rate_pct
FROM customers;

-- Q2. Churn rate by contract type
SELECT
    contract,
    COUNT(*)                                          AS customers,
    SUM(churn_value)                                  AS churned,
    ROUND(100.0 * SUM(churn_value) / COUNT(*), 1)     AS churn_rate_pct
FROM customers
GROUP BY contract
ORDER BY churn_rate_pct DESC;

-- Q3. Churn rate by tenure bucket (when do customers leave?)
SELECT
    tenure_bucket,
    COUNT(*)                                          AS customers,
    ROUND(100.0 * SUM(churn_value) / COUNT(*), 1)     AS churn_rate_pct
FROM customers
GROUP BY tenure_bucket
ORDER BY MIN(tenure_months);

-- Q4. Churn by payment method and internet service
SELECT
    payment_method,
    internet_service,
    COUNT(*)                                          AS customers,
    ROUND(100.0 * SUM(churn_value) / COUNT(*), 1)     AS churn_rate_pct
FROM customers
GROUP BY payment_method, internet_service
HAVING COUNT(*) >= 50                                 -- ignore tiny groups
ORDER BY churn_rate_pct DESC;

-- Q5. Monthly revenue lost to churn
SELECT
    ROUND(SUM(CASE WHEN churn_value = 1 THEN monthly_charges END), 0)  AS monthly_revenue_lost,
    ROUND(SUM(monthly_charges), 0)                                     AS total_monthly_revenue,
    ROUND(100.0 * SUM(CASE WHEN churn_value = 1 THEN monthly_charges END)
          / SUM(monthly_charges), 1)                                   AS pct_of_revenue_lost
FROM customers;

-- Q6. Lifetime value lost to churned customers, by contract type
SELECT
    contract,
    SUM(churn_value)                                  AS churned_customers,
    ROUND(SUM(CASE WHEN churn_value = 1 THEN cltv END), 0)  AS cltv_lost
FROM customers
GROUP BY contract
ORDER BY cltv_lost DESC;

-- Q7. Top churn reasons (only churned customers have a reason)
SELECT
    TOP 10
    churn_reason,
    COUNT(*)                                          AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_churners
FROM customers
WHERE churn_value = 1
GROUP BY churn_reason
ORDER BY customers DESC
;

-- Q8. High-risk segment: month-to-month, first-year, fiber optic
SELECT
    COUNT(*)                                          AS customers,
    ROUND(100.0 * SUM(churn_value) / COUNT(*), 1)     AS churn_rate_pct,
    ROUND(AVG(monthly_charges), 2)                    AS avg_monthly_charge
FROM customers
WHERE contract = 'Month-to-month'
  AND tenure_months <= 12
  AND internet_service = 'Fiber optic';

-- Q9. Do add-on services reduce churn? (tech support and online security)
SELECT
    tech_support,
    online_security,
    COUNT(*)                                          AS customers,
    ROUND(100.0 * SUM(churn_value) / COUNT(*), 1)     AS churn_rate_pct
FROM customers
WHERE internet_service <> 'No'
GROUP BY tech_support, online_security
ORDER BY churn_rate_pct DESC;

-- Q10. Share of all churn that comes from the high-risk segment
WITH seg AS (
    SELECT * FROM customers
    WHERE contract = 'Month-to-month' AND tenure_months <= 12
)
SELECT
    ROUND(100.0 * SUM(seg.churn_value) / (SELECT SUM(churn_value) FROM customers), 1)
        AS pct_of_all_churn_from_new_month_to_month
FROM seg;