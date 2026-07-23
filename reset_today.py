from app.db import DatabaseManager
from datetime import datetime

db = DatabaseManager(db_path="database/paper_trades.db")
today = datetime.now().strftime("%Y-%m-%d")
db.execute("DELETE FROM paper_trades WHERE entry_time LIKE ?", (today + "%",))
print("Done — today trades cleared")
