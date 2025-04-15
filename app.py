from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from config import Config
from flask_sqlalchemy import SQLAlchemy







app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config.from_object(Config)
db.init_app(app)

# Create tables once when app starts
with app.app_context():
    db.create_all()




# Home page route
@app.route('/')
def home():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    return render_template('index.html', user=user)


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
        
        # Check if email already exists in the database
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'danger')
            return render_template('add-admin.html')

        # Hash the password before saving to the database
        hashed_password = generate_password_hash(password)
        
        # Create a new admin user
        new_admin = User(
            name=name,
            email=email,
            password=hashed_password,
            role='admin',  # Set the role to admin by default
            phone='',
            address='',
            blood_group='O+',
            image=None
        )
        
        # Add the new admin to the database
        db.session.add(new_admin)
        db.session.commit()

        flash('New admin added successfully!', 'success')
        return redirect(url_for('admin_panel'))  # Redirect back to the admin panel after adding the admin

    return render_template('add-admin.html')


# Edit User Role (GET + POST)
@app.route('/edit-user-role', methods=['GET', 'POST'])
def edit_user_role():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':  # Check if user exists and is an admin
        return redirect(url_for('login'))  # Or return to a page indicating they don't have admin rights

    users = User.query.all()  # Fetch all users from the database

    if request.method == 'POST':
        user_id = request.form['user_id']
        new_role = request.form['new_role']
        user_to_update = User.query.get(user_id)

        if user_to_update:
            user_to_update.role = new_role  # Update the user's role
            db.session.commit()  # Save changes to the database

        return redirect(url_for('admin_panel'))  # Redirect back to the admin panel after updating the role

    return render_template('edit-user-role.html', users=users)



# Delete User (GET + POST)
@app.route('/delete-users', methods=['GET', 'POST'])
def delete_users():
    if 'user_id' not in session or User.query.get(session['user_id']).role != 'admin':
        return redirect(url_for('login'))

    users = User.query.all()  # Fetch all users from the database

    if request.method == 'POST':
        user_id = request.form['user_id']
        user_to_delete = User.query.get(user_id)

        if user_to_delete:
            db.session.delete(user_to_delete)
            db.session.commit()  # Delete the user from the database

        return redirect(url_for('admin_panel'))  # Redirect back to the admin panel after deletion

    return render_template('delete-users.html', users=users)



@app.route('/profile-management')
def profile_management():
    user_id = session.get('user_id')  # Get the logged-in user email
    user = User.query.get(user_id)  # Get the user data from the users table
    
    if not user:
        return redirect(url_for('login'))  # Redirect to login if user not found
    
    if user.role == 'admin':
        return render_template('profile_management.html', user=user)  # Admin's profile management page
    elif user.role == 'customer':
        return render_template('profile_customer.html', user=user)  # Customer's profile management page
    elif user.role == 'delivery_man':  # Changed from 'employee' to 'delivery_man'
        return render_template('profile_delivery_man.html', user=user)  # Delivery man's profile management page
    elif user.role == 'manager':
        return render_template('profile_manager.html', user=user)  # Manager's profile management page
    else:
        return redirect(url_for('home'))  # Redirect to home page for other roles






@app.route('/update-profile', methods=['GET', 'POST'])
def update_profile():
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if not user:
        return redirect(url_for('login'))

    error = None

    if request.method == 'POST':
        # Ensure the email is included in the update
        user.name = request.form.get('name')
        user.email = request.form.get('email')  # Correctly handle email field
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        user.blood_group = request.form.get('blood_group')

        # Handle image upload
        image = request.files.get('image')
        if image:
            image_filename = secure_filename(image.filename)
            image.save(os.path.join('static/images', image_filename))
            user.image = image_filename

        db.session.commit()  # Commit the changes to the database
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile_management'))

    return render_template('update_profile.html', user=user, error=error)




@app.route('/users')
def manage_users():
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if user.role != 'admin':
        return redirect(url_for('home'))
    
    all_users = User.query.all()
    return render_template('users.html', user=user, all_users=all_users)




@app.route('/select-user', methods=['POST'])
def select_user():
    target_user_id = request.form.get('target_user_id')
    selected_user = User.query.get(target_user_id)
    current_user = User.query.get(session.get('user_id'))

    if selected_user:
        all_users = User.query.all()
        return render_template('update_profile.html',
                               user=current_user,
                               selected_user=selected_user,
                               all_users=all_users)
    return redirect(url_for('users'))


@app.route('/manager-dashboard')
def manager_dashboard():
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if user and user.role == 'manager':  # Use dot notation
        return render_template('manager-dashboard.html', user=user)
    return redirect(url_for('home'))  # Redirect if the user is not a manager



@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))

    success = None

    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        quantity = request.form.get('quantity')
        unit_price = request.form.get('unit_price')
        product_description = request.form.get('product_description')

        try:
            new_product = Product(
                name=name,
                category=category,
                quantity=int(quantity),
                unit_price=float(unit_price),
                product_description=product_description,
                added_by=user.id
            )
            db.session.add(new_product)
            db.session.commit()
            success = "Product added successfully!"
        except Exception as e:
            db.session.rollback()
            success = f"Error: {str(e)}"

    return render_template('add-product.html', user=user, success=success)


@app.route('/orders')
def orders():
    # Make sure the user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))

    # Dummy order data, replace with real query later
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
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'customer':  # Make sure the user is a customer
        return redirect(url_for('home'))  # Redirect if not a customer
    
    return render_template('customer_dashboard.html', user=user)


@app.route('/delivery-dashboard')
def delivery_dashboard():
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if user and user.role == 'delivery_man':  # Check for 'delivery_man' role
        return render_template('delivery_man_dashboard.html', user=user)
    return redirect(url_for('home'))  # Redirect if user is not a delivery man



@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id

            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('admin_panel'))
            elif user.role == 'manager':
                return redirect(url_for('manager_dashboard'))
            elif user.role == 'delivery_man':
                return redirect(url_for('delivery_dashboard'))
            elif user.role == 'farmer':
                return redirect(url_for('farmer_dashboard'))
            elif user.role == 'customer':
                return redirect(url_for('customer_dashboard'))
        else:
            error = "Invalid email or password"
    return render_template('login.html', error=error)






@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_id', None)  # Clear the session
    return redirect(url_for('home'))  # Redirect to the homepage (index.html)





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

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            error = "Email already registered"
        else:
            hashed_pw = generate_password_hash(password)
            new_user = User(
                name=name,
                email=email,
                password=hashed_pw,
                role=role,
                phone="",
                address="",
                blood_group="O+",
                image=None
            )
            db.session.add(new_user)
            db.session.commit()
            session['user_id'] = new_user.id
            return render_template('registration_success.html', email=email)
    return render_template('register.html', error=error)

# Forgot Password
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            # Set default new password
            user.password = generate_password_hash("password123")
            db.session.commit()
            return render_template('password_reset_sent.html', email=email)
        else:
            error = "Email not found"

    return render_template('login.html', error=error)





@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))

    error = None

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not check_password_hash(user.password, current_password):
            error = "Current password is incorrect"
        elif new_password != confirm_password:
            error = "New passwords do not match"
        else:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            return render_template('password_reset_success.html')

    return render_template('change_password.html', user=user, error=error)



if __name__ == '__main__':
    app.run(debug=True)
