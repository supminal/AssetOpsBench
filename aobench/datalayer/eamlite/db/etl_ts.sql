-- 1) Create staging table
DROP TABLE IF EXISTS staging_assetmeters;
CREATE TABLE staging_assetmeters (
    asset_id TEXT,
    timestamp TEXT,
    condenser_water_return_to_tower_temperature TEXT,
    chiller_efficiency TEXT,
    tonnage TEXT,
    supply_temperature TEXT,
    return_temperature TEXT,
    condenser_water_flow TEXT,
    schedule TEXT,
    power_input TEXT,
    chiller_percent_loaded TEXT,
    liquid_refrigerant_evaporator_temperature TEXT,
    setpoint_temperature TEXT,
    run_status TEXT
);

-- 2) Load CSV into staging
COPY staging_assetmeters
FROM '/tmp/chiller_readings.csv'
WITH (FORMAT csv, HEADER true, DELIMITER E',');


-- 3) Insert/Upsert into assets
INSERT INTO assets (assetnum, description)
SELECT DISTINCT asset_id, ''
FROM staging_assetmeters
WHERE asset_id IS NOT NULL AND asset_id <> ''
ON CONFLICT (assetnum) DO NOTHING;


-- 4) Insert/Upsert into assetmeters
INSERT INTO assetmeters (assetid, metername, meterreading, readingdate)
SELECT 
    a.assetid,
    m.metername,
    m.reading::DECIMAL,
    s.timestamp::timestamp
FROM staging_assetmeters s
JOIN assets a ON a.assetnum = s.asset_id
CROSS JOIN LATERAL (
  VALUES
    ('condenser_water_return_to_tower_temperature', s.condenser_water_return_to_tower_temperature),
    ('chiller_efficiency', s.chiller_efficiency),
    ('tonnage', s.tonnage),
    ('supply_temperature', s.supply_temperature),
    ('return_temperature', s.return_temperature),
    ('condenser_water_flow', s.condenser_water_flow),
    ('schedule', s.schedule),
    ('power_input', s.power_input),
    ('chiller_percent_loaded', s.chiller_percent_loaded),
    ('liquid_refrigerant_evaporator_temperature', s.liquid_refrigerant_evaporator_temperature),
    ('setpoint_temperature', s.setpoint_temperature),
    ('run_status', s.run_status)
) AS m(metername, reading)
WHERE m.reading IS NOT NULL
  AND m.reading ~ '^-?[0-9]+(\.[0-9]+)?$'; -- only insert numeric readings
