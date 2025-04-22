from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, redirect, url_for
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Product, Order, OrderItem, DeliveryIssue, DeliveryPayment, Batch, Vaccination, Production, FeedLog, Sale, Invoice, PriorityLevel, PoultryBatch
from config import Config
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from datetime import datetime, date
from models import Vaccination
from flask import make_response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from flask_migrate import Migrate





app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'  # This sets the SQLite database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Optional: disables a feature that's not necessary

migrate = Migrate(app, db)
app.secret_key = os.urandom(24)
app.config.from_object(Config)
db.init_app(app)


UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



# Create tables once when app starts
with app.app_context():
    db.create_all()




# Home page route
@app.route('/')
def home():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None
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

@app.route('/admin/manage_batches')
def manage_batches():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role not in ['admin', 'manager']:
        return redirect(url_for('login'))

    batches = Batch.query.order_by(Batch.batch_name.desc()).all()
    return render_template('admin_manage_batches.html', user=user, batches=batches)



@app.route('/admin/add_batch', methods=['POST'])
def add_batch():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    batch_name = request.form['batch_name'].strip()
    bird_type = request.form['bird_type'].strip()  # <- retrieved here

    # ✅ Insert this block here!
    if not bird_type:
        flash("Bird type is required but not found in form!", "danger")
        return redirect(url_for('manage_batches'))

    breed = request.form.get('breed', '').strip()
    bird_type = request.form['bird_type'].strip()  # ✅ Must be read from form
    breed = request.form.get('breed', '').strip()
    location = request.form.get('location', '').strip()
    quantity = int(request.form['quantity'])
    arrival_date = datetime.strptime(request.form['arrival_date'], '%Y-%m-%d')
    status = request.form.get('status', 'Healthy')
    notes = request.form.get('notes', '').strip()

    # Check duplicates
    existing_poultry_batch = PoultryBatch.query.filter_by(batch_id=batch_name).first()
    if existing_poultry_batch:
        flash(f"A poultry batch with name '{batch_name}' already exists.", 'danger')
        return redirect(url_for('manage_batches'))

    existing_batch = Batch.query.filter_by(batch_name=batch_name).first()
    if existing_batch:
        flash(f"A batch with name '{batch_name}' already exists.", 'danger')
        return redirect(url_for('manage_batches'))

    # ✅ Create and insert
    new_batch = Batch(
        batch_name=batch_name,
        bird_type=bird_type,  # ✅ now handled properly
        quantity=quantity,
        arrival_date=arrival_date,
        notes=notes,
        added_by=session['user_id']
    )
    db.session.add(new_batch)

    new_poultry_batch = PoultryBatch(
        batch_id=batch_name,
        bird_type=bird_type,
        breed=breed,
        location=location,
        count=quantity,
        arrival_date=arrival_date,
        status=status,
        created_by=session['user_id']
    )
    db.session.add(new_poultry_batch)

    db.session.commit()
    flash("Batch added successfully!", 'success')
    return redirect(url_for('manage_batches'))

@app.route('/admin/delete_batch/<int:batch_id>')
def delete_batch(batch_id):
    batch = Batch.query.get(batch_id)

    if batch:
        # ✅ First delete all related Vaccinations
        for vac in batch.vaccinations:
            db.session.delete(vac)

        # ✅ Delete related Production logs
        for prod in batch.productions:
            db.session.delete(prod)

        # ✅ Delete related Feed logs
        for log in batch.feed_logs:
            db.session.delete(log)

        # ✅ Delete from PoultryBatch table if exists
        poultry_batch = PoultryBatch.query.filter_by(batch_id=batch.batch_name).first()
        if poultry_batch:
            db.session.delete(poultry_batch)

        # ✅ Now delete the batch
        db.session.delete(batch)

        db.session.commit()
        flash('Batch and all related records deleted successfully!', 'success')
    else:
        flash('Batch not found.', 'danger')

    return redirect(url_for('manage_batches'))

## This route is for the confirmation to delete any batch associated vaccination, production and feedlog 

@app.route('/admin/check_batch_dependencies/<int:batch_id>')
def check_batch_dependencies(batch_id):
    batch = Batch.query.get(batch_id)
    if not batch:
        return jsonify({'error': 'Batch not found'}), 404

    return jsonify({
        'vaccinations': len(batch.vaccinations),
        'productions': len(batch.productions),
        'feedlogs': len(batch.feed_logs)
    })

@app.route('/admin/edit_batch/<int:batch_id>', methods=['GET', 'POST'])
def edit_batch(batch_id):
    batch = Batch.query.get_or_404(batch_id)

    # ✅ Add this here to fetch the related PoultryBatch record
    poultry_batch = PoultryBatch.query.filter_by(batch_id=batch.batch_name).first()

    if request.method == 'POST':
        try:
            new_quantity = int(request.form['quantity'])

            # ✅ Update Batch table
            batch.quantity = new_quantity

            # ✅ Update PoultryBatch table if it exists
            if poultry_batch:
                poultry_batch.count = new_quantity

            db.session.commit()
            flash('Batch quantity updated successfully.', 'success')
            return redirect(url_for('manage_batches'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating batch quantity: ' + str(e), 'danger')

    return render_template('edit_batch.html', batch=batch)



# @app.route('/admin/edit_batch/<int:batch_id>', methods=['GET', 'POST'])
# def edit_batch(batch_id):
#     batch = Batch.query.get_or_404(batch_id)
#     poultry_batch = PoultryBatch.query.filter_by(batch_id=batch.batch_name).first()

#     if request.method == 'POST':
#         try:
#             new_quantity = int(request.form['quantity'])

#             batch.quantity = new_quantity
#             if poultry_batch:
#                 poultry_batch.count = new_quantity

#             db.session.commit()
#             flash('Batch quantity updated successfully.', 'success')
#             return redirect(url_for('manage_batches'))
#         except Exception as e:
#             db.session.rollback()
#             flash('Error updating batch quantity: ' + str(e), 'danger')

#     return render_template('edit_batch.html', batch=batch)

@app.route('/admin/feed-resources', methods=['GET', 'POST'])
def manage_feed_resources():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # user = User.query.get(session['user_id'])
    user = db.session.get(User, session['user_id'])

    if not user or user.role not in ['admin', 'manager']:  # ✅ allow both
        return redirect(url_for('login'))

    batches = Batch.query.all()

    if request.method == 'POST':
        batch_id = request.form['batch_id']
        log_date = datetime.strptime(request.form['log_date'], '%Y-%m-%d').date()
        feed_type = request.form['feed_type']
        quantity_kg = float(request.form['quantity_kg'])
        cost = float(request.form['cost'])
        notes = request.form['notes']

        # ✅ Flag critical low-feed logs
        priority = PriorityLevel.high if quantity_kg < 50 else PriorityLevel.medium

        feed_entry = FeedLog(
            batch_id=batch_id,
            log_date=log_date,
            feed_type=feed_type,
            quantity_kg=quantity_kg,
            cost=cost,
            notes=notes,
            priority=priority
        )
        db.session.add(feed_entry)
        db.session.commit()
        return redirect(url_for('manage_feed_resources'))

    logs = FeedLog.query.order_by(FeedLog.log_date.desc()).all()
    return render_template('admin_manage_feed.html', user=user, logs=logs, batches=batches)

@app.route('/admin/record-sales', methods=['GET', 'POST'])
def record_sales():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('login'))

    customers = User.query.filter_by(role='customer').all()
    products = Product.query.all()

    if request.method == 'POST':
        customer_id = request.form['customer_id']
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        sale_date = datetime.strptime(request.form['sale_date'], '%Y-%m-%d').date()
        product = Product.query.get(product_id)
        total_amount = product.unit_price * quantity
        notes = request.form['notes']

        new_sale = Sale(
            customer_id=customer_id,
            product_id=product_id,
            quantity=quantity,
            total_amount=total_amount,
            sale_date=sale_date,
            notes=notes
        )
        db.session.add(new_sale)
        db.session.commit()
        return redirect(url_for('record_sales'))

    sales = Sale.query.order_by(Sale.sale_date.desc()).all()
    return render_template('admin_record_sales.html', user=user, sales=sales, customers=customers, products=products)


@app.route('/admin/invoices', methods=['GET', 'POST'])
def manage_invoices():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        invoice_id = request.form['invoice_id']
        new_status = request.form['status']
        invoice = Invoice.query.get(invoice_id)
        if invoice:
            invoice.status = new_status
            db.session.commit()
        return redirect(url_for('manage_invoices'))

    invoices = Invoice.query.order_by(Invoice.issue_date.desc()).all()
    return render_template('admin_manage_invoices.html', user=user, invoices=invoices)



@app.route('/admin/receipts', methods=['GET', 'POST'])
def generate_receipts():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('login'))

    sales = Sale.query.all()

    if request.method == 'POST':
        sale_id = int(request.form['sale_id'])
        sale = Sale.query.get(sale_id)

        # Create PDF in memory
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        p.setFont("Helvetica", 12)

        p.drawString(50, 750, f"Receipt for Sale #{sale.id}")
        p.drawString(50, 730, f"Customer: {sale.customer.name}")
        p.drawString(50, 710, f"Product: {sale.product.name}")
        p.drawString(50, 690, f"Quantity: {sale.quantity}")
        p.drawString(50, 670, f"Total: BDT {sale.total_amount}")
        p.drawString(50, 650, f"Sale Date: {sale.sale_date}")

        p.showPage()
        p.save()
        buffer.seek(0)

        return make_response(buffer.getvalue(), {
            "Content-Type": "application/pdf",
            "Content-Disposition": f"attachment; filename=receipt_{sale.id}.pdf"
        })

    return render_template('admin_generate_receipts.html', user=user, sales=sales)

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
    user = db.session.get(User, user_id)


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
    user = db.session.get(User, user_id)


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
    user = db.session.get(User, user_id)

    
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
    user = db.session.get(User, user_id)


    if user and user.role == 'manager':  # Use dot notation
        return render_template('manager-dashboard.html', user=user)
    return redirect(url_for('home'))  # Redirect if the user is not a manager



@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = db.session.get(User, user_id)
    
    if not user:
        return redirect(url_for('login'))

    success = None
    error = None

    # Fetch all existing products for display in the template
    products = Product.query.all()

    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        quantity = request.form.get('quantity')
        unit_price = request.form.get('unit_price')
        product_description = request.form.get('product_description')

        # Handle image upload
        image = request.files.get('image')
        image_filename = None
        if image and allowed_file(image.filename):
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))  # Save image to static/images

        try:
            # Add new product to DB
            new_product = Product(
                name=name,
                category=category,
                quantity=int(quantity),
                unit_price=float(unit_price),
                product_description=product_description,
                image=image_filename,  # Save filename in DB
                added_by=user.id
            )
            db.session.add(new_product)
            db.session.commit()
            success = "Product added successfully!"
        except Exception as e:
            db.session.rollback()
            success = f"Error: {str(e)}"

    # Render the page with success, error, and products
    return render_template('add-product.html', user=user, success=success, error=error, products=products)



@app.route('/delete-product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = db.session.get(User, user_id)
    
    if user.role not in ['admin', 'manager']:
        return redirect(url_for('login'))

    product = Product.query.get(product_id)
    if product:
        try:
            db.session.delete(product)
            db.session.commit()
            return redirect(url_for('add_product', success="Product deleted successfully"))
        except Exception as e:
            db.session.rollback()
            return redirect(url_for('add_product', error=f"Error: {str(e)}"))
    else:
        return redirect(url_for('add_product', error="Product not found"))



@app.route('/orders')
def orders():
    # Make sure the user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = db.session.get(User, user_id)

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

@app.route('/admin/vaccinations', methods=['GET', 'POST'])
def manage_vaccinations():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role not in ['admin', 'manager']:
        return redirect(url_for('login'))

    batches = Batch.query.order_by(Batch.batch_name.asc()).all()

    if request.method == 'POST':
        batch_id = request.form['batch_id']
        vaccine_name = request.form['vaccine_name'].strip().lower()  # Normalize for duplicate check
        scheduled_date = datetime.strptime(request.form['scheduled_date'], '%Y-%m-%d').date()
        dosage = request.form.get('dosage', '').strip()
        administered_by = request.form.get('administered_by', '').strip()
        status = request.form['status']
        notes = request.form.get('notes', '').strip()
        priority_input = request.form.get('priority', 'medium')
        priority = PriorityLevel[priority_input]

        # ❌ Prevent duplicate vaccine name for the same batch (case-insensitive)
        existing = Vaccination.query.filter(
            Vaccination.batch_id == batch_id,
            db.func.lower(Vaccination.vaccine_name) == vaccine_name
        ).first()

        if existing:
            flash('⚠️ This vaccine has already been scheduled for this batch.', 'warning')
            return redirect(url_for('manage_vaccinations'))

        # ✅ Create and save vaccination using formatted vaccine name
        new_vaccine = Vaccination(
            batch_id=batch_id,
            vaccine_name=vaccine_name.title(),  # Store nicely formatted
            scheduled_date=scheduled_date,
            dosage=dosage,
            administered_by=administered_by,
            status=status,
            notes=notes,
            priority=priority
        )
        db.session.add(new_vaccine)
        db.session.commit()
        flash('✅ Vaccination added successfully.', 'success')
        return redirect(url_for('manage_vaccinations'))

    today = date.today()

    # Upcoming vaccinations (Scheduled and future date)
    upcoming = (
        db.session.query(Vaccination)
        .join(Batch)
        .filter(Vaccination.status == 'Scheduled', Vaccination.scheduled_date >= today)
        .options(db.joinedload(Vaccination.batch))
        .order_by(Vaccination.scheduled_date.asc())
        .all()
    )

    # Vaccination history (Completed or Missed and in the past)
    history = (
        db.session.query(Vaccination)
        .join(Batch)
        .filter(Vaccination.status.in_(['Completed', 'Missed']), Vaccination.scheduled_date < today)
        .options(db.joinedload(Vaccination.batch))
        .order_by(Vaccination.scheduled_date.desc())
        .all()
    )

    return render_template(
        'admin_manage_vaccinations.html',
        user=user,
        batches=batches,
        upcoming=upcoming,
        history=history
    )



@app.route('/admin/production', methods=['GET', 'POST'])
def manage_production():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role not in ['admin', 'manager']:  # ✅ allow both
        return redirect(url_for('login'))

    batches = Batch.query.all()

    if request.method == 'POST':
        batch_id = request.form['batch_id']
        production_date = datetime.strptime(request.form['production_date'], '%Y-%m-%d').date()
        egg_count = int(request.form['egg_count'])
        meat_weight_kg = float(request.form['meat_weight_kg'])
        notes = request.form['notes']
        priority_input = request.form.get('priority', 'medium')  # ✅ NEW
        priority = PriorityLevel[priority_input]

        new_entry = Production(
            batch_id=batch_id,
            production_date=production_date,
            egg_count=egg_count,
            meat_weight_kg=meat_weight_kg,
            notes=notes,
            priority=priority
        )
        db.session.add(new_entry)
        db.session.commit()
        return redirect(url_for('manage_production'))

    records = Production.query.order_by(Production.production_date.desc()).all()
    return render_template('admin_manage_production.html', user=user, records=records, batches=batches)



@app.route('/customer-dashboard')
def customer_dashboard():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    
    if not user or user.role != 'customer':  # Make sure the user is a customer
        return redirect(url_for('home'))  # Redirect if not a customer
    
    return render_template('customer_dashboard.html', user=user)


@app.route('/delivery-dashboard')
def delivery_dashboard():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

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
    user = db.session.get(User, user_id)

    
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
    user = db.session.get(User, user_id)

    
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
    user = db.session.get(User, user_id)

    
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
    user = db.session.get(User, user_id)

    
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
    user = db.session.get(User, user_id)

    
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
    user = db.session.get(User, user_id)

    
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
    user = db.session.get(User, user_id)

    
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
    user = db.session.get(User, user_id)

    
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
    user = db.session.get(User, user_id)

    
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
                return redirect(url_for('home'))  # send to homepage after login

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



@app.route('/daily-tasks', methods=['GET', 'POST'])
def daily_tasks():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    
    if not user or user.role != 'farmer':
        return redirect(url_for('login'))
    
    # Get today's date for the form
    from datetime import datetime
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        # In a real application, you would save the task to the database
        flash('Task added successfully!', 'success')
        return redirect(url_for('daily_tasks'))
    
    # In a real application, you would fetch tasks from the database
    return render_template('daily_tasks.html', user=user, today_date=today_date)


@app.route('/poultry-status-farmer', methods=['GET', 'POST'])
def poultry_status_farmer():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    
    if not user or user.role != 'farmer':
        return redirect(url_for('login'))
    
    # Get today's date for the form
    from datetime import datetime
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'count_update':
            # Handle count update form submission
            flash('Poultry count updated successfully!', 'success')
        elif form_type == 'health_check':
            # Handle health check form submission
            flash('Health check recorded successfully!', 'success')
        
        return redirect(url_for('poultry_status_farmer'))
    
    return render_template('poultry_status_farmer.html', user=user, today_date=today_date)

@app.route('/feed-schedule', methods=['GET', 'POST'])
def feed_schedule():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    
    if not user or user.role != 'farmer':
        return redirect(url_for('login'))
    
    # Get today's date for the form
    from datetime import datetime
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        # In a real application, you would save the feeding record to the database
        flash('Feeding record added successfully!', 'success')
        return redirect(url_for('feed_schedule'))
    
    return render_template('feed_schedule.html', user=user, today_date=today_date)


@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = db.session.get(User, user_id)

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
    user = db.session.get(User, user_id)

    
    if not user or user.role != 'manager':
        return redirect(url_for('login'))
    
    return render_template('notifications.html', user=user)

@app.route('/feed-resources', methods=['GET', 'POST'])
def feed_resources():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user or user.role != 'manager':
        return redirect(url_for('login'))

    batches = Batch.query.all()

    if request.method == 'POST':
        batch_id = request.form['batch_id']
        log_date = datetime.strptime(request.form['log_date'], '%Y-%m-%d').date()
        feed_type = request.form['feed_type']
        quantity_kg = float(request.form['quantity_kg'])
        cost = float(request.form['cost'])
        notes = request.form['notes']
        priority_input = request.form.get('priority', 'medium')
        priority = PriorityLevel[priority_input]

        feed_entry = FeedLog(
            batch_id=batch_id,
            log_date=log_date,
            feed_type=feed_type,
            quantity_kg=quantity_kg,
            cost=cost,
            notes=notes,
            priority=priority
        )
        db.session.add(feed_entry)
        db.session.commit()
        flash("Feed entry added successfully.", "success")
        return redirect(url_for('feed_resources'))

    logs = FeedLog.query.order_by(FeedLog.log_date.desc()).all()
    return render_template('admin_manage_feed.html', user=user, logs=logs, batches=batches)

@app.route('/feed-schedule-manager', methods=['GET', 'POST'])
def feed_schedule_manager():
    user = db.session.get(User, session.get('user_id'))
    if not user or user.role != 'manager':
        return redirect(url_for('login'))

    today_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('feed_schedule.html', user=user, today_date=today_date)


@app.route('/production-record')
def production_record():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    
    if not user or user.role != 'manager':
        return redirect(url_for('login'))
    
    from datetime import datetime
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('production_record.html', user=user, today_date=today_date)

# @app.route('/vaccination-schedule', methods=['GET', 'POST'])
@app.route('/vaccination-schedule')
def vaccination_schedule():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    if not user or user.role not in ['admin', 'manager']:
        return redirect(url_for('login'))

    batches = Batch.query.all()

    if request.method == 'POST':
        batch_id = request.form['batch_id']
        vaccine_name = request.form['vaccine_name']
        scheduled_date = datetime.strptime(request.form['scheduled_date'], '%Y-%m-%d').date()
        status = request.form['status']
        notes = request.form['notes']
        priority_input = request.form.get('priority', 'medium')
        priority = PriorityLevel[priority_input]

        new_vaccine = Vaccination(
            batch_id=batch_id,
            vaccine_name=vaccine_name,
            scheduled_date=scheduled_date,
            status=status,
            notes=notes,
            priority=priority
        )
        db.session.add(new_vaccine)
        db.session.commit()
        return redirect(url_for('manage_vaccinations'))

    vaccinations = Vaccination.query.order_by(Vaccination.scheduled_date.desc()).all()
    return render_template('admin_manage_vaccinations.html', user=user, vaccinations=vaccinations, batches=batches)

@app.route('/poultry-stock')
def poultry_stock():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    if not user or user.role != 'manager':
        return redirect(url_for('login'))

    # ✅ Sort batches by batch_id (i.e., batch name) in ascending order
    poultry_batches = PoultryBatch.query.order_by(PoultryBatch.batch_id.asc()).all()

    # ✅ Pass today's date for age calculation
    from datetime import datetime
    today = datetime.now().date()

    return render_template('poultry_stock.html', user=user, poultry_batches=poultry_batches, today=today)


@app.route('/shop')
def shop():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None

    products = Product.query.order_by(Product.name.asc()).all()  # fetch all products
    return render_template('shop.html', user=user, products=products)



@app.route('/track-orders')
def track_customer_orders():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    
    if not user or user.role != 'customer':
        return redirect(url_for('login'))
    
    # In a real application, you would fetch the user's orders from the database
    # For now, we'll just render the template with dummy data
    return render_template('track_orders.html', user=user)

@app.route('/farmer-dashboard')
def farmer_dashboard():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)


    if not user or user.role != 'farmer':
        return redirect(url_for('login'))

    return render_template('farmer_dashboard.html', user=user)

#puspita just add this
@app.route('/admin/manage-orders', methods=['GET', 'POST'])
def manage_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role not in ['admin', 'manager']:
        return redirect(url_for('login'))

    # Handle form submissions
    if request.method == 'POST':
        order_id = int(request.form['order_id'])
        new_status = request.form.get('status')
        delivery_man_id = request.form.get('delivery_man_id')

        order = Order.query.get(order_id)
        if order:
            if new_status:
                order.status = new_status
            if delivery_man_id:
                order.delivery_man_id = int(delivery_man_id)
            db.session.commit()
        return redirect(url_for('manage_orders'))

    # Fetch all orders
    orders = Order.query.all()
    now = datetime.utcnow()

    # Update priority based on emergency criteria
    for order in orders:
        urgent = (
            order.total_amount and order.total_amount > 1000
        ) or (
            order.delivery_date and order.delivery_date - now < timedelta(hours=6)
        )
        order.priority = PriorityLevel.high if urgent else PriorityLevel.medium

    db.session.commit()

    # Fetch again sorted by priority and order date
    orders = Order.query.order_by(Order.priority.desc(), Order.order_date.desc()).all()
    delivery_men = User.query.filter_by(role='delivery_man').all()

    return render_template('admin_manager_orders.html', user=user, orders=orders, delivery_men=delivery_men)

@app.route('/delivery/assigned-orders', methods=['GET', 'POST'])
def delivery_assigned_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))

    if request.method == 'POST':
        order_id = int(request.form['order_id'])
        new_status = request.form['status']
        order = Order.query.get(order_id)

        # Only allow updates if the order is assigned to this delivery man
        if order and order.delivery_man_id == user.id:
            order.status = new_status
            db.session.commit()

        return redirect(url_for('assigned_orders'))

    # Fetch only orders assigned to the logged-in delivery man
    assigned = Order.query.filter_by(delivery_man_id=user.id).order_by(Order.order_date.desc()).all()
    return render_template('assigned_orders.html', user=user, orders=assigned)


#====================================== 22nd April Arzoo added


@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)

    # Initialize cart in session if it doesn't exist
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    # If the product is already in cart, increase quantity
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += 1
        cart[str(product_id)]['subtotal'] = cart[str(product_id)]['quantity'] * product.unit_price
    else:
        cart[str(product_id)] = {
            'name': product.name,
            'image': product.image,
            'quantity': 1,
            'unit_price': product.unit_price,
            'subtotal': product.unit_price
        }

    session.modified = True  # Mark session as modified to save changes
    return jsonify({'success': True, 'message': f'{product.name} added to cart'})


@app.route('/cart')
def view_cart():
    user = db.session.get(User, session.get('user_id'))
    cart = session.get('cart', {})
    total = sum(item['subtotal'] for item in cart.values())
    return render_template('cart.html', user=user, cart=cart, total=total)


@app.route('/checkout', methods=['POST', 'GET'])
def checkout():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    if not user or user.role != 'customer':
        return redirect(url_for('login'))

    cart = session.get('cart')
    if not cart:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('shop'))

    # Calculate total
    total = sum(item['subtotal'] for item in cart.values())

    # Create Order
    new_order = Order(
        customer_id=user_id,
        status='Pending',
        total_amount=total,
        shipping_address=user.address,
        order_date=datetime.utcnow()
    )
    db.session.add(new_order)
    db.session.commit()  # Commit first to get the order ID

    # Create OrderItems
    for product_id, item in cart.items():
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=int(product_id),
            quantity=item['quantity'],
            price=item['unit_price']
        )
        db.session.add(order_item)

    db.session.commit()

    # Clear cart
    session.pop('cart', None)
    flash('Order placed successfully!', 'success')

    return redirect(url_for('track_customer_orders'))





if __name__ == '__main__':
    app.run(debug=True)
