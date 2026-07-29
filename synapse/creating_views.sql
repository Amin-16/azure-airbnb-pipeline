DROP VIEW IF EXISTS vw_fact_listing_snapshot;
CREATE VIEW vw_fact_listing_snapshot AS
SELECT *
FROM OPENROWSET(
    BULK 'fact_listing_snapshot/',
    DATA_SOURCE = 'gold_data_source',
    FORMAT = 'DELTA'
)
WITH (
    listing_id VARCHAR(50),
    host_id VARCHAR(50),
    neighbourhood_key BIGINT,
    room_type VARCHAR(50),
    accommodates INT,
    bedrooms INT,
    price FLOAT,
    number_of_reviews INT,
    has_reviews BIT,
    review_scores_rating FLOAT,
    host_is_superhost BIT,
    host_listings_count INT,
    city VARCHAR(50),
    quarter_label VARCHAR(20)
) AS result;
GO

DROP VIEW IF EXISTS vw_fact_calendar_availability;
CREATE VIEW vw_fact_calendar_availability AS
SELECT *
FROM OPENROWSET(
    BULK 'fact_calendar_availability/',
    DATA_SOURCE = 'gold_data_source',
    FORMAT = 'DELTA'
)
WITH (
    listing_id VARCHAR(50),
    date_key INT,
    available BIT,
    has_valid_availability BIT,
    minimum_nights INT,
    maximum_nights INT,
    has_nights_anomaly BIT,
    city VARCHAR(50),
    quarter_label VARCHAR(20)
) AS result;
GO

DROP VIEW IF EXISTS vw_dim_listing;
CREATE VIEW vw_dim_listing AS
SELECT *
FROM OPENROWSET(
    BULK 'dim_listing/',
    DATA_SOURCE = 'gold_data_source',
    FORMAT = 'DELTA'
)
WITH (
    listing_id VARCHAR(50),
    city VARCHAR(50),
    neighbourhood_key BIGINT,
    room_type VARCHAR(50),
    accommodates INT,
    bedrooms INT,
    effective_start_quarter VARCHAR(20),
    effective_end_quarter VARCHAR(20),
    is_current BIT
) AS result;
GO

DROP VIEW IF EXISTS vw_dim_host;
CREATE VIEW vw_dim_host AS
SELECT *
FROM OPENROWSET(
    BULK 'dim_host/',
    DATA_SOURCE = 'gold_data_source',
    FORMAT = 'DELTA'
)
WITH (
    host_id VARCHAR(50),
    city VARCHAR(50),
    host_is_superhost BIT,
    host_listings_count INT,
    effective_start_quarter VARCHAR(20),
    effective_end_quarter VARCHAR(20),
    is_current BIT
) AS result;
GO

 
CREATE VIEW vw_dim_neighbourhood AS
SELECT *
FROM OPENROWSET(
    BULK 'dim_neighbourhood/',
    DATA_SOURCE = 'gold_data_source',
    FORMAT = 'DELTA'
) AS result;
GO
 
CREATE VIEW vw_dim_date AS
SELECT *
FROM OPENROWSET(
    BULK 'dim_date/',
    DATA_SOURCE = 'gold_data_source',
    FORMAT = 'DELTA'
) AS result;
GO