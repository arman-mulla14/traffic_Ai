import sqlite3

def run():
    conn = sqlite3.connect('traffic_system.db')
    c = conn.cursor()

    # 1. Update traffic_records table columns
    cols_tr = [col[1] for col in c.execute('PRAGMA table_info(traffic_records)')]
    if 'camera_id' not in cols_tr:
        c.execute('ALTER TABLE traffic_records ADD COLUMN camera_id INTEGER;')
        print('Added camera_id to traffic_records')
    if 'road_name' not in cols_tr:
        c.execute('ALTER TABLE traffic_records ADD COLUMN road_name TEXT;')
        print('Added road_name to traffic_records')

    # 2. Update incidents table columns
    cols_inc = [col[1] for col in c.execute('PRAGMA table_info(incidents)')]
    if 'camera_id' not in cols_inc:
        c.execute('ALTER TABLE incidents ADD COLUMN camera_id INTEGER;')
        print('Added camera_id to incidents')
    if 'road_name' not in cols_inc:
        c.execute('ALTER TABLE incidents ADD COLUMN road_name TEXT;')
        print('Added road_name to incidents')

    conn.commit()

    # 3. Populate existing rows based on analysis_id mapping
    road_mapping = {
        18: (1, 'North Approach (Road 1 - Nort NH4)'),
        19: (2, 'South Approach (Road 2 - South NH4)'),
        2:  (3, 'East Approach (Road 3 - East NH4)'),
        14: (3, 'East Approach (Road 3 - East NH4)'),
        17: (3, 'East Approach (Road 3 - East NH4)'),
        8:  (4, 'West Approach (Road 4 - West NH4)'),
        9:  (4, 'West Approach (Road 4 - West NH4)'),
        15: (4, 'West Approach (Road 4 - West NH4)'),
        16: (4, 'West Approach (Road 4 - West NH4)')
    }

    for aid, (cam_id, rname) in road_mapping.items():
        c.execute('UPDATE traffic_records SET camera_id = ?, road_name = ? WHERE analysis_id = ?', (cam_id, rname, aid))
        c.execute('UPDATE incidents SET camera_id = ?, road_name = ? WHERE analysis_id = ?', (cam_id, rname, aid))

    # For any unassigned
    c.execute("""
        UPDATE traffic_records 
        SET camera_id = ((analysis_id % 4) + 1),
            road_name = CASE ((analysis_id % 4) + 1)
                WHEN 1 THEN 'North Approach (Road 1 - Nort NH4)'
                WHEN 2 THEN 'South Approach (Road 2 - South NH4)'
                WHEN 3 THEN 'East Approach (Road 3 - East NH4)'
                ELSE 'West Approach (Road 4 - West NH4)'
            END
        WHERE camera_id IS NULL;
    """)

    c.execute("""
        UPDATE incidents 
        SET camera_id = ((analysis_id % 4) + 1),
            road_name = CASE ((analysis_id % 4) + 1)
                WHEN 1 THEN 'North Approach (Road 1 - Nort NH4)'
                WHEN 2 THEN 'South Approach (Road 2 - South NH4)'
                WHEN 3 THEN 'East Approach (Road 3 - East NH4)'
                ELSE 'West Approach (Road 4 - West NH4)'
            END
        WHERE camera_id IS NULL;
    """)

    conn.commit()

    print('Updated records count per camera:')
    for r in c.execute('SELECT camera_id, road_name, COUNT(*) FROM traffic_records GROUP BY camera_id'):
        print(r)
    print('Updated incidents count per camera:')
    for r in c.execute('SELECT camera_id, road_name, COUNT(*) FROM incidents GROUP BY camera_id'):
        print(r)
    conn.close()

if __name__ == '__main__':
    run()
