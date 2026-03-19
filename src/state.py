import sqlite3

def get_db_connection():
    # In-memory DB, resets every time the proxy restarts
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mock_bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id TEXT,
            bid_amount REAL,
            status TEXT
        )
    ''')
    conn.commit()

# Initialize state globally for the proxy
db_conn = get_db_connection()
init_db(db_conn)