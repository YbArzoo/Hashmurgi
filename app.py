import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, redirect, url_for
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Product, Order, OrderItem, DeliveryIssue, DeliveryPayment, Batch, Vaccination, Production, FeedLog, Sale, Invoice, PriorityLevel, PoultryBatch, HealthCheck, Notification, Task, Feeding
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
from models import db, User, Order, DeliveryPayment


#updated 24th april


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


#LANGUAGE API
from flask import session, redirect, url_for

@app.route('/set_language/<language>')
def set_language(language):
    if language in ['en', 'bn']:  # Only allow English ('en') and Bangla ('bn')
        session['language'] = language
    return redirect(url_for('home'))  # Redirect back to home page after language change






# Home page route
@app.route('/')
def home():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None
    #title = translate_to_bangla("Welcome to HashMurgi")
    #description = translate_to_bangla("Find the best poultry products here.")
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

    if not user or user.role != 'manager':
        return redirect(url_for('login'))

    query = request.args.get('q', '').strip()

    if query:
        products = Product.query.filter(
            (Product.name.ilike(f'%{query}%')) |
            (Product.category.ilike(f'%{query}%')) |
            (db.cast(Product.id, db.String).ilike(f'%{query}%'))
        ).order_by(Product.id.desc()).all()
    else:
        products = Product.query.order_by(Product.id.desc()).limit(5).all()

    return render_template('manager-dashboard.html', user=user, products=products, query=query)



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


@app.route('/track-orders')
def track_customer_orders():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    if not user or user.role != 'customer':
        return redirect(url_for('login'))

    # ✅ Fetch real customer orders
    status_filter = request.args.get('status')

    if status_filter and status_filter != 'All':
        orders = Order.query.filter_by(customer_id=user_id, status=status_filter).order_by(Order.order_date.desc()).all()
    else:
        orders = Order.query.filter_by(customer_id=user_id).order_by(Order.order_date.desc()).all()


    return render_template('track_orders.html', user=user, orders=orders)

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

    if not user or user.role != 'customer':
        return redirect(url_for('home'))

    # ✅ Fetch recent notifications for customer
    recent_notifications = Notification.query.filter(
        db.or_(
            Notification.for_user == user_id,
            Notification.for_role.like('%customer%')
        )
    ).order_by(Notification.created_at.desc()).limit(5).all()

    # ✅ Count unread notifications
    unread_count = Notification.query.filter(
        db.and_(
            Notification.is_read == False,
            db.or_(
                Notification.for_user == user_id,
                Notification.for_role.like('%customer%')
            )
        )
    ).count()

    return render_template(
        'customer_dashboard.html',
        user=user,
        recent_notifications=recent_notifications,
        unread_count=unread_count
    )



@app.route('/delivery-dashboard')
def delivery_dashboard():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    today = datetime.now().date()

    # Fetch recent notifications (customize query if needed)
    recent_notifications = Notification.query.filter(
        db.or_(
            Notification.for_user == user_id,
            Notification.for_role.like("%delivery_man%")
        )
    ).order_by(Notification.created_at.desc()).limit(5).all()

    unread_count = Notification.query.filter(
        db.and_(
            Notification.is_read == False,
            db.or_(
                Notification.for_user == user_id,
                Notification.for_role.like("%delivery_man%")
            )
        )
    ).count()

    return render_template('delivery_man_dashboard.html', 
                           user=user,
                           today_deliveries=3,  # Replace with real logic
                           pending_deliveries=2,
                           completed_deliveries=1,
                           recent_notifications=recent_notifications,
                           unread_count=unread_count)


# Remove or comment out the first update_order_status function
# @app.route('/update-order-status/<int:order_id>', methods=['GET', 'POST'])
# def update_order_status(order_id):
#     user_id = session.get('user_id')
#     user = db.session.get(User, user_id)
#     
#     if not user or user.role != 'delivery_man':
#         return redirect(url_for('login'))
#     
#     if request.method == 'POST':
#         # In a real application, you would update the order in the database
#         # For example:
#         # order = Order.query.get(order_id)
#         # if order and order.delivery_man_id == user_id:
#         #     order.status = request.form.get('status')
#         #     if order.status == 'Delivered':
#         #         order.delivered_at = datetime.utcnow()
#         #     db.session.commit()
#         #     flash('Order status updated successfully!', 'success')
#         
#         flash('Order status updated successfully!', 'success')
#     
#     # Redirect back to assigned orders page
#     return redirect(url_for('assigned_orders'))
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
    
    # Fetch orders assigned to this delivery person
    orders = Order.query.filter_by(delivery_man_id=user_id).all()
    
    # Fetch previous reports submitted by this delivery person
    user_reports = DeliveryIssue.query.filter_by(reported_by=user_id).order_by(DeliveryIssue.created_at.desc()).all()
    
    return render_template('report_issues.html', user=user, orders=orders, user_reports=user_reports)

@app.route('/submit-issue', methods=['POST'])
def submit_issue():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    # Get form data
    order_id = request.form.get('order_id')
    issue_type = request.form.get('issue_type')
    description = request.form.get('description')
    urgency = request.form.get('urgency')
    
    # Handle image upload if provided
    image_filename = None
    if 'image' in request.files and request.files['image'].filename:
        image = request.files['image']
        if allowed_file(image.filename):
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
    
    # Create new issue in database
    new_issue = DeliveryIssue(
        order_id=order_id,
        reported_by=user_id,
        issue_type=issue_type,
        description=description,
        image=image_filename,
        urgency=urgency,
        status='Pending',
        created_at=datetime.utcnow()
    )
    db.session.add(new_issue)
    db.session.commit()
    
    flash('Issue reported successfully!', 'success')
    return redirect(url_for('report_issues'))

# Add a new route for admins to view reported issues
@app.route('/admin/reported-issues', methods=['GET', 'POST'])
def admin_reported_issues():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role not in ['admin', 'manager']:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        issue_id = request.form.get('issue_id')
        new_status = request.form.get('status')
        
        issue = DeliveryIssue.query.get(issue_id)
        if issue:
            issue.status = new_status
            db.session.commit()
            flash('Issue status updated successfully!', 'success')
        
        return redirect(url_for('admin_reported_issues'))
    
    # Get all issues with reporter information
    issues = DeliveryIssue.query.join(User, DeliveryIssue.reported_by == User.id).add_entity(User).all()
    
    # Transform the query result into a more usable format
    formatted_issues = []
    for issue, reporter in issues:
        issue_dict = {
            'id': issue.id,
            'order_id': issue.order_id,
            'reporter': reporter,
            'issue_type': issue.issue_type,
            'description': issue.description,
            'image': issue.image,
            'urgency': issue.urgency,
            'status': issue.status,
            'created_at': issue.created_at
        }
        formatted_issues.append(issue_dict)
    
    return render_template('admin_reported_issues.html', user=user, issues=formatted_issues)
from flask import render_template, redirect, url_for, session
from datetime import datetime, timedelta
from models import db, User, Order, DeliveryPayment

@app.route('/delivery-income')
def delivery_income():
    # Retrieve user_id from session and check if user exists
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    # If user is not found or the user is not a 'delivery_man', redirect to login
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    # Get today's date
    today = datetime.now().date()
    
    # Calculate the start of the current month and week
    month_start = datetime(today.year, today.month, 1).date()
    week_start = today - timedelta(days=today.weekday())  # Monday of this week
    
    # Get completed orders for different time periods
    monthly_orders = Order.query.filter(
        Order.delivery_man_id == user_id,
        Order.status == 'Delivered',
        Order.delivery_date >= month_start
    ).all()
    
    weekly_orders = Order.query.filter(
        Order.delivery_man_id == user_id,
        Order.status == 'Delivered',
        Order.delivery_date >= week_start
    ).all()
    
    daily_orders = Order.query.filter(
        Order.delivery_man_id == user_id,
        Order.status == 'Delivered',
        Order.delivery_date == today
    ).all()
    
    # Calculate income
    monthly_income = sum(order.total_amount for order in monthly_orders)
    weekly_income = sum(order.total_amount for order in weekly_orders)
    daily_income = sum(order.total_amount for order in daily_orders)
    
    # Get payment history for this delivery man
    payments = DeliveryPayment.query.filter_by(delivery_man_id=user_id).order_by(DeliveryPayment.payment_date.desc()).all()
    
    # Create chart data for the template
    chart_data = {
        'weekly': {
            'labels': [(today - timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)],
            'datasets': [{
                'label': 'Daily Income',
                'data': [0] * 7,  # Placeholder data - you would calculate real values
                'borderColor': 'rgb(75, 192, 192)',
                'tension': 0.1
            }]
        },
        'monthly': {
            'labels': [(today - timedelta(days=i)).strftime('%d %b') for i in range(29, -1, -1)],
            'datasets': [{
                'label': 'Daily Income',
                'data': [0] * 30,  # Placeholder data
                'borderColor': 'rgb(75, 192, 192)',
                'tension': 0.1
            }]
        },
        'yearly': {
            'labels': [(today.replace(day=1) - timedelta(days=i*30)).strftime('%b %Y') for i in range(11, -1, -1)],
            'datasets': [{
                'label': 'Monthly Income',
                'data': [0] * 12,  # Placeholder data
                'borderColor': 'rgb(75, 192, 192)',
                'tension': 0.1
            }]
        }
    }
    
    # Pass all calculated values to the template
    return render_template('delivery_income.html', 
                           user=user, 
                           monthly_income=monthly_income,
                           monthly_deliveries=len(monthly_orders),
                           weekly_income=weekly_income,
                           weekly_deliveries=len(weekly_orders),
                           daily_income=daily_income,
                           daily_deliveries=len(daily_orders),
                           payments=payments,
                           chart_data=chart_data)  # Add chart_data here

@app.route('/view-report/<int:report_id>')
def view_report(report_id):
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user:
        return redirect(url_for('login'))
    
    # Fetch the report from the database
    report = DeliveryIssue.query.get_or_404(report_id)
    
    # Check if the user is authorized to view this report
    if user.role == 'delivery_man' and report.reported_by != user_id:
        flash('You are not authorized to view this report', 'danger')
        return redirect(url_for('report_issues'))
    
    # Get the associated order
    order = Order.query.get(report.order_id)
    
    return render_template('view_report.html', user=user, report=report, order=order)
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
    
    if not user:
        return redirect(url_for('login'))
    
    order = Order.query.get_or_404(order_id)
    
    # Check permissions based on user role
    if user.role == 'customer' and order.customer_id != user_id:
        flash('You are not authorized to view this order', 'danger')
        return redirect(url_for('track_customer_orders'))
    elif user.role == 'delivery_man' and order.delivery_man_id != user_id:
        flash('You are not authorized to view this order', 'danger')
        return redirect(url_for('assigned_orders'))
    elif user.role not in ['admin', 'manager', 'customer', 'delivery_man']:
        return redirect(url_for('home'))
    
    return render_template('order_details.html', user=user, order=order)

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
    try:
        # Get user information and validate
        user_id = session.get('user_id')
        if not user_id:
            print(f"[WARNING] No user_id in session, redirecting to login")

            return redirect(url_for('login'))
            
        user = db.session.get(User, user_id)
        if not user or user.role != 'farmer':
            print(f"[WARNING] No user_id in session, redirecting to login")

            return redirect(url_for('login'))
        
        # Handle POST request for completing tasks
        if request.method == 'POST':
            task_id = request.form.get('task_id')
            action = request.form.get('action')
            
            if task_id and action == 'complete':
                try:
                    task = Task.query.get(task_id)
                    
                    if task and task.assigned_to == user_id:
                        task.status = 'completed'
                        task.completed_at = datetime.utcnow()
                        db.session.commit()
                        flash('Task marked as completed!', 'success')
                    else:
                        print(f"[WARNING] No user_id in session, redirecting to login")

                        flash('Task not found or not assigned to you', 'error')
                except Exception as e:
                    print(f"Error fetching tasks: {str(e)}")
                    db.session.rollback()
                    flash('Error marking task as completed. Please try again.', 'error')
            
            return redirect(url_for('daily_tasks'))
        
        # Get today's date for the form
        today_date = datetime.now().strftime('%Y-%m-%d')
        today = datetime.now().date()
        
        # Get tasks with proper error handling
        try:
            # Today's tasks
            today_tasks = Task.query.filter(
                Task.assigned_to == user_id,
                Task.due_date == today
            ).order_by(Task.priority.desc()).all()
            
            # Tomorrow's tasks
            tomorrow = today + timedelta(days=1)
            tomorrow_tasks = Task.query.filter(
                Task.assigned_to == user_id,
                Task.due_date == tomorrow
            ).order_by(Task.priority.desc()).all()
            
            # This week's tasks (excluding today and tomorrow)
            week_end = today + timedelta(days=7)
            week_tasks = Task.query.filter(
                Task.assigned_to == user_id,
                Task.due_date > tomorrow,
                Task.due_date <= week_end
            ).order_by(Task.due_date.asc(), Task.priority.desc()).all()
            
            print(f"[DEBUG] Retrieved tasks for user {user_id}: today={len(today_tasks)}, tomorrow={len(tomorrow_tasks)}, week={len(week_tasks)}")

        except Exception as e:
            print(f"Error fetching tasks: {str(e)}")
            today_tasks = []
            tomorrow_tasks = []
            week_tasks = []
            flash("Could not load tasks. Please try again later.", "error")
        
        return render_template('farmer_daily_tasks.html', 
                              user=user, 
                              today_date=today_date,
                              today_tasks=today_tasks,
                              tomorrow_tasks=tomorrow_tasks,
                              week_tasks=week_tasks)
    except Exception as e:
        print(f"Error fetching tasks: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('farmer_dashboard'))


@app.route('/poultry-status-farmer', methods=['GET', 'POST'])
def poultry_status_farmer():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user or user.role != 'farmer':
        return redirect(url_for('login'))
    
    # Get today's date for the form
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    # Get available batches for the dropdown
    batches = PoultryBatch.query.all()
    
    # Get recent health checks for this farmer
    recent_health_checks = HealthCheck.query.filter_by(recorded_by=user_id).order_by(HealthCheck.check_date.desc()).limit(5).all()
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'count_update':
            # Handle count update form submission
            batch_id = request.form.get('batch_id')
            new_count = int(request.form.get('new_count'))
            reason = request.form.get('reason')
            notes = request.form.get('notes', '')
            
            # Get the batch
            batch = PoultryBatch.query.filter_by(batch_id=batch_id).first()
            
            if batch:
                # Calculate the difference
                count_difference = new_count - batch.count
                old_count = batch.count
                
                # Update the batch count
                batch.count = new_count
                
                # Create a notification for admins and managers
                notification_title = f"Poultry Count Updated: {batch_id}"
                notification_message = f"Count changed from {old_count} to {new_count} ({count_difference:+d}). Reason: {reason}. Notes: {notes}"
                
                notification = Notification(
                    title=notification_title,
                    message=notification_message,
                    category='count_update',
                    priority='high' if abs(count_difference) > 10 else 'normal',
                    created_by=user_id,
                    related_batch=batch_id
                )
                
                db.session.add(notification)
                db.session.commit()
                flash('Poultry count updated successfully!', 'success')
            else:
                flash('Batch not found!', 'danger')
                
        elif form_type == 'health_check':
            # Handle health check form submission
            batch_id = request.form.get('health_batch_id')
            health_status = request.form.get('health_status')
            feed_consumption = request.form.get('feed_consumption')
            water_consumption = request.form.get('water_consumption')
            mortality = int(request.form.get('mortality', 0))
            health_notes = request.form.get('health_notes', '')
            check_date = datetime.strptime(request.form.get('health_date'), '%Y-%m-%d').date()
            
            # Create a new health check record
            health_check = HealthCheck(
                batch_id=batch_id,
                check_date=check_date,
                health_status=health_status,
                feed_consumption=feed_consumption,
                water_consumption=water_consumption,
                mortality=mortality,
                notes=health_notes,
                recorded_by=user_id
            )
            
            # Create a notification
            notification_title = f"Health Check: {batch_id}"
            notification_message = f"Status: {health_status}. Mortality: {mortality}. Notes: {health_notes}"
            
            # Set priority based on health status and mortality
            priority = 'normal'
            if health_status in ['poor', 'critical'] or mortality > 0:
                priority = 'high'
            if health_status == 'critical' or mortality > 5:
                priority = 'urgent'
                
            notification = Notification(
                title=notification_title,
                message=notification_message,
                category='health_check',
                priority=priority,
                created_by=user_id,
                related_batch=batch_id
            )
            
            db.session.add(health_check)
            db.session.add(notification)
            db.session.commit()
            flash('Health check recorded successfully!', 'success')
        
        return redirect(url_for('poultry_status_farmer'))
    
    return render_template('poultry_status_farmer.html', 
                          user=user, 
                          today_date=today_date,
                          batches=batches,
                          recent_health_checks=recent_health_checks)

@app.route('/feed-schedule', methods=['GET', 'POST'])
def feed_schedule():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
            
        user = db.session.get(User, user_id)
        if not user or user.role != 'farmer':
            return redirect(url_for('login'))
        
        # Get today's date
        today = datetime.now().date()
        
        if request.method == 'POST':
            feeding_id = request.form.get('feeding_id')
            action = request.form.get('action')
            
            if feeding_id and action == 'complete':
                try:
                    feeding = Feeding.query.get(feeding_id)
                    
                    if feeding:
                        feeding.status = 'completed'
                        feeding.completed_by = user_id
                        feeding.completed_at = datetime.utcnow()
                        
                        # Create notification for admins and managers
                        notification_title = f"Feeding Completed: {feeding.batch_id}"
                        notification_message = f"Feed type: {feeding.feed_type}, Quantity: {feeding.quantity}kg. Completed by {user.name}."
                        
                        notification = Notification(
                            title=notification_title,
                            message=notification_message,
                            category='feeding',
                            priority='normal',
                            created_by=user_id,
                            related_batch=feeding.batch_id
                        )
                        
                        db.session.add(notification)
                        db.session.commit()
                        flash('Feeding marked as completed!', 'success')
                except Exception as e:
                    print(f"Error fetching tasks: {str(e)}")
                    db.session.rollback()
                    flash('Error marking feeding as completed. Please try again.', 'error')
            
            return redirect(url_for('feed_schedule'))
        
        # Get today's feedings with error handling
        try:
            today_feedings = Feeding.query.filter(
                Feeding.date == today
            ).order_by(Feeding.time.asc()).all()
        except Exception as e:
            print(f"Error fetching tasks: {str(e)}")
            today_feedings = []
        
        # Get upcoming feedings with error handling
        try:
            upcoming_feedings = Feeding.query.filter(
                Feeding.date > today
            ).order_by(Feeding.date.asc(), Feeding.time.asc()).all()
        except Exception as e:
            print(f"Error fetching tasks: {str(e)}")
            upcoming_feedings = []
        
        # Get recent completed feedings with error handling
        try:
            completed_feedings = Feeding.query.filter(
                Feeding.status == 'completed'
            ).order_by(Feeding.completed_at.desc()).limit(5).all()
        except Exception as e:
            print(f"Error fetching tasks: {str(e)}")
            completed_feedings = []
        
        # Get feed inventory (you might want to create a separate model for this)
        feed_inventory = [
            {"feed_type": "Layer Feed", "stock": 250, "unit": "kg", "threshold": 100, "last_restocked": "Apr 10, 2025", "status": "Adequate"},
            {"feed_type": "Broiler Feed", "stock": 120, "unit": "kg", "threshold": 100, "last_restocked": "Apr 8, 2025", "status": "Adequate"},
            {"feed_type": "Chick Starter", "stock": 50, "unit": "kg", "threshold": 75, "last_restocked": "Apr 5, 2025", "status": "Low Stock"}
        ]
        
        # Get unread notifications count
        try:
            unread_count = Notification.query.filter(
                db.and_(
                    Notification.is_read == False,
                    db.or_(
                        Notification.for_user == user_id,
                        db.and_(
                            Notification.for_role.like("%farmer%"),
                            Notification.for_role != None
                        )
                    )
                )
            ).count()
        except Exception as e:
            print(f"Error fetching tasks: {str(e)}")
            unread_count = 0
        
        return render_template('feed_schedule.html', 
                              user=user, 
                              today_feedings=today_feedings,
                              upcoming_feedings=upcoming_feedings,
                              completed_feedings=completed_feedings,
                              feed_inventory=feed_inventory,
                              today_date=today.strftime('%Y-%m-%d'),
                              unread_count=unread_count)
    except Exception as e:
        print(f"Error fetching tasks: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('farmer_dashboard'))


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
    if not user_id:
        return redirect(url_for('login'))
        
    user = db.session.get(User, user_id)
    if not user:
        return redirect(url_for('login'))

    try:
        # Dynamic filtering
        query = Notification.query

        if user.role in ['admin', 'manager']:
            # Admins and managers see all
            filtered_notifications = query.order_by(Notification.created_at.desc()).all()
        else:
            # Customers, Farmers, Delivery Men see only targeted notifications
            filtered_notifications = query.filter(
                db.or_(
                    Notification.for_user == user_id,
                    Notification.for_role.like(f"%{user.role}%")
                )
            ).order_by(Notification.created_at.desc()).all()

        unread_count = Notification.query.filter(
            db.and_(
                Notification.is_read == False,
                db.or_(
                    Notification.for_user == user_id,
                    Notification.for_role.like(f"%{user.role}%")
                )
            )
        ).count()

    except Exception as e:
        print(f"Notification error: {str(e)}")
        filtered_notifications = []
        unread_count = 0

    return render_template('notifications.html', 
                           user=user, 
                           all_notifications=filtered_notifications,
                           unread_count=unread_count)



@app.route('/mark-notification-read/<int:notification_id>')
def mark_notification_read(notification_id):
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user:
        return redirect(url_for('login'))

    notification = Notification.query.get_or_404(notification_id)

    # Allow only if user is admin/manager OR it's meant for them
    if user.role in ['admin', 'manager'] or notification.for_user == user_id or notification.for_role == user.role:
        notification.is_read = True
        db.session.commit()
        flash('Notification marked as read', 'success')
    else:
        flash('You are not authorized to mark this notification', 'danger')

    return redirect(url_for('notifications'))


@app.route('/delete-notification/<int:notification_id>')
def delete_notification(notification_id):
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user:
        return redirect(url_for('login'))

    notification = Notification.query.get_or_404(notification_id)

    # Allow delete only for admin or the creator
    if user.role == 'admin' or notification.created_by == user.id:
        db.session.delete(notification)
        db.session.commit()
        flash('Notification deleted successfully.', 'success')
    else:
        flash('Unauthorized to delete notification.', 'danger')

    return redirect(url_for('notifications'))



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
# def poultry_stock():
#     user_id = session.get('user_id')
#     user = db.session.get(User, user_id)

#     if not user or user.role != 'manager':
#         return redirect(url_for('login'))

#     # ✅ Sort batches by batch_id (i.e., batch name) in ascending order
#     poultry_batches = PoultryBatch.query.order_by(PoultryBatch.batch_id.asc()).all()

#     # ✅ Pass today's date for age calculation
#     from datetime import datetime
#     today = datetime.now().date()

#     return render_template('poultry_stock.html', user=user, poultry_batches=poultry_batches, today=today)
@app.route('/poultry-stock')
def poultry_stock():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    if not user or user.role != 'manager':
        return redirect(url_for('login'))

    # Existing batch filter
    search = request.args.get('search', '').strip()
    poultry_batches = PoultryBatch.query.filter(
        (PoultryBatch.batch_id.ilike(f"%{search}%")) |
        (PoultryBatch.bird_type.ilike(f"%{search}%")) |
        (db.cast(PoultryBatch.arrival_date, db.String).ilike(f"%{search}%")) |
        (PoultryBatch.status.ilike(f"%{search}%"))
    ).order_by(PoultryBatch.created_at.desc()).limit(5).all() if search else PoultryBatch.query.order_by(PoultryBatch.created_at.desc()).limit(5).all()

    # Production filter
    prod_search = request.args.get('prod_search', '').strip()
    productions = Production.query.join(Batch).filter(
        (Batch.batch_name.ilike(f"%{prod_search}%")) |
        (db.cast(Production.production_date, db.String).ilike(f"%{prod_search}%")) |
        (db.cast(Production.egg_count, db.String).ilike(f"%{prod_search}%")) |
        (db.cast(Production.meat_weight_kg, db.String).ilike(f"%{prod_search}%"))
    ).order_by(Production.production_date.desc()).all() if prod_search else Production.query.order_by(Production.production_date.desc()).limit(5).all()

    # 🆕 Feed filter
    feed_search = request.args.get('feed_search', '').strip()
    feed_logs = FeedLog.query.join(Batch).filter(
        (db.cast(FeedLog.id, db.String).ilike(f"%{feed_search}%")) |
        (FeedLog.feed_type.ilike(f"%{feed_search}%")) |
        (Batch.batch_name.ilike(f"%{feed_search}%"))
    ).order_by(FeedLog.log_date.desc()).all() if feed_search else FeedLog.query.order_by(FeedLog.log_date.desc()).limit(5).all()

    today = datetime.now().date()
    return render_template('poultry_stock.html', user=user, today=today,
                           poultry_batches=poultry_batches,
                           productions=productions,
                           feed_logs=feed_logs,
                           search=search,
                           prod_search=prod_search,
                           feed_search=feed_search)


@app.route('/shop')
def shop():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None

    products = Product.query.order_by(Product.name.asc()).all()  # fetch all products
    return render_template('shop.html', user=user, products=products)




@app.route('/farmer-dashboard')
def farmer_dashboard():
    try:
        # Get user information
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))

        user = db.session.get(User, user_id)
        if not user or user.role != 'farmer':
            return redirect(url_for('login'))

        # Initialize variables to avoid "not defined" errors
        today_tasks = []
        tomorrow_tasks = []
        week_tasks = []

        # Get today's tasks
        try:
            today = datetime.now().date()
            today_tasks = Task.query.filter(
                Task.assigned_to == user_id,
                Task.due_date == today
            ).order_by(Task.priority.desc()).all()
        except Exception as e:
            print(f"Error fetching today's tasks: {str(e)}")
            flash("Could not load today's tasks.", "error")

        # Get poultry batches
        try:
            batches = PoultryBatch.query.all()
        except Exception as e:
            print(f"Error fetching poultry batches: {str(e)}")
            batches = []
            flash("Could not load poultry batch data.", "error")

        # Get health checks
        try:
            health_checks = HealthCheck.query.filter_by(recorded_by=user_id).all()
        except Exception as e:
            print(f"Error fetching health checks: {str(e)}")
            health_checks = []

        # Get recent notifications
        try:
            recent_notifications = Notification.query.filter(
                db.or_(
                    Notification.for_user == user_id,
                    db.and_(
                        Notification.for_role.like("%farmer%"),
                        Notification.for_role != None
                    )
                )
            ).order_by(Notification.created_at.desc()).limit(5).all()
        except Exception as e:
            print(f"Error fetching notifications: {str(e)}")
            recent_notifications = []

        # Get unread notifications count
        try:
            unread_count = Notification.query.filter(
                db.and_(
                    Notification.is_read == False,
                    db.or_(
                        Notification.for_user == user_id,
                        db.and_(
                            Notification.for_role.like("%farmer%"),
                            Notification.for_role != None
                        )
                    )
                )
            ).count()
        except Exception as e:
            print(f"Error fetching unread count: {str(e)}")
            unread_count = 0

        # Only print debug once
        print(f"[DEBUG] Retrieved tasks for user {user_id}: today={len(today_tasks)}, tomorrow={len(tomorrow_tasks)}, week={len(week_tasks)}")

        return render_template('farmer_dashboard.html',
                               user=user,
                               today_tasks=today_tasks,
                               batches=batches,
                               health_checks=health_checks,
                               recent_notifications=recent_notifications,
                               unread_count=unread_count)
    except Exception as e:
        print(f"Unexpected error in farmer_dashboard: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('home'))


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
                new_dm_id = int(delivery_man_id)

                if order.delivery_man_id != new_dm_id:
                    order.delivery_man_id = new_dm_id

                    delivery_man = User.query.get(new_dm_id)
                    if delivery_man:
                        notification = Notification(
                            title=f"New Delivery Assigned - Order #{order.id}",
                            message=f"You have been assigned to deliver Order #{order.id}. Please check your dashboard for details.",
                            category="order_assignment",
                            priority="normal",
                            for_user=delivery_man.id,
                            for_role="delivery_man",
                            is_read=False,
                            created_at=datetime.utcnow(),
                            created_by=user.id
                        )
                        db.session.add(notification)

            db.session.commit()


    # Fetch again sorted by priority and order date
    orders = Order.query.order_by(Order.priority.desc(), Order.order_date.desc()).all()
    delivery_men = User.query.filter_by(role='delivery_man').all()

    return render_template('admin_manager_orders.html', user=user, orders=orders, delivery_men=delivery_men)


@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        return jsonify({"error": "Please login first"}), 401
    
    user = User.query.get(session['user_id'])
    if not user or user.role != 'customer':
        return jsonify({"error": "Only customers can add to cart"}), 403
    
    product = Product.query.get_or_404(product_id)
    
    # Initialize cart in session if it doesn't exist
    if 'cart' not in session:
        session['cart'] = []
    
    # Check if product already in cart
    cart = session['cart']
    product_in_cart = False
    
    for item in cart:
        if item['product_id'] == product_id:
            item['quantity'] += 1
            product_in_cart = True
            break
    
    if not product_in_cart:
        cart.append({
            'product_id': product_id,
            'name': product.name,
            'price': product.unit_price,
            'quantity': 1
        })
    
    session['cart'] = cart
    # Force the session to update
    session.modified = True
    
    return jsonify({"success": True, "message": "Product added to cart", "cart_count": len(cart)}), 200
# Add this route to view the cart
@app.route('/cart')
def view_cart():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None
    
    if not user or user.role != 'customer':
        return redirect(url_for('login'))
    
    cart = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    
    return render_template('cart.html', user=user, cart=cart, total=total)

# Add this route to update cart quantities
@app.route('/update-cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    if 'user_id' not in session or 'cart' not in session:
        return jsonify({"error": "Invalid session"}), 400
    
    quantity = request.json.get('quantity', 0)
    
    if quantity <= 0:
        # Remove item from cart
        session['cart'] = [item for item in session['cart'] if item['product_id'] != product_id]
    else:
        # Update quantity
        for item in session['cart']:
            if item['product_id'] == product_id:
                item['quantity'] = quantity
                break
    
    return jsonify({"success": True}), 200

# Add this route to remove items from cart
@app.route('/remove-from-cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['product_id'] != product_id]
    
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user or user.role != 'customer':
        return redirect(url_for('login'))
    
    cart = session.get('cart', [])
    if not cart:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('shop'))
    
    total = sum(item['price'] * item['quantity'] for item in cart)
    
    if request.method == 'POST':
        shipping_address = request.form.get('shipping_address')
        if not shipping_address:
            flash('Shipping address is required', 'danger')
            return render_template('checkout.html', user=user, cart=cart, total=total)
        
        # Create a new order
        new_order = Order(
            customer_id=user.id,
            status='Pending',
            total_amount=total,
            shipping_address=shipping_address,
            order_date=datetime.utcnow()
        )
        db.session.add(new_order)
        db.session.flush()  # This assigns an ID to new_order
        
        # Add order items
        for item in cart:
            product = Product.query.get(item['product_id'])
            if product:
                order_item = OrderItem(
                    order_id=new_order.id,
                    product_id=product.id,
                    quantity=item['quantity'],
                    price=product.unit_price
                )
                db.session.add(order_item)
                
                # Update product quantity (optional)
                product.quantity = max(0, product.quantity - item['quantity'])
        
        db.session.commit()
        
        # Clear the cart
        session.pop('cart', None)
        
        flash('Order placed successfully!', 'success')
        # return redirect(url_for('order_confirmation', order_id=new_order.id))
        return redirect(url_for('track_customer_orders'))

    
    return render_template('checkout.html', user=user, cart=cart, total=total)

# Add this route to debug the cart
@app.route('/debug-cart')
def debug_cart():
    cart = session.get('cart', [])
    return jsonify({
        'cart': cart,
        'cart_length': len(cart),
        'session_keys': list(session.keys())
    })

@app.route('/assigned-orders')
def assigned_orders():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    # Fetch orders from the database
    pending_orders = Order.query.filter_by(
        delivery_man_id=user_id,
        status='Pending'
    ).order_by(Order.order_date.desc()).all()
    
    in_transit_orders = Order.query.filter_by(
        delivery_man_id=user_id,
        status='In Transit'
    ).order_by(Order.order_date.desc()).all()
    
    completed_orders = Order.query.filter_by(
        delivery_man_id=user_id,
        status='Delivered'
    ).order_by(Order.order_date.desc()).all()
    
    return render_template('assigned_orders.html', 
                          user=user, 
                          pending_orders=pending_orders,
                          in_transit_orders=in_transit_orders,
                          completed_orders=completed_orders)

@app.route('/update-order-status/<int:order_id>', methods=['GET', 'POST'])
def delivery_update_order_status(order_id):
    print(f"DEBUG: Accessing delivery_update_order_status with order_id={order_id}")
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user or user.role != 'delivery_man':
        return redirect(url_for('login'))
    
    order = Order.query.get_or_404(order_id)
    
    if order.delivery_man_id != user_id:
        flash('You are not authorized to update this order', 'danger')
        return redirect(url_for('assigned_orders'))
    
    if request.method == 'POST':
        new_status = request.form.get('status')
        notes = request.form.get('notes', '')

        print(f"DEBUG: Updating order {order_id} status to {new_status}")
        
        order.status = new_status
        

        if new_status == 'Delivered':
            order.delivery_date = datetime.utcnow()

            existing_payment = DeliveryPayment.query.filter_by(
                delivery_man_id=user_id,
                order_id=order.id
            ).first()

            if not existing_payment:
                print(f"Creating payment for Order #{order.id} by Delivery Man #{user_id}")
                payment = DeliveryPayment(
                    delivery_man_id=user_id,
                    order_id=order.id,
                    amount=100,
                    method='Cash',
                    status='Completed',
                    payment_date=datetime.utcnow()
                )
                db.session.add(payment)
                print("Payment prepared for commit.")
            else:
                print(f"Payment already exists for Order #{order.id}")

                # Send notification to the customer about the new delivery status
        
        notification = Notification(
            title=f"Order #{order.id} Status Updated",
            message=f"Your order is now marked as '{new_status}' by the delivery man.",
            category="order_update",
            priority="normal" if new_status != "Delivered" else "high",
            for_user=order.customer_id,
            for_role="customer",
            is_read=False,
            created_at=datetime.utcnow(),
            created_by=user.id
        )
        db.session.add(notification)
        
        
        db.session.commit()
        print(f"DB committed for order #{order.id} update.")
        
        flash('Order status updated successfully!', 'success')
        return redirect(url_for('assigned_orders'))

    return render_template('update_order_status.html', user=user, order=order)



#====================================== 23rd April Arzoo added

@app.route('/admin/income')
def admin_income():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user or user.role != 'admin':
        return redirect(url_for('login'))

    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # Fetch Sales and Payments for admin income
    sales = Sale.query.all()
    daily_income = sum(s.total_amount for s in sales if s.sale_date == today)
    weekly_income = sum(s.total_amount for s in sales if s.sale_date >= week_start)
    monthly_income = sum(s.total_amount for s in sales if s.sale_date >= month_start)

    # For delivery man income
    delivery_payments = DeliveryPayment.query.order_by(DeliveryPayment.payment_date.desc()).all()

    # Calculate monthly, weekly, and daily payment amounts for delivery men
    monthly_deliveries = len([p for p in delivery_payments if p.payment_date.date() >= month_start])
    weekly_deliveries = len([p for p in delivery_payments if p.payment_date.date() >= week_start])
    daily_deliveries = len([p for p in delivery_payments if p.payment_date.date() == today])

    # Create chart data in a format that is JSON serializable
    chart_data = {
        'weekly': {
            'labels': [(today - timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)],
            'datasets': [{
                'label': 'Daily Income',
                'data': [daily_income] * 7,  # Replace with actual weekly data if needed
                'borderColor': 'rgb(75, 192, 192)',
                'tension': 0.1
            }]
        },
        'monthly': {
            'labels': [(today - timedelta(days=i)).strftime('%d %b') for i in range(29, -1, -1)],
            'datasets': [{
                'label': 'Daily Income',
                'data': [daily_income] * 30,  # Replace with actual monthly data if needed
                'borderColor': 'rgb(75, 192, 192)',
                'tension': 0.1
            }]
        },
        'yearly': {
            'labels': [(today.replace(day=1) - timedelta(days=i*30)).strftime('%b %Y') for i in range(11, -1, -1)],
            'datasets': [{
                'label': 'Monthly Income',
                'data': [monthly_income] * 12,  # Replace with actual yearly data if needed
                'borderColor': 'rgb(75, 192, 192)',
                'tension': 0.1
            }]
        }
    }

    return render_template('admin_income.html', 
                           user=user, 
                           daily_income=daily_income,
                           weekly_income=weekly_income,
                           monthly_income=monthly_income,
                           delivery_payments=delivery_payments,
                           daily_deliveries=daily_deliveries,
                           weekly_deliveries=weekly_deliveries,
                           monthly_deliveries=monthly_deliveries,
                           chart_data=chart_data)


#=================== 1st may 2025

@app.route('/admin/manage-tasks', methods=['GET', 'POST'])
def manage_tasks():
    try:
        user_id = session.get('user_id')
        user = db.session.get(User, user_id)
        
        if not user or user.role not in ['admin', 'manager']:
            return redirect(url_for('login'))
        
        # Get all farmers for the assignment dropdown
        farmers = User.query.filter_by(role='farmer').all()
        
        if request.method == 'POST':
            try:
                # Extract form data
                name = request.form.get('name')
                category = request.form.get('category')
                due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
                priority = request.form.get('priority')
                description = request.form.get('description')
                assigned_to = request.form.get('assigned_to')
                
                # Create new task
                new_task = Task(
                    name=name,
                    category=category,
                    due_date=due_date,
                    priority=priority,
                    description=description,
                    status='pending',
                    created_by=user_id,
                    assigned_to=assigned_to
                )
                
                db.session.add(new_task)
                db.session.commit()
                
                flash('Task created successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating task: {str(e)}', 'error')
                print(f"Error fetching tasks: {str(e)}")
            return redirect(url_for('manage_tasks'))
        
        # Get all tasks with error handling
        try:
            # Use a safer query that doesn't rely on the assigned_to column
            # until we're sure it exists
            tasks = db.session.query(Task).order_by(Task.due_date.asc()).all()
        except Exception as e:
            print(f"Error fetching tasks: {str(e)}")
            tasks = []
            flash("Could not load tasks. Please run the database migration first.", "error")
        
        # Get today's date for the form
        today_date = datetime.now().strftime('%Y-%m-%d')
        
        return render_template('admin_manage_tasks.html', 
                              user=user, 
                              tasks=tasks, 
                              farmers=farmers, 
                              today_date=today_date)
    except Exception as e:
        print(f"Error fetching tasks: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('home'))




@app.route('/admin/edit-task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user or user.role not in ['admin', 'manager']:
        return redirect(url_for('login'))
    
    task = Task.query.get_or_404(task_id)
    farmers = User.query.filter_by(role='farmer').all()
    
    if request.method == 'POST':
        task.name = request.form.get('name')
        task.category = request.form.get('category')
        task.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        task.priority = request.form.get('priority')
        task.description = request.form.get('description')
        task.assigned_to = request.form.get('assigned_to')
        task.status = request.form.get('status')
        
        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('manage_tasks'))
    
    return render_template('admin_edit_task.html', user=user, task=task, farmers=farmers)



@app.route('/admin/feed-schedule', methods=['GET', 'POST'])
def admin_feed_schedule():
    try:
        user_id = session.get('user_id')
        user = db.session.get(User, user_id)
        
        if not user or user.role not in ['admin', 'manager']:
            return redirect(url_for('login'))
        
        # Get all batches for the dropdown
        batches = PoultryBatch.query.all()
        
        if request.method == 'POST':
            try:
                # Extract form data
                date = datetime.strptime(request.form.get('feeding_date'), '%Y-%m-%d').date()
                time = datetime.strptime(request.form.get('feeding_time'), '%H:%M').time()
                batch_id = request.form.get('batch_id')
                feed_type = request.form.get('feed_type')
                quantity = float(request.form.get('quantity'))
                status = request.form.get('status')
                notes = request.form.get('notes', '')
                
                # Create new feeding schedule
                new_feeding = Feeding(
                    date=date,
                    time=time,
                    batch_id=batch_id,
                    feed_type=feed_type,
                    quantity=quantity,
                    status=status,
                    notes=notes,
                    recorded_by=user_id,
                    created_by=user_id
                )
                
                db.session.add(new_feeding)
                db.session.commit()
                
                flash('Feed schedule created successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating feed schedule: {str(e)}', 'error')
                print(f"Error in feed schedule creation: {str(e)}")
            
            return redirect(url_for('admin_feed_schedule'))
        
        # Get today's date for the form
        today_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get all feeding schedules with proper error handling
        try:
            # Use outerjoin to handle potential missing relationships
            feedings = (Feeding.query
                        .outerjoin(User, Feeding.recorded_by == User.id)
                        .order_by(Feeding.date.desc(), Feeding.time.asc())
                        .all())
        except Exception as e:
            print(f"Error fetching feedings: {str(e)}")
            feedings = []  # Fallback to empty list if query fails
        
        # Get unread notifications count for the sidebar
        try:
            unread_count = Notification.query.filter_by(is_read=False).count()
        except Exception as e:
            print(f"Error fetching notifications count: {str(e)}")
            unread_count = 0
        
        return render_template('admin_feed_schedule.html', 
                              user=user, 
                              batches=batches,
                              feedings=feedings,
                              today_date=today_date,
                              unread_count=unread_count)
    
    except Exception as e:
        print(f"Unexpected error in admin_feed_schedule: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('home'))

@app.route('/admin/edit-feeding/<int:feeding_id>', methods=['GET', 'POST'])
def edit_feeding():
    try:
        user_id = session.get('user_id')
        user = db.session.get(User, user_id)
        
        if not user or user.role not in ['admin', 'manager']:
            return redirect(url_for('login'))
        
        feeding = Feeding.query.get_or_404(feeding_id)
        batches = PoultryBatch.query.all()
        
        if request.method == 'POST':
            try:
                feeding.date = datetime.strptime(request.form.get('feeding_date'), '%Y-%m-%d').date()
                feeding.time = datetime.strptime(request.form.get('feeding_time'), '%H:%M').time()
                feeding.batch_id = request.form.get('batch_id')
                feeding.feed_type = request.form.get('feed_type')
                feeding.quantity = float(request.form.get('quantity'))
                feeding.status = request.form.get('status')
                feeding.notes = request.form.get('notes', '')
                
                db.session.commit()
                flash('Feeding schedule updated successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating feeding schedule: {str(e)}', 'error')
                print(f"Error in edit_feeding: {str(e)}")
                
            return redirect(url_for('admin_feed_schedule'))
        
        return render_template('edit_feeding.html', 
                              user=user, 
                              feeding=feeding,
                              batches=batches)
    except Exception as e:
        print(f"Unexpected error in edit_feeding: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('admin_feed_schedule'))


@app.route('/admin/delete-feeding/<int:feeding_id>')
def delete_feeding(feeding_id):
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user or user.role not in ['admin', 'manager']:
        return redirect(url_for('login'))
    
    feeding = Feeding.query.get_or_404(feeding_id)
    
    db.session.delete(feeding)
    db.session.commit()
    
    flash('Feeding schedule deleted successfully!', 'success')
    return redirect(url_for('admin_feed_schedule'))


if __name__ == '__main__':
    app.run(debug=True)
