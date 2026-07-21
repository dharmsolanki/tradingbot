from app.db import DatabaseManager

db = DatabaseManager()

db.execute("""
CREATE TABLE IF NOT EXISTS test(

    id INTEGER PRIMARY KEY,

    name TEXT

)
""")

db.execute("INSERT INTO test(name) VALUES(?)", ("Dharm",))

rows = db.fetchall("SELECT * FROM test")

print(rows)

db.close()
