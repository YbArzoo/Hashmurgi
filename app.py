from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Order, OrderItem, DeliveryIssue, DeliveryPayment
from config import Config
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from models import db, User, Product, Order, OrderItem, DeliveryIssue, DeliveryPayment







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
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if not user:
        return redirect(url_for('login'))

    if user.role == 'admin':
        return render_template('profile_management.html', user=user)
    elif user.role == 'manager':
        return render_template('profile_manager.html', user=user)
    elif user.role == 'customer':
        return render_template('profile_customer.html', user=user)
    elif user.role == 'delivery_man':
        return render_template('profile_delivery_man.html', user=user)
    elif user.role == 'farmer':
        return render_template('profile_farmer.html', user=user)  # ✅ Add this line
    else:
        return redirect(url_for('home'))





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

    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    # Get today's date
    today = datetime.now().date()
    
    # In a real application, you would fetch this data from the database
    # For now, we'll use dummy data
    today_deliveries = 3
    pending_deliveries = 2
    completed_deliveries = 1
    
    return render_template('delivery_man_dashboard.html', 
                          user=user,
                          today_deliveries=today_deliveries,
                          pending_deliveries=pending_deliveries,
                          completed_deliveries=completed_deliveries)
@app.route('/assigned-orders')
def assigned_orders():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    # In a real application, you would fetch orders from the database
    # For example:
    # orders = Order.query.filter_by(delivery_man_id=user_id, status='Pending').all()
    
    # For now, we'll use dummy data
    orders = [
        {"id": 1, "customer_name": "John Doe", "address": "123 Main St, Dhaka", "items": "Chicken (2kg)", "status": "Pending"},
        {"id": 2, "customer_name": "Jane Smith", "address": "456 Park Ave, Dhaka", "items": "Eggs (30pcs)", "status": "In Transit"}
    ]
    
    history = [
        {"id": 101, "customer_name": "Alice Johnson", "date": "2025-04-14", "status": "Delivered", "rating": 5},
        {"id": 102, "customer_name": "Bob Williams", "date": "2025-04-13", "status": "Delivered", "rating": 4}
    ]
    
    return render_template('assigned_orders.html', user=user, orders=orders, history=history)

@app.route('/update-order-status/<int:order_id>', methods=['GET', 'POST'])
def update_order_status(order_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # In a real application, you would update the order in the database
        # For example:
        # order = Order.query.get(order_id)
        # if order and order.delivery_man_id == user_id:
        #     order.status = request.form.get('status')
        #     if order.status == 'Delivered':
        #         order.delivered_at = datetime.utcnow()
        #     db.session.commit()
        #     flash('Order status updated successfully!', 'success')
        
        flash('Order status updated successfully!', 'success')
    
    # Redirect back to assigned orders page
    return redirect(url_for('assigned_orders'))
@app.route('/delivery-map')
def delivery_map():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    # In a real application, you would fetch locations from the database
    # For example:
    # orders = Order.query.filter_by(delivery_man_id=user_id).all()
    # locations = []
    # for order in orders:
    #     # You would need to have latitude and longitude stored or use a geocoding service
    #     locations.append({
    #         "order_id": order.id,
    #         "customer_name": order.customer.name,
    #         "address": order.address,
    #         "status": order.status,
    #         "lat": order.latitude,
    #         "lng": order.longitude
    #     })
    
    # For now, we'll use dummy data
    locations = [
        {"order_id": 1, "customer_name": "John Doe", "address": "123 Main St, Dhaka", "distance": 2.5, "status": "Pending", "lat": 23.8103, "lng": 90.4125},
        {"order_id": 2, "customer_name": "Jane Smith", "address": "456 Park Ave, Dhaka", "distance": 3.8, "status": "In Transit", "lat": 23.8203, "lng": 90.4225}
    ]
    
    return render_template('delivery_map.html', user=user, locations=locations)

@app.route('/report-issues')
def report_issues():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    # In a real application, you would fetch orders assigned to this delivery person
    # For example:
    # orders = Order.query.filter_by(delivery_man_id=user_id).all()
    
    # And you would fetch previous reports submitted by this delivery person
    # For example:
    # reports = DeliveryIssue.query.filter_by(reported_by=user_id).order_by(DeliveryIssue.created_at.desc()).all()
    
    # For now, we'll use dummy data
    orders = [
        {"id": 1, "customer_name": "John Doe"},
        {"id": 2, "customer_name": "Jane Smith"}
    ]
    
    reports = [
        {"id": 1, "order_id": 101, "issue_type": "Wrong Address", "date": "2025-04-14", "status": "Resolved"},
        {"id": 2, "order_id": 102, "issue_type": "Customer Unavailable", "date": "2025-04-13", "status": "Pending"}
    ]
    
    return render_template('report_issues.html', user=user, orders=orders, reports=reports)

@app.route('/submit-issue', methods=['POST'])
def submit_issue():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    # In a real application, you would save the issue to the database
    # For example:
    # order_id = request.form.get('order_id')
    # issue_type = request.form.get('issue_type')
    # description = request.form.get('description')
    # urgency = request.form.get('urgency')
    
    # # Handle image upload if provided
    # image_filename = None
    # if 'image' in request.files and request.files['image'].filename:
    #     image = request.files['image']
    #     image_filename = secure_filename(image.filename)
    #     image.save(os.path.join('static/uploads', image_filename))
    
    # new_issue = DeliveryIssue(
    #     order_id=order_id,
    #     reported_by=user_id,
    #     issue_type=issue_type,
    #     description=description,
    #     image=image_filename,
    #     urgency=urgency,
    #     status='Pending'
    # )
    # db.session.add(new_issue)
    # db.session.commit()
    
    flash('Issue reported successfully!', 'success')
    return redirect(url_for('report_issues'))
@app.route('/delivery-income')
def delivery_income():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    # In a real application, you would calculate these values from the database
    # For example:
    # today = datetime.now().date()
    # month_start = datetime(today.year, today.month, 1).date()
    # week_start = today - timedelta(days=today.weekday())
    
    # # Get completed orders for different time periods
    # monthly_orders = Order.query.filter(
    #     Order.delivery_man_id == user_id,
    #     Order.status == 'Delivered',
    #     Order.delivered_at >= month_start
    # ).all()
    
    # weekly_orders = Order.query.filter(
    #     Order.delivery_man_id == user_id,
    #     Order.status == 'Delivered',
    #     Order.delivered_at >= week_start
    # ).all()
    
    # daily_orders = Order.query.filter(
    #     Order.delivery_man_id == user_id,
    #     Order.status == 'Delivered',
    #     Order.delivered_at >= today
    # ).all()
    
    # # Calculate income (assuming there's a delivery fee or commission per order)
    # monthly_income = sum(order.delivery_fee for order in monthly_orders)
    # weekly_income = sum(order.delivery_fee for order in weekly_orders)
    # daily_income = sum(order.delivery_fee for order in daily_orders)
    
    # # Get payment history
    # payments = DeliveryPayment.query.filter_by(delivery_man_id=user_id).order_by(DeliveryPayment.payment_date.desc()).all()
    
    # For now, we'll use dummy data
    monthly_income = 15000
    monthly_deliveries = 45
    weekly_income = 3500
    weekly_deliveries = 12
    daily_income = 800
    daily_deliveries = 3
    
    payments = [
        {"id": "PAY001", "date": "2025-04-15", "amount": 5000, "method": "Bank Transfer", "status": "Completed"},
        {"id": "PAY002", "date": "2025-04-01", "amount": 4500, "method": "Mobile Banking", "status": "Completed"},
        {"id": "PAY003", "date": "2025-03-15", "amount": 5500, "method": "Bank Transfer", "status": "Completed"}
    ]
    
    return render_template('delivery_income.html', 
                          user=user, 
                          monthly_income=monthly_income,
                          monthly_deliveries=monthly_deliveries,
                          weekly_income=weekly_income,
                          weekly_deliveries=weekly_deliveries,
                          daily_income=daily_income,
                          daily_deliveries=daily_deliveries,
                          payments=payments)
@app.route('/view-report/<int:report_id>')
def view_report(report_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    # In a real application, you would fetch the report from the database
    # For example:
    # report = DeliveryIssue.query.get_or_404(report_id)
    # if report.reported_by != user_id:
    #     flash('You are not authorized to view this report', 'danger')
    #     return redirect(url_for('report_issues'))
    
    # For now, we'll just redirect back to the report issues page
    # In a real application, you would render a template with report details
    return redirect(url_for('report_issues'))
@app.route('/update-location', methods=['POST'])
def update_location():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
        
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'delivery_man':
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if not all([latitude, longitude]):
        return jsonify({"error": "Missing required fields"}), 400
    
    # In a real application, you would update the delivery person's location
    # For example:
    # user.current_latitude = latitude
    # user.current_longitude = longitude
    # user.last_location_update = datetime.utcnow()
    # db.session.commit()
    
    return jsonify({"success": True, "message": "Location updated successfully"}), 200
@app.route('/view-order-details/<int:order_id>')
def view_order_details(order_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    # In a real application, you would fetch the order from the database
    # For example:
    # order = Order.query.get_or_404(order_id)
    # if order.delivery_man_id != user_id:
    #     flash('You are not authorized to view this order', 'danger')
    #     return redirect(url_for('assigned_orders'))
    
    # For now, we'll just redirect back to the assigned orders page
    # In a real application, you would render a template with order details
    return redirect(url_for('assigned_orders'))

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
            
            # Redirect based on role
            if role == 'admin':
                return redirect(url_for('admin_panel'))
            elif role == 'manager':
                return redirect(url_for('manager_dashboard'))
            elif role == 'delivery_man':
                return redirect(url_for('delivery_dashboard'))
            elif role == 'farmer':
                return redirect(url_for('farmer_dashboard'))  # Add this line
            elif role == 'customer':
                return redirect(url_for('customer_dashboard'))
            
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


@app.route('/notifications')
def notifications():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'manager':
        return redirect(url_for('login'))
    
    return render_template('notifications.html', user=user)

@app.route('/feed-resources')
def feed_resources():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'manager':
        return redirect(url_for('login'))
    
    return render_template('feed_resources.html', user=user)

@app.route('/production-record')
def production_record():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'manager':
        return redirect(url_for('login'))
    
    from datetime import datetime
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('production_record.html', user=user, today_date=today_date)

@app.route('/vaccination-schedule')
def vaccination_schedule():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'manager':
        return redirect(url_for('login'))
    
    from datetime import datetime
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('vaccination_schedule.html', user=user, today_date=today_date)

@app.route('/poultry-stock')
def poultry_stock():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'manager':
        return redirect(url_for('login'))
    
    return render_template('poultry_stock.html', user=user)
@app.route('/shop')
def shop():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'customer':
        return redirect(url_for('login'))
    
    # In a real application, you would fetch products from the database
    # For now, we'll just render the template
    return render_template('shop.html', user=user)

@app.route('/track-orders')
def track_customer_orders():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user or user.role != 'customer':
        return redirect(url_for('login'))
    
    # In a real application, you would fetch the user's orders from the database
    # For now, we'll just render the template with dummy data
    return render_template('track_orders.html', user=user)

@app.route('/farmer-dashboard')
def farmer_dashboard():
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if not user or user.role != 'farmer':
        return redirect(url_for('login'))

    return render_template('farmer_dashboard.html', user=user)










if __name__ == '__main__':
    app.run(debug=True)
