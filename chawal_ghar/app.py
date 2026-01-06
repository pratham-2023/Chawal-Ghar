from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
import razorpay

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chawal_ghar_secret_key_2025')
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
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        gender = request.form['gender']
        contact = request.form['contact']
        address = request.form['address']
        email = request.form['email']
        loginname = request.form['loginname']
        password = request.form['password']
        
        if not role or not firstname or not lastname or not loginname or not password:
            flash('All required fields must be filled.', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        db = get_db()
        
        try:
            if role == 'farmer':
                db.execute('INSERT INTO farmers (f_firstname, f_lastname, f_gender, f_contact, f_address, f_email, f_loginname, f_password) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                           (firstname, lastname, gender, contact, address, email, loginname, hashed_password))
            elif role == 'customer':
                db.execute('INSERT INTO customers (c_firstname, c_lastname, c_gender, c_contact, c_address, c_email, c_loginname, c_password) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                           (firstname, lastname, gender, contact, address, email, loginname, hashed_password))
            elif role == 'admin':
                db.execute('INSERT INTO admins (a_firstname, a_lastname, a_gender, a_contact, a_address, a_email, a_loginname, a_password) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                           (firstname, lastname, gender, contact, address, email, loginname, hashed_password))
            
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
            session['fullname'] = user[role[0] + '_firstname'] + ' ' + user[role[0] + '_lastname']
            
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
        SELECT orders.*, products.p_name, customers.c_firstname, customers.c_lastname
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
    
    # Get rice type from query parameter if provided
    rice_type = request.args.get('rice_type', '')
    
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
        
    return render_template('add_product.html', rice_type=rice_type)

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
    products = db.execute('SELECT products.*, farmers.f_firstname, farmers.f_lastname FROM products JOIN farmers ON products.f_id = farmers.f_id WHERE p_status = "Available"').fetchall()
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
        # This handles the payment success callback
        quantity = float(request.form['quantity'])
        destination = request.form['destination']
        
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
                   (o_id, session['user_id'], total_amount, 'Online (Razorpay)', 'Completed'))
        
        # 3. Update Inventory
        new_quantity = product['p_quantity'] - quantity
        if new_quantity <= 0:
            db.execute('UPDATE products SET p_quantity = 0, p_status = "Sold Out" WHERE p_id = ?', (p_id,))
        else:
            db.execute('UPDATE products SET p_quantity = ? WHERE p_id = ?', (new_quantity, p_id))
            
        db.commit()
        flash('Payment successful! Order placed.', 'success')
        return redirect(url_for('dashboard_customer'))
    
    customer = db.execute('SELECT * FROM customers WHERE c_id = ?', (session['user_id'],)).fetchone()

    # GET request - Create Razorpay order for payment
    initial_amount = product['p_priceperunit']
    data = { "amount": int(initial_amount * 100), "currency": "INR", "receipt": f"buy_rcpt_{p_id}" }
    payment = client.order.create(data=data)

    return render_template('buy_product.html', product=product, payment=payment, key_id=KEY_ID, customer=customer)

# --- Admin Routes ---

@app.route('/admin/dashboard')
def dashboard_admin():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    db = get_db()
    orders = db.execute('''
        SELECT orders.*, products.p_name, customers.c_firstname, customers.c_lastname, farmers.f_firstname, farmers.f_lastname
        FROM orders 
        JOIN products ON orders.p_id = products.p_id 
        JOIN customers ON orders.c_id = customers.c_id
        JOIN farmers ON products.f_id = farmers.f_id
    ''').fetchall()
    
    return render_template('dashboard_admin.html', orders=orders)

@app.route('/admin/profile', methods=['GET', 'POST'])
def admin_profile():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    db = get_db()
    
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        contact = request.form['contact']
        email = request.form['email']
        address = request.form['address']
        gender = request.form['gender']
        
        db.execute('UPDATE admins SET a_firstname = ?, a_lastname = ?, a_contact = ?, a_email = ?, a_address = ?, a_gender = ? WHERE a_id = ?',
                   (firstname, lastname, contact, email, address, gender, session['user_id']))
        db.commit()
        session['fullname'] = firstname + ' ' + lastname # Update session fullname
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('admin_profile'))
        
    admin = db.execute('SELECT * FROM admins WHERE a_id = ?', (session['user_id'],)).fetchone()
    return render_template('admin_profile.html', admin=admin)

@app.route('/admin/customers')
def admin_customers():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    db = get_db()
    customers = db.execute('SELECT * FROM customers').fetchall()
    return render_template('admin_customers.html', customers=customers)

@app.route('/admin/customer/edit/<int:c_id>', methods=['GET', 'POST'])
def admin_edit_customer(c_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    db = get_db()
    
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        contact = request.form['contact']
        address = request.form['address']
        gender = request.form['gender']
        
        db.execute('UPDATE customers SET c_firstname = ?, c_lastname = ?, c_email = ?, c_contact = ?, c_address = ?, c_gender = ? WHERE c_id = ?',
                   (firstname, lastname, email, contact, address, gender, c_id))
        db.commit()
        flash('Customer updated successfully.', 'success')
        return redirect(url_for('admin_customers'))
        
    customer = db.execute('SELECT * FROM customers WHERE c_id = ?', (c_id,)).fetchone()
    if not customer:
         flash('Customer not found.', 'error')
         return redirect(url_for('admin_customers'))

    return render_template('admin_edit_customer.html', customer=customer)

@app.route('/admin/customer/delete/<int:c_id>')
def admin_delete_customer(c_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    db = get_db()
    db.execute('DELETE FROM customers WHERE c_id = ?', (c_id,))
    db.commit()
    flash('Customer deleted successfully.', 'success')
    return redirect(url_for('admin_customers'))

@app.route('/admin/farmers')
def admin_farmers():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    db = get_db()
    farmers = db.execute('SELECT * FROM farmers').fetchall()
    return render_template('admin_farmers.html', farmers=farmers)

@app.route('/admin/farmer/edit/<int:f_id>', methods=['GET', 'POST'])
def admin_edit_farmer(f_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    db = get_db()
    
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        contact = request.form['contact']
        address = request.form['address']
        gender = request.form['gender']
        
        db.execute('UPDATE farmers SET f_firstname = ?, f_lastname = ?, f_email = ?, f_contact = ?, f_address = ?, f_gender = ? WHERE f_id = ?',
                   (firstname, lastname, email, contact, address, gender, f_id))
        db.commit()
        flash('Farmer updated successfully.', 'success')
        return redirect(url_for('admin_farmers'))
        
    farmer = db.execute('SELECT * FROM farmers WHERE f_id = ?', (f_id,)).fetchone()
    if not farmer:
         flash('Farmer not found.', 'error')
         return redirect(url_for('admin_farmers'))

    return render_template('admin_edit_farmer.html', farmer=farmer)

@app.route('/admin/farmer/delete/<int:f_id>')
def admin_delete_farmer(f_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    db = get_db()
    # Optional: Check if farmer has products before deleting? For now, simpler delete.
    # Note: SQLite Foreign Keys ON DELETE actions should be considered, but current schema doesn't specify CASCADE explicitly.
    # If we delete a farmer, their products might remain orphaned or need deletion.
    # Logic: Delete products first to be safe or rely on DB. Let's strictly delete farmer for now as per minimal requirement, 
    # but a better approach would be to handle associated data.
    # Deleting farmer's products first:
    db.execute('DELETE FROM products WHERE f_id = ?', (f_id,))
    db.execute('DELETE FROM farmers WHERE f_id = ?', (f_id,))
    db.commit()
    flash('Farmer and their products deleted successfully.', 'success')
    return redirect(url_for('admin_farmers'))

# --- Cart & Payment Routes ---

# Razorpay Configuration
KEY_ID = 'rzp_test_RxwJftVK3EV6AU'
KEY_SECRET = 'vpadQBd7bt5KKxSB0p4jTOMD'
client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))

@app.route('/customer/add_to_cart/<int:p_id>', methods=['POST'])
def add_to_cart(p_id):
    if session.get('role') != 'customer':
        return redirect(url_for('login'))
        
    db = get_db()
    try:
        quantity = int(request.form['quantity'])
    except ValueError:
        flash('Invalid quantity.', 'error')
        return redirect(url_for('dashboard_customer'))

    product = db.execute('SELECT * FROM products WHERE p_id = ?', (p_id,)).fetchone()
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('dashboard_customer'))
        
    if quantity > product['p_quantity']:
        flash(f'Only {product["p_quantity"]} kg available.', 'error')
        return redirect(url_for('dashboard_customer'))
        
    # Check if item already in cart
    existing_item = db.execute('SELECT * FROM cart WHERE c_id = ? AND p_id = ?', (session['user_id'], p_id)).fetchone()
    
    if existing_item:
        new_quantity = existing_item['quantity'] + quantity
        if new_quantity > product['p_quantity']:
             flash(f'Total quantity in cart exceeds availability ({product["p_quantity"]} kg).', 'error')
        else:
            db.execute('UPDATE cart SET quantity = ? WHERE cart_id = ?', (new_quantity, existing_item['cart_id']))
            flash('Cart updated.', 'success')
    else:
        db.execute('INSERT INTO cart (c_id, p_id, quantity) VALUES (?, ?, ?)', (session['user_id'], p_id, quantity))
        flash('Added to cart.', 'success')
        
    db.commit()
    return redirect(url_for('dashboard_customer'))

@app.route('/customer/cart')
def view_cart():
    if session.get('role') != 'customer':
        return redirect(url_for('login'))
        
    db = get_db()
    cart_items = db.execute('''
        SELECT cart.*, products.p_name, products.p_priceperunit, products.p_quantity as max_quantity 
        FROM cart 
        JOIN products ON cart.p_id = products.p_id 
        WHERE cart.c_id = ?
    ''', (session['user_id'],)).fetchall()
    
    total_amount = sum([item['quantity'] * item['p_priceperunit'] for item in cart_items])
    
    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)

@app.route('/customer/cart/remove/<int:cart_id>')
def remove_from_cart(cart_id):
    if session.get('role') != 'customer':
        return redirect(url_for('login'))
        
    db = get_db()
    db.execute('DELETE FROM cart WHERE cart_id = ? AND c_id = ?', (cart_id, session['user_id']))
    db.commit()
    flash('Item removed from cart.', 'success')
    return redirect(url_for('view_cart'))

@app.route('/customer/checkout', methods=['GET', 'POST'])
def checkout():
    if session.get('role') != 'customer':
        return redirect(url_for('login'))
        
    db = get_db()
    cart_items = db.execute('''
        SELECT cart.*, products.p_name, products.p_priceperunit 
        FROM cart 
        JOIN products ON cart.p_id = products.p_id 
        WHERE cart.c_id = ?
    ''', (session['user_id'],)).fetchall()
    
    if not cart_items:
        flash('Your cart is empty.', 'error')
        return redirect(url_for('dashboard_customer'))
        
    total_amount = sum([item['quantity'] * item['p_priceperunit'] for item in cart_items])
    
    # Razorpay Order Creation
    data = { "amount": int(total_amount * 100), "currency": "INR", "receipt": "order_rcptid_11" }
    payment = client.order.create(data=data)

    customer = db.execute('SELECT * FROM customers WHERE c_id = ?', (session['user_id'],)).fetchone()
    
    return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount, payment=payment, key_id=KEY_ID, customer=customer)

@app.route('/customer/payment/success', methods=['POST'])
def payment_success():
    if session.get('role') != 'customer':
        return redirect(url_for('login'))
    
    db = get_db()
    cart_items = db.execute('''
        SELECT cart.*, products.p_name, products.p_priceperunit, products.p_quantity as stock_quantity, products.f_id
        FROM cart 
        JOIN products ON cart.p_id = products.p_id 
        WHERE cart.c_id = ?
    ''', (session['user_id'],)).fetchall()
    
    destination = request.form.get('destination', 'Default Address')
    
    for item in cart_items:
        total_price = item['quantity'] * item['p_priceperunit']
        
        # 1. Create Order
        cursor = db.execute('INSERT INTO orders (c_id, p_id, o_status, o_destination, o_amount) VALUES (?, ?, ?, ?, ?)',
                   (session['user_id'], item['p_id'], 'Confirmed', destination, total_price))
        o_id = cursor.lastrowid
        
        # 2. Create Payment Record
        db.execute('INSERT INTO payments (o_id, c_id, p_amount, p_method, p_status) VALUES (?, ?, ?, ?, ?)',
                   (o_id, session['user_id'], total_price, 'Online (Razorpay)', 'Completed'))
        
        # 3. Update Inventory
        new_quantity = item['stock_quantity'] - item['quantity']
        if new_quantity <= 0:
            db.execute('UPDATE products SET p_quantity = 0, p_status = "Sold Out" WHERE p_id = ?', (item['p_id'],))
        else:
            db.execute('UPDATE products SET p_quantity = ? WHERE p_id = ?', (new_quantity, item['p_id']))
            
    # Clear Cart
    db.execute('DELETE FROM cart WHERE c_id = ?', (session['user_id'],))
    db.commit()
    
    flash('Payment successful! Orders placed.', 'success')
    return redirect(url_for('dashboard_customer'))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        import database
        database.init_db()
    app.run(debug=True)
