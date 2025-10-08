-- === SITES ===
INSERT INTO sites(sitenum, name, address)
VALUES
    ('MAIN', 'Main Facility', '123 Industrial Ave'),
('WEST', 'West Campus', '456 West St'),
('EAST', 'East Plant', '789 East Blvd')
ON CONFLICT (sitenum)
    DO NOTHING;

-- === LOCATIONS ===
INSERT INTO locations(locationnum, description, siteid, locationtype)
SELECT
    'MAIN-CHILLER-ROOM',
    'Chiller room for Main site',
    siteid,
    'Room'
FROM
    sites
WHERE
    sitenum = 'MAIN'
ON CONFLICT (locationnum)
    DO NOTHING;

INSERT INTO locations(locationnum, description, siteid, locationtype)
SELECT
    'WEST-MECH-ROOM',
    'Mechanical room for West Campus',
    siteid,
    'Room'
FROM
    sites
WHERE
    sitenum = 'WEST'
ON CONFLICT (locationnum)
    DO NOTHING;

INSERT INTO locations(locationnum, description, siteid, locationtype)
SELECT
    'EAST-PLANT-A',
    'Main plant building at East site',
    siteid,
    'Building'
FROM
    sites
WHERE
    sitenum = 'EAST'
ON CONFLICT (locationnum)
    DO NOTHING;

-- Keep Chiller 6 fixed at MAIN
UPDATE
    assets
SET
    locationid =(
        SELECT
            locationid
        FROM
            locations
        WHERE
            siteid =(
                SELECT
                    siteid
                FROM
                    sites
                WHERE
                    sitenum = 'MAIN')
            LIMIT 1)
WHERE
    assetnum = 'Chiller 6';

-- Randomly assign all other assets to any site
UPDATE
    assets a
SET
    locationid = l.locationid
FROM
    LATERAL (
        SELECT
            loc.locationid
        FROM
            locations loc
            JOIN sites s ON loc.siteid = s.siteid
        WHERE
            s.sitenum <> 'MAIN'
        ORDER BY
            random()
        LIMIT 1) l
WHERE
    a.assetnum <> 'Chiller 6';
