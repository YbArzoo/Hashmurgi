from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)
