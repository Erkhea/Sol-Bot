import sqlite3
from .config import DB_PATH

def connect():
    db = sqlite3.connect(DB_PATH)
    db.execute("""CREATE TABLE IF NOT EXISTS guild_settings (guild_id TEXT PRIMARY KEY, alert_channel_id TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS watched (
        address TEXT PRIMARY KEY, added_by TEXT, last_score INTEGER,
        last_verdict TEXT, last_price REAL, last_liquidity REAL, last_change REAL
    )""")
    db.commit()
    return db

def add_watch(address, user):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO watched(address, added_by) VALUES(?, ?)", (address, user))

def remove_watch(address):
    with connect() as db:
        cur = db.execute("DELETE FROM watched WHERE address=?", (address,))
        return cur.rowcount > 0

def list_watched():
    with connect() as db:
        return db.execute("SELECT address, last_score, last_verdict, last_price, last_liquidity FROM watched ORDER BY address").fetchall()

def get_watched():
    with connect() as db:
        return db.execute("SELECT address, last_score, last_verdict, last_price, last_liquidity, last_change FROM watched").fetchall()

def update_watch(address, score, verdict, price, liquidity, change):
    with connect() as db:
        db.execute("""UPDATE watched SET last_score=?, last_verdict=?, last_price=?,
            last_liquidity=?, last_change=? WHERE address=?""",
            (score, verdict, price, liquidity, change, address))


def set_alert_channel(guild_id, channel_id):
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO guild_settings(guild_id, alert_channel_id) VALUES(?, ?)",
                   (str(guild_id), str(channel_id)))

def get_alert_channel(guild_id):
    with connect() as db:
        row = db.execute("SELECT alert_channel_id FROM guild_settings WHERE guild_id=?",
                         (str(guild_id),)).fetchone()
        return row[0] if row else None
