from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this in production
DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form['role']
        fullname = request.form['fullname']
        loginname = request.form['loginname']
        password = request.form['password']
        email = request.form['email']
        
        if not role or not fullname or not loginname or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        db = get_db()
        
        try:
            if role == 'farmer':
                db.execute('INSERT INTO farmers (f_fullname, f_loginname, f_password, f_email) VALUES (?, ?, ?, ?)',
                           (fullname, loginname, hashed_password, email))
            elif role == 'customer':
                db.execute('INSERT INTO customers (c_fullname, c_loginname, c_password, c_email) VALUES (?, ?, ?, ?)',
                           (fullname, loginname, hashed_password, email))
            elif role == 'admin':
                db.execute('INSERT INTO admins (a_fullname, a_loginname, a_password, a_email) VALUES (?, ?, ?, ?)',
                           (fullname, loginname, hashed_password, email))
            
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash(f'Username {loginname} already exists.', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        loginname = request.form['loginname']
        password = request.form['password']
        
        db = get_db()
        user = None
        
        if role == 'farmer':
            user = db.execute('SELECT * FROM farmers WHERE f_loginname = ?', (loginname,)).fetchone()
            id_field = 'f_id'
            pass_field = 'f_password'
        elif role == 'customer':
            user = db.execute('SELECT * FROM customers WHERE c_loginname = ?', (loginname,)).fetchone()
            id_field = 'c_id'
            pass_field = 'c_password'
        elif role == 'admin':
            user = db.execute('SELECT * FROM admins WHERE a_loginname = ?', (loginname,)).fetchone()
            id_field = 'a_id'
            pass_field = 'a_password'
            
        if user and check_password_hash(user[pass_field], password):
            session.clear()
            session['user_id'] = user[id_field]
            session['role'] = role
            session['fullname'] = user[role[0] + '_fullname']
            
            if role == 'admin':
                return redirect(url_for('dashboard_admin'))
            elif role == 'farmer':
                return redirect(url_for('dashboard_farmer'))
            elif role == 'customer':
                return redirect(url_for('dashboard_customer'))
        
        flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# --- Farmer Product Routes ---

@app.route('/farmer/dashboard')
def dashboard_farmer():
    if session.get('role') != 'farmer':
        return redirect(url_for('login'))
    
    db = get_db()
    products = db.execute('SELECT * FROM products WHERE f_id = ?', (session['user_id'],)).fetchall()
    # Also show orders for this farmer's products
    orders = db.execute('''
        SELECT orders.*, products.p_name, customers.c_fullname 
        FROM orders 
        JOIN products ON orders.p_id = products.p_id 
        JOIN customers ON orders.c_id = customers.c_id
        WHERE products.f_id = ?
    ''', (session['user_id'],)).fetchall()
    
    return render_template('dashboard_farmer.html', products=products, orders=orders)

@app.route('/farmer/add_product', methods=['GET', 'POST'])
def add_product():
    if session.get('role') != 'farmer':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        p_name = request.form['p_name']
        p_type = request.form['p_type']
        p_quantity = request.form['p_quantity']
        p_priceperunit = request.form['p_priceperunit']
        p_batch = request.form['p_batch']
        p_status = 'Available'
        
        db = get_db()
        db.execute('INSERT INTO products (f_id, p_name, p_type, p_quantity, p_priceperunit, p_batch, p_status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (session['user_id'], p_name, p_type, p_quantity, p_priceperunit, p_batch, p_status))
        db.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('dashboard_farmer'))
        
    return render_template('add_product.html')

@app.route('/farmer/delete_product/<int:p_id>')
def delete_product(p_id):
    if session.get('role') != 'farmer':
        return redirect(url_for('login'))
        
    db = get_db()
    db.execute('DELETE FROM products WHERE p_id = ? AND f_id = ?', (p_id, session['user_id']))
    db.commit()
    flash('Product deleted.', 'success')
    return redirect(url_for('dashboard_farmer'))

# --- Customer Routes ---

@app.route('/customer/dashboard')
def dashboard_customer():
    if session.get('role') != 'customer':
        return redirect(url_for('login'))
        
    db = get_db()
    products = db.execute('SELECT products.*, farmers.f_fullname FROM products JOIN farmers ON products.f_id = farmers.f_id WHERE p_status = "Available"').fetchall()
    my_orders = db.execute('SELECT orders.*, products.p_name FROM orders JOIN products ON orders.p_id = products.p_id WHERE orders.c_id = ?', (session['user_id'],)).fetchall()
    return render_template('dashboard_customer.html', products=products, my_orders=my_orders)

@app.route('/customer/buy/<int:p_id>', methods=['GET', 'POST'])
def buy_product(p_id):
    if session.get('role') != 'customer':
        return redirect(url_for('login'))
    
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE p_id = ?', (p_id,)).fetchone()
    
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('dashboard_customer'))

    if request.method == 'POST':
        quantity = float(request.form['quantity'])
        destination = request.form['destination']
        payment_method = request.form['payment_method']
        
        if quantity > product['p_quantity']:
            flash(f'Only {product["p_quantity"]} kg available.', 'error')
            return redirect(url_for('buy_product', p_id=p_id))
        
        total_amount = quantity * product['p_priceperunit']
        
        # 1. Create Order
        cursor = db.execute('INSERT INTO orders (c_id, p_id, o_status, o_destination, o_amount) VALUES (?, ?, ?, ?, ?)',
                   (session['user_id'], p_id, 'Confirmed', destination, total_amount))
        o_id = cursor.lastrowid
        
        # 2. Create Payment
        db.execute('INSERT INTO payments (o_id, c_id, p_amount, p_method, p_status) VALUES (?, ?, ?, ?, ?)',
                   (o_id, session['user_id'], total_amount, payment_method, 'Completed'))
        
        # 3. Update Inventory
        new_quantity = product['p_quantity'] - quantity
        if new_quantity == 0:
            db.execute('UPDATE products SET p_quantity = ?, p_status = "Sold Out" WHERE p_id = ?', (new_quantity, p_id))
        else:
            db.execute('UPDATE products SET p_quantity = ? WHERE p_id = ?', (new_quantity, p_id))
            
        db.commit()
        flash('Order placed successfully!', 'success')
        return redirect(url_for('dashboard_customer'))

    return render_template('buy_product.html', product=product)

# --- Admin Routes ---

@app.route('/admin/dashboard')
def dashboard_admin():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    db = get_db()
    orders = db.execute('''
        SELECT orders.*, products.p_name, customers.c_fullname, farmers.f_fullname 
        FROM orders 
        JOIN products ON orders.p_id = products.p_id 
        JOIN customers ON orders.c_id = customers.c_id
        JOIN farmers ON products.f_id = farmers.f_id
    ''').fetchall()
    
    return render_template('dashboard_admin.html', orders=orders)

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        import database
        database.init_db()
    app.run(debug=True)
