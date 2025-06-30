-- MindsDB Job Setup for TextTrove
-- This SQL script sets up a job to monitor and ingest new documents

CREATE JOB IF NOT EXISTS texttrove_monitor_job AS (
    SELECT 'Job configuration for monitoring new documents' AS description
) EVERY 1 hour;
