from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)



users = {
    "admin@example.com": {
        "name": "Admin User",
        "password": generate_password_hash("admin123"),
        "role": "admin",
        "employee_type": None,
        "phone": "123-456-7890",
        "address": "123 Admin St",
        "blood_group": "O+",
        "image": None,
        "verified": True
    }
}


users["manager@example.com"] = {
    "name": "Manager User",
    "password": generate_password_hash("manager123"),
    "role": "manager",
    "employee_type": None,
    "phone": "123-456-7891",
    "address": "123 Manager St",
    "blood_group": "A+",
    "image": None,
    "verified": True
}

users["farmer@example.com"] = {
    "name": "Farmer User",
    "password": generate_password_hash("farmer123"),
    "role": "employee",
    "employee_type": "farmer",
    "phone": "123-456-7892",
    "address": "123 Farmer St",
    "blood_group": "B+",
    "image": None,
    "verified": True
}

users["delivery@example.com"] = {
    "name": "Delivery User",
    "password": generate_password_hash("delivery123"),
    "role": "employee",
    "employee_type": "delivery",
    "phone": "123-456-7893",
    "address": "123 Delivery St",
    "blood_group": "AB+",
    "image": None,
    "verified": True
}


users["customer@example.com"] = {
    "name": "Customer User",
    "password": generate_password_hash("customer123"),
    "role": "customer",
    "employee_type": None,
    "phone": "123-456-7894",
    "address": "123 Customer St",
    "blood_group": "O-",
    "image": None,
    "verified": True
}


# Home page route
@app.route('/')
def home():
    user_email = session.get('user_email')
    return render_template('index.html', user_email=user_email, users=users)

# Admin panel route
@app.route('/admin')
def admin_panel():
    return render_template('admin_panel.html')

# Add Admin (GET + POST)
@app.route('/add-admin', methods=['GET', 'POST'])
def add_admin():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        print(f"[ADD ADMIN] Name: {name}, Email: {email}")
        return redirect(url_for('admin_panel'))
    return render_template('add-admin.html')

# Edit User Role (GET + POST)
@app.route('/edit-user-role', methods=['GET', 'POST'])
def edit_user_role():
    users = [
        {"id": 1, "name": "Arzoo", "role": "Customer"},
        {"id": 2, "name": "Baaker", "role": "Manager"},
        {"id": 3, "name": "Chuppu", "role": "Employee"}
    ]
    if request.method == 'POST':
        user_id = request.form['user_id']
        new_role = request.form['new_role']
        print(f"[EDIT ROLE] User ID: {user_id}, New Role: {new_role}")
        return redirect(url_for('admin_panel'))
    return render_template('edit-user-role.html', users=users)

# Delete User (GET + POST)
@app.route('/delete-users', methods=['GET', 'POST'])
def delete_users():
    users = [
        {"id": 1, "name": "Arzoo", "role": "Customer"},
        {"id": 2, "name": "Baaker", "role": "Manager"},
        {"id": 3, "name": "Chuppu", "role": "Employee"}
    ]
    if request.method == 'POST':
        user_id = request.form['user_id']
        print(f"[DELETE USER] User ID: {user_id}")
        return redirect(url_for('admin_panel'))
    return render_template('delete-users.html', users=users)


@app.route('/profile-management')
def profile_management():
    user_email = session.get('user_email')  # Get the logged-in user email
    user = users.get(user_email)  # Get the user data from the users dictionary
    
    if not user:
        return redirect(url_for('login'))  # Redirect to login if user not found
    
    if user['role'] == 'admin':
        return render_template('profile_management.html', user=user)  # Admin's profile management page
    elif user['role'] == 'customer':
        return render_template('profile_customer.html', user=user)  # Customer's profile management page
    elif user['role'] == 'employee' and user['employee_type'] == 'delivery':
        return render_template('profile_delivery_man.html', user=user)  # Delivery man's profile management page
    elif user['role'] == 'manager':
        return render_template('profile_manager.html', user=user)  # Manager's profile management page
    else:
        return redirect(url_for('home'))  # Redirect to home page for other roles





@app.route('/update-profile', methods=['GET', 'POST'])
def update_profile():
    user = users.get('admin@example.com')
    error = None
    if request.method == 'POST':
        user['name'] = request.form.get('name')
        user['phone'] = request.form.get('phone')
        user['address'] = request.form.get('address')
        user['blood_group'] = request.form.get('blood_group')
        flash('Profile updated successfully')
        return redirect(url_for('index'))
    return render_template('update_profile.html', user=user, error=error)


@app.route('/users')
def manage_users():
    user = users.get('admin@example.com')
    if user['role'] != 'admin':
        return redirect(url_for('index'))
    all_users = []
    for email, user_data in users.items():
        user_with_id = user_data.copy()
        user_with_id['id'] = email  # Use email as ID
        user_with_id['email'] = email
        all_users.append(user_with_id)
    return render_template('users.html', user=user, all_users=all_users)




@app.route('/select-user', methods=['POST'])
def select_user():
    target_user_id = request.form.get('target_user_id')
    if target_user_id in users:
        selected_user = users[target_user_id].copy()
        selected_user['id'] = target_user_id
        selected_user['email'] = target_user_id
        all_users = []
        for email, user_data in users.items():
            user_with_id = user_data.copy()
            user_with_id['id'] = email
            user_with_id['email'] = email
            all_users.append(user_with_id)
        return render_template('update_profile.html', 
                               user=users['admin@example.com'], 
                               selected_user=selected_user, 
                               all_users=all_users)
    return redirect(url_for('users'))

@app.route('/manager-dashboard')
def manager_dashboard():
    user_email = session.get('user_email')
    user = users.get(user_email)  # Fetch user details based on email

    if user and user['role'] == 'manager':
        return render_template('manager-dashboard.html', user=user)
    return redirect(url_for('home'))  # Redirect if user is not a manager



@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    # Check if user is logged in
    if 'user_email' not in session:
        return redirect(url_for('login'))

    user_email = session['user_email']
    user = users.get(user_email)  # Get the user info from the session
    
    if request.method == 'POST':
        # Add product logic here
        # (handle form submission as before)

        success = f"Product added successfully!"
        return render_template('add-product.html', success=success, user=user)
    
    return render_template('add-product.html', user=user)

@app.route('/orders')
def orders():
    # Make sure the user is logged in
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user_email']
    user = users.get(user_email)  # Get user details based on email

    # Dummy order data, replace with actual order fetching logic
    orders = [
        {"id": 1, "customer_name": "John Doe", "date": "2025-04-01", "status": "Delivered", "total": 500},
        {"id": 2, "customer_name": "Jane Smith", "date": "2025-04-02", "status": "In Transit", "total": 300}
    ]
    
    return render_template('order.html', user=user, orders=orders)

@app.route('/track-order/<int:order_id>')
def track_order(order_id):
    # Logic to track the order
    # For now, we'll just display the order ID
    return f"Tracking order with ID: {order_id}"

@app.route('/generate-invoice/<int:order_id>')
def generate_invoice(order_id):
    # Logic to generate the invoice
    # For now, we'll just display the order ID
    return f"Generating invoice for order with ID: {order_id}"

@app.route('/customer-dashboard')
def customer_dashboard():
    user_email = session.get('user_email')  # Get the logged-in user email
    user = users.get(user_email)  # Fetch user data from users dictionary
    
    if not user or user['role'] != 'customer':
        return redirect(url_for('login'))  # Redirect to login if not a customer
    
    return render_template('customer_dashboard.html', user=user)

@app.route('/delivery-dashboard')
def delivery_dashboard():
    user_email = session.get('user_email')
    user = users.get(user_email)  # Get user details based on email

    if user and user['role'] == 'employee' and user['employee_type'] == 'delivery':
        return render_template('delivery_man_dashboard.html', user=user)
    return redirect(url_for('home'))  # Redirect if user is not a delivery man


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if email exists and if password is correct
        if email in users and check_password_hash(users[email]['password'], password):
            session['user_email'] = email  # Save the user email in the session

            # Redirect based on role
            if users[email]['role'] == 'admin':
                return redirect(url_for('admin_panel'))  # Redirect to admin panel
            elif users[email]['role'] == 'manager':
                return redirect(url_for('manager_dashboard'))  # Redirect to manager dashboard
            elif users[email]['role'] == 'customer':
                return redirect(url_for('customer_dashboard'))  # Redirect to customer dashboard
            elif users[email]['role'] == 'employee' and users[email]['employee_type'] == 'delivery':
                return redirect(url_for('delivery_dashboard'))  # Redirect to delivery man dashboard
            else:
                return redirect(url_for('home'))  # Redirect to home page for other users
        else:
            error = "Invalid email or password"

    return render_template('login.html', error=error)






@app.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect(url_for('home'))  # Redirect to home page after logging out


# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        employee_type = request.form.get('employee_type') if role == 'employee' else None

        if email in users:
            error = "Email already registered"
        else:
            users[email] = {
                "name": name,
                "password": generate_password_hash(password),
                "role": role,
                "employee_type": employee_type,
                "phone": "",
                "address": "",
                "blood_group": "O+",
                "image": None,
                "verified": True
            }
            session['user_email'] = email
            return render_template('registration_success.html', email=email)
    return render_template('register.html', error=error)

# Forgot Password
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        if email in users:
            users[email]['password'] = generate_password_hash("password123")
            return render_template('password_reset_sent.html', email=email)
        else:
            error = "Email not found"
    return render_template('login.html', error=error)

# Change Password (self only, admin route already exists)
@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    user = users[session['user_email']]
    error = None
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if not check_password_hash(user['password'], current_password):
            error = "Current password is incorrect"
        elif new_password != confirm_password:
            error = "New passwords do not match"
        else:
            user['password'] = generate_password_hash(new_password)
            return render_template('password_reset_success.html')
    return render_template('change_password.html', user=user, error=error)


if __name__ == '__main__':
    app.run(debug=True)
