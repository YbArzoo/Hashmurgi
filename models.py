from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime  # Add this import
import enum
from sqlalchemy import Enum

db = SQLAlchemy()

class PriorityLevel(enum.Enum):
    low = 'Low'
    medium = 'Medium'
    high = 'High'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin, manager, farmer, delivery_man, customer
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    blood_group = db.Column(db.String(5))
    image = db.Column(db.String(200))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    product_description = db.Column(db.String(200), nullable=True)
    image = db.Column(db.String(100), nullable=True)  # Add this line for the image
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Product {self.name}>'



class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    delivery_man_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='Pending')  # Pending, In Transit, Delivered, Cancelled
    total_amount = db.Column(db.Float)
    shipping_address = db.Column(db.Text)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    delivery_date = db.Column(db.DateTime)
    
    # Add priority field
    priority = db.Column(db.Enum(PriorityLevel), default=PriorityLevel.medium)

    # Relationships
    customer = db.relationship('User', foreign_keys=[customer_id], backref='customer_orders')
    delivery_man = db.relationship('User', foreign_keys=[delivery_man_id], backref='delivery_orders')

    @property
    def customer_name(self):
        return self.customer.name if self.customer else "Unknown Customer"
    
    @property
    def address(self):
        return self.shipping_address


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float)
    
    # Relationships
    order = db.relationship('Order', backref='items')
    product = db.relationship('Product')
    
    @property
    def subtotal(self):
        return self.quantity * self.price
class DeliveryIssue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    reported_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    issue_type = db.Column(db.String(50))  # delivery_delay, wrong_address, customer_unavailable, etc.
    description = db.Column(db.Text)
    image = db.Column(db.String(100))  # Path to uploaded image
    urgency = db.Column(db.String(20))  # low, medium, high
    status = db.Column(db.String(20), default='Pending')  # Pending, In Progress, Resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    order = db.relationship('Order', backref='issues')
    reporter = db.relationship('User', backref='reported_issues')
class DeliveryPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delivery_man_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))  # ✅ Add this line
    amount = db.Column(db.Float)
    method = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Pending')
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)

    delivery_man = db.relationship('User', backref='payments')

    
    

# class Batch(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     batch_name = db.Column(db.String(100), nullable=False)
#     bird_type = db.Column(db.String(50), nullable=False)
#     quantity = db.Column(db.Integer, nullable=False)
#     arrival_date = db.Column(db.Date, nullable=False)
#     notes = db.Column(db.Text, nullable=True)
#     added_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Optional: track admin who added it

#     def __repr__(self):
#         return f"<Batch {self.batch_name}>"
    
class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_name = db.Column(db.String(100), nullable=False)
    bird_type = db.Column(db.String(50), nullable=False)  # ✅ this must now exist
    quantity = db.Column(db.Integer, nullable=False)
    arrival_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'))
   
    
class Vaccination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    vaccine_name = db.Column(db.String(100), nullable=False)
    scheduled_date = db.Column(db.Date, nullable=False)
    dosage = db.Column(db.String(100))
    administered_by = db.Column(db.String(100))
    status = db.Column(db.String(50), default='Scheduled')  # Scheduled, Completed, Missed
    priority = db.Column(Enum(PriorityLevel), default=PriorityLevel.medium)
    notes = db.Column(db.Text)
    batch = db.relationship('Batch', backref='vaccinations')

    def __repr__(self):
        return f"<Vaccination {self.vaccine_name} for Batch {self.batch_id}>"



class Production(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    production_date = db.Column(db.Date, nullable=False)
    egg_count = db.Column(db.Integer, default=0)
    meat_weight_kg = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    priority = db.Column(Enum(PriorityLevel), default=PriorityLevel.medium)

    batch = db.relationship('Batch', backref='productions')

    def __repr__(self):
        return f"<Production Batch {self.batch_id} on {self.production_date}>"
    
    

class FeedLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    log_date = db.Column(db.Date, nullable=False)
    feed_type = db.Column(db.String(100), nullable=False)
    quantity_kg = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)
    priority = db.Column(Enum(PriorityLevel), default=PriorityLevel.medium)

    batch = db.relationship('Batch', backref='feed_logs')

    def __repr__(self):
        return f"<FeedLog {self.feed_type} for Batch {self.batch_id} on {self.log_date}>"



class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)

    customer = db.relationship('User', foreign_keys=[customer_id])
    product = db.relationship('Product')

    def __repr__(self):
        return f"<Sale {self.product.name} to {self.customer.name}>"


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    status = db.Column(db.String(20), default='Unpaid')  # Paid or Unpaid
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    payment_method = db.Column(db.String(50))
    notes = db.Column(db.Text)

    sale = db.relationship('Sale', backref='invoice')

    def __repr__(self):
        return f"<Invoice {self.id} - {self.status}>"



class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    user = db.relationship('User', backref='tasks')
    
    

class PoultryBatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String(20), nullable=False, unique=True)
    bird_type = db.Column(db.String(20), nullable=False)  # layer, broiler, chick
    breed = db.Column(db.String(50))  # ✅ NEW
    location = db.Column(db.String(100))  # ✅ NEW
    count = db.Column(db.Integer, nullable=False)
    arrival_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default='Healthy')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 
    # Relationship
    user = db.relationship('User', backref='poultry_batches')

class HealthCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String(20), nullable=False)
    check_date = db.Column(db.Date, nullable=False)
    health_status = db.Column(db.String(20), nullable=False)  # excellent, good, fair, poor, critical
    feed_consumption = db.Column(db.String(20), nullable=False)  # normal, above, below
    water_consumption = db.Column(db.String(20), nullable=False)  # normal, above, below
    mortality = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='health_checks')

class Feeding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    batch_id = db.Column(db.String(20), nullable=False)
    feed_type = db.Column(db.String(20), nullable=False)  # layer, broiler, chick, mixed
    quantity = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # completed, pending, scheduled
    notes = db.Column(db.Text, nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='feedings')