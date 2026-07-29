
-- 1. Average price by neighbourhood, per city, per snapshot
CREATE VIEW vw_avg_price_by_neighbourhood AS
SELECT
    n.city,
    n.neighbourhood_name,
    f.quarter_label,
    COUNT(*) AS listing_count,
    AVG(f.price) AS avg_price,
    AVG(CASE WHEN f.room_type = 'Entire place' THEN f.price END) AS avg_price_entire_place,
    AVG(CASE WHEN f.room_type = 'Private room' THEN f.price END) AS avg_price_private_room
FROM vw_fact_listing_snapshot f
JOIN vw_dim_neighbourhood n ON f.neighbourhood_key = n.neighbourhood_key
WHERE f.price IS NOT NULL
GROUP BY n.city, n.neighbourhood_name, f.quarter_label;
GO
 
-- 2. Superhost status changes — the flagship SCD2 query, exposed for Power BI
CREATE VIEW vw_superhost_status_changes AS
SELECT
    old_h.host_id,
    old_h.city,
    old_h.host_is_superhost AS previous_status,
    new_h.host_is_superhost AS current_status,
    old_h.effective_start_quarter AS previous_status_as_of,
    new_h.effective_start_quarter AS current_status_as_of,
    CASE
        WHEN old_h.host_is_superhost = 1 AND new_h.host_is_superhost = 0 THEN 'LOST_SUPERHOST'
        WHEN old_h.host_is_superhost = 0 AND new_h.host_is_superhost = 1 THEN 'GAINED_SUPERHOST'
        ELSE 'OTHER_CHANGE'
    END AS change_type
FROM vw_dim_host old_h
JOIN vw_dim_host new_h
    ON old_h.host_id = new_h.host_id
    AND old_h.city = new_h.city
    AND old_h.is_current = 0
    AND new_h.is_current = 1
WHERE old_h.host_is_superhost <> new_h.host_is_superhost;
GO
 
-- 3. Occupancy rate by city and quarter
CREATE VIEW vw_occupancy_rate_by_city AS
SELECT
    city,
    quarter_label,
    COUNT(*) AS total_listing_days,
    SUM(CASE WHEN available = 0 THEN 1 ELSE 0 END) AS booked_days,
    CAST(SUM(CASE WHEN available = 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS occupancy_rate
FROM vw_fact_calendar_availability
WHERE has_valid_availability = 1
GROUP BY city, quarter_label;
GO
 
-- 4. Room type mix by city
CREATE VIEW vw_room_type_mix_by_city AS
SELECT
    city,
    quarter_label,
    room_type,
    COUNT(*) AS listing_count,
    CAST(COUNT(*) AS FLOAT) / SUM(COUNT(*)) OVER (PARTITION BY city, quarter_label) AS pct_of_city_listings
FROM vw_fact_listing_snapshot
GROUP BY city, quarter_label, room_type;
GO
 
-- 5. Top 10 neighbourhoods by listing count, per city (market concentration)
CREATE VIEW vw_top_neighbourhoods_by_listing_count AS
SELECT city, neighbourhood_name, quarter_label, listing_count, rnk
FROM (
    SELECT
        n.city,
        n.neighbourhood_name,
        f.quarter_label,
        COUNT(*) AS listing_count,
        RANK() OVER (PARTITION BY n.city, f.quarter_label ORDER BY COUNT(*) DESC) AS rnk
    FROM vw_fact_listing_snapshot f
    JOIN vw_dim_neighbourhood n ON f.neighbourhood_key = n.neighbourhood_key
    GROUP BY n.city, n.neighbourhood_name, f.quarter_label
) ranked
WHERE rnk <= 10;
GO
 
-- 6. Cross-city summary comparison (Barcelona vs Lisbon, latest quarter)
CREATE VIEW vw_city_comparison_summary AS
SELECT
    f.city,
    f.quarter_label,
    COUNT(*) AS total_listings,
    AVG(f.price) AS avg_price,
    SUM(CASE WHEN f.host_is_superhost = 1 THEN 1 ELSE 0 END) AS superhost_count,
    CAST(SUM(CASE WHEN f.host_is_superhost = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS superhost_pct,
    AVG(f.review_scores_rating) AS avg_review_score
FROM vw_fact_listing_snapshot f
GROUP BY f.city, f.quarter_label;
GO