from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Numeric

# User Model
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Category Model
class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    products = db.relationship('Product', backref='category', lazy=True)

# Product Model
class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500))
    price = db.Column(Numeric(10, 2), nullable=False)  # Supports up to 2 decimal places
    quantity = db.Column(db.Integer, nullable=False)
    low_stock_threshold = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

# Invoice Model
class Invoice(db.Model):
    __tablename__ = 'invoices'  # Consistent naming for table
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(255), nullable=False)
    invoice_number = db.Column(db.String(100), unique=True, nullable=False)
    invoice_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(Numeric(10, 2), nullable=False, default=0)
    discount = db.Column(Numeric(10, 2), nullable=True, default=0)  # Field for discounts
    items = db.relationship('InvoiceItem', back_populates='invoice', cascade="all, delete-orphan")  # Correct relationship

# InvoiceItem Model
class InvoiceItem(db.Model):
    __tablename__ = 'invoice_item'
    __table_args__ = (
        db.UniqueConstraint('invoice_id', 'product_id', name='unique_invoice_product'),  # Prevent duplicate rows
    )

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Numeric(10, 2), nullable=False)  # Supports up to 2 decimal places
    tax = db.Column(db.Numeric(10, 2), default=0, nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # NEW: Discount per item (if needed)
    discount = db.Column(db.Numeric(10, 2), nullable=True, default=0)  # This can be per item

    # Relationships
    invoice = db.relationship('Invoice', back_populates='items')  # Link to Invoice
    product = db.relationship('Product', backref='invoice_items', lazy=True)  # Link to Product

    # Method to calculate final amount considering discount
    def calculate_amount(self):
        discount_amount = (self.discount / 100) * self.amount if self.discount else 0
        self.amount = round(self.quantity * self.rate + self.tax - discount_amount, 2)
