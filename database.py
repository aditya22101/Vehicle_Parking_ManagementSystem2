import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime

DATABASE = 'parking_system.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    
    # Create tables
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS parking_lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            total_slots INTEGER NOT NULL,
            price_per_hour REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP NULL
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS parking_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parking_lot_id INTEGER NOT NULL,
            slot_number INTEGER NOT NULL,
            status TEXT DEFAULT 'available',
            deleted_at TIMESTAMP NULL,
            FOREIGN KEY (parking_lot_id) REFERENCES parking_lots (id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            parking_lot_id INTEGER NOT NULL,
            slot_id INTEGER NOT NULL,
            vehicle_number TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP NOT NULL,
            total_cost REAL NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (parking_lot_id) REFERENCES parking_lots (id),
            FOREIGN KEY (slot_id) REFERENCES parking_slots (id)
        )
    ''')
    
    # Insert sample data if tables are empty
    cursor = conn.execute('SELECT COUNT(*) FROM parking_lots WHERE deleted_at IS NULL')
    if cursor.fetchone()[0] == 0:
        # Sample parking lots
        lots = [
            ('Downtown Plaza', 'Main Street, City Center', 25, 5.00),
            ('Shopping Mall', 'Mall Avenue, Shopping District', 30, 3.50),
            ('Airport Terminal', 'Airport Road, Terminal Building', 50, 8.00)
        ]
        
        for name, location, slots, price in lots:
            cursor = conn.execute('''
                INSERT INTO parking_lots (name, location, total_slots, price_per_hour)
                VALUES (?, ?, ?, ?)
            ''', (name, location, slots, price))
            
            lot_id = cursor.lastrowid
            
            # Create slots for each lot
            for slot_num in range(1, slots + 1):
                conn.execute('''
                    INSERT INTO parking_slots (parking_lot_id, slot_number, status)
                    VALUES (?, ?, 'available')
                ''', (lot_id, slot_num))
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def execute_query(query, params=None):
    conn = get_db()
    if params:
        result = conn.execute(query, params)
    else:
        result = conn.execute(query)
    conn.commit()
    data = result.fetchall()
    conn.close()
    return data

def execute_single(query, params=None):
    conn = get_db()
    if params:
        result = conn.execute(query, params)
    else:
        result = conn.execute(query)
    conn.commit()
    data = result.fetchone()
    conn.close()
    return data
