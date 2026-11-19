import sqlite3

conn = sqlite3.connect('traffic_system.db')
c = conn.cursor()

# 1. Create streets table if not exists
c.execute("""
CREATE TABLE IF NOT EXISTS streets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL UNIQUE,
    location VARCHAR(255),
    description VARCHAR(255),
    speed_limit INTEGER DEFAULT 60,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# 2. Check if street_name column exists in cameras
c.execute("PRAGMA table_info(cameras)")
cols = [col[1] for col in c.fetchall()]
if 'street_name' not in cols:
    c.execute("ALTER TABLE cameras ADD COLUMN street_name VARCHAR(150)")
    print("Added street_name column to cameras table.")
else:
    print("street_name column already exists in cameras table.")

# 3. Insert default streets if not exists
c.execute("SELECT COUNT(id) FROM streets")
count = c.fetchone()[0]
if count == 0:
    c.execute("""
    INSERT INTO streets (name, location, description, speed_limit)
    VALUES 
    ('Gandhi Chowk', 'Kodoli', 'Major 4-way intersection grouping all 4 NH4 approach roads', 60),
    ('MG Road Express Corridor', 'Downtown Sector 2', 'High-speed urban arterial corridor', 65)
    """)
    print("Inserted initial streets.")

# 4. Assign cameras to default streets
# Camera 1-4 belong to Gandhi Chowk
c.execute("""
UPDATE cameras 
SET street_name = 'Gandhi Chowk'
WHERE id IN (1, 2, 3, 4)
""")

# Camera 5 & 6 belong to MG Road Express Corridor
c.execute("""
UPDATE cameras 
SET street_name = 'MG Road Express Corridor'
WHERE id IN (5, 6)
""")

conn.commit()

c.execute("SELECT id, name, location FROM streets")
print("Streets:", c.fetchall())

c.execute("SELECT id, camera_name, road_name, street_name FROM cameras")
for row in c.fetchall():
    print("Cam:", row)

conn.close()
