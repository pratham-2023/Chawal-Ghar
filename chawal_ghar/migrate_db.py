import sqlite3

DATABASE = 'database.db'

def add_cart_table():
    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
            c_id INTEGER NOT NULL,
            p_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (c_id) REFERENCES customers (c_id),
            FOREIGN KEY (p_id) REFERENCES products (p_id)
        );
        ''')
        print("Cart table created successfully.")
        conn.commit()
    except Exception as e:
        print(f"Error creating cart table: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    add_cart_table()
