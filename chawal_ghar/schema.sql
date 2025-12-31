DROP TABLE IF EXISTS admins;
DROP TABLE IF EXISTS farmers;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS cart;

CREATE TABLE cart (
    cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
    c_id INTEGER NOT NULL,
    p_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (c_id) REFERENCES customers (c_id),
    FOREIGN KEY (p_id) REFERENCES products (p_id)
);

CREATE TABLE admins (
    a_id INTEGER PRIMARY KEY AUTOINCREMENT,
    a_fullname TEXT NOT NULL,
    a_loginname TEXT UNIQUE NOT NULL,
    a_password TEXT NOT NULL,
    a_gender TEXT,
    a_contact TEXT,
    a_email TEXT,
    a_address TEXT
);

CREATE TABLE farmers (
    f_id INTEGER PRIMARY KEY AUTOINCREMENT,
    f_fullname TEXT NOT NULL,
    f_loginname TEXT UNIQUE NOT NULL,
    f_password TEXT NOT NULL,
    f_gender TEXT,
    f_contact TEXT,
    f_email TEXT,
    f_address TEXT
);

CREATE TABLE customers (
    c_id INTEGER PRIMARY KEY AUTOINCREMENT,
    c_fullname TEXT NOT NULL,
    c_loginname TEXT UNIQUE NOT NULL,
    c_password TEXT NOT NULL,
    c_gender TEXT,
    c_contact TEXT,
    c_email TEXT,
    c_address TEXT
);

CREATE TABLE products (
    p_id INTEGER PRIMARY KEY AUTOINCREMENT,
    f_id INTEGER NOT NULL,
    p_name TEXT NOT NULL,
    p_type TEXT NOT NULL,
    p_quantity INTEGER NOT NULL,
    p_status TEXT,
    p_priceperunit REAL NOT NULL,
    p_batch TEXT,
    FOREIGN KEY (f_id) REFERENCES farmers (f_id)
);

CREATE TABLE orders (
    o_id INTEGER PRIMARY KEY AUTOINCREMENT,
    c_id INTEGER NOT NULL,
    p_id INTEGER NOT NULL,
    o_date TEXT DEFAULT CURRENT_TIMESTAMP,
    o_status TEXT DEFAULT 'Pending',
    o_destination TEXT,
    o_amount REAL NOT NULL,
    FOREIGN KEY (c_id) REFERENCES customers (c_id),
    FOREIGN KEY (p_id) REFERENCES products (p_id)
);

CREATE TABLE payments (
    pay_id INTEGER PRIMARY KEY AUTOINCREMENT,
    o_id INTEGER NOT NULL,
    c_id INTEGER NOT NULL,
    p_amount REAL NOT NULL,
    p_date TEXT DEFAULT CURRENT_TIMESTAMP,
    p_method TEXT,
    p_status TEXT DEFAULT 'Completed',
    FOREIGN KEY (o_id) REFERENCES orders (o_id),
    FOREIGN KEY (c_id) REFERENCES customers (c_id)
);
