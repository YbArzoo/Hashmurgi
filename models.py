from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime  # Add this import
db = SQLAlchemy()

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
    category = db.Column(db.String(50))
    quantity = db.Column(db.Integer)
    unit_price = db.Column(db.Float)
    product_description = db.Column(db.Text)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'))
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    delivery_man_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='Pending')  # Pending, In Transit, Delivered, Cancelled
    total_amount = db.Column(db.Float)
    shipping_address = db.Column(db.Text)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    delivery_date = db.Column(db.DateTime)
    
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
    amount = db.Column(db.Float)
    method = db.Column(db.String(50))  # Bank Transfer, Mobile Banking, Cash, etc.
    status = db.Column(db.String(20), default='Pending')  # Pending, Completed
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    delivery_man = db.relationship('User', backref='payments')