from flask import Flask, render_template, request, redirect, url_for, flash
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)


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
    return render_template('index.html')

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
    user = users.get('admin@example.com')  # Use admin for demonstration
    return render_template('profile_management.html', user=user)


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

if __name__ == '__main__':
    app.run(debug=True)
