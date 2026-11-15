import sqlite3

def migrate():
    conn = sqlite3.connect("traffic_system.db")
    c = conn.cursor()

    columns_to_add = [
        ("road_name", "VARCHAR(150)"),
        ("direction", "VARCHAR(50) DEFAULT 'Northbound'"),
        ("speed_limit", "INTEGER DEFAULT 60")
    ]

    c.execute("PRAGMA table_info(cameras)")
    existing_cols = [r[1] for r in c.fetchall()]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            c.execute(f"ALTER TABLE cameras ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to cameras")

    c.execute("UPDATE cameras SET road_name = 'North Approach (Road 1 - Nort NH4)', direction = 'Northbound', speed_limit = 60 WHERE id = 1")
    c.execute("UPDATE cameras SET road_name = 'South Approach (Road 2 - South NH4)', direction = 'Southbound', speed_limit = 60 WHERE id = 2")
    c.execute("UPDATE cameras SET road_name = 'East Approach (Road 3 - East NH4)', direction = 'Eastbound', speed_limit = 50 WHERE id = 3")
    c.execute("UPDATE cameras SET road_name = 'West Approach (Road 4 - West NH4)', direction = 'Westbound', speed_limit = 50 WHERE id = 4")
    conn.commit()

    c.execute("SELECT id, camera_name, road_name, direction, speed_limit FROM cameras")
    for r in c.fetchall():
        print("Camera:", r)

    conn.close()

if __name__ == "__main__":
    migrate()
