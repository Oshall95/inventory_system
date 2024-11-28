from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.models import User, Product, Category, Invoice, InvoiceItem
from app import db
from datetime import datetime
import logging
from decimal import Decimal
from flask import request
import os
import re 
from flask import send_from_directory
from werkzeug.utils import secure_filename
bp = Blueprint('routes', __name__)
UPLOAD_FOLDER = 'uploads'  # Directory to store uploaded files
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the directory exists
# Logging configuration
logging.basicConfig(level=logging.DEBUG)





@bp.route('/admin_view_documents', methods=['GET'])
def admin_view_documents():
    try:
        # Fetch all uploaded files from the uploads directory
        files = os.listdir(UPLOAD_FOLDER)
        file_urls = [url_for('routes.uploaded_file', filename=file) for file in files]
        zipped_files = zip(files, file_urls)

        # Render the new admin-specific template
        return render_template('admin_view_documents.html', zipped_files=zipped_files)
    except Exception as e:
        logging.error(f"Error viewing documents for admin: {e}")
        return jsonify({"message": "Error loading documents"}), 500



# Login and Logout
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['admin'] = username
            return redirect(url_for('routes.index'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('routes.login'))

@bp.route('/')
def index():
    if 'admin' not in session:
        return redirect(url_for('routes.login'))
    return render_template('index.html')

# API Endpoints

# Get all products
@bp.route('/api/products', methods=['GET'])
def get_products():
    if 'admin' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    products = Product.query.all()
    product_list = [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "quantity": p.quantity,
            "low_stock": p.quantity <= p.low_stock_threshold,
            "category": p.category.name if p.category else "No Category",
        }
        for p in products
    ]
    return jsonify({"products": product_list})

# Get all categories
@bp.route('/api/categories', methods=['GET'])
def get_categories():
    if 'admin' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    categories = Category.query.all()
    return jsonify([{"id": c.id, "name": c.name} for c in categories])

# Add a new category
@bp.route('/api/add_category', methods=['POST'])
def add_category():
    if 'admin' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({"message": "Category name is required"}), 400

    # Check for duplicate category
    existing_category = Category.query.filter_by(name=data['name']).first()
    if existing_category:
        logging.warning(f"Category {data['name']} already exists.")
        return jsonify({"message": "Category already exists"}), 400

    new_category = Category(name=data['name'])
    db.session.add(new_category)
    db.session.commit()
    return jsonify({"message": "Category added successfully"})

# Add a new product
@bp.route('/api/add_product', methods=['POST'])
def add_product():
    if 'admin' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json()
    if not data or not data.get('category_id'):
        return jsonify({"message": "Category ID is required"}), 400

    category = Category.query.get(data['category_id'])
    if not category:
        logging.error(f"Category ID {data['category_id']} not found.")
        return jsonify({"message": "Category not found"}), 404

    new_product = Product(
        name=data['name'],
        description=data['description'],
        price=Decimal(data['price']),
        quantity=data['quantity'],
        low_stock_threshold=data['low_stock_threshold'],
        category_id=category.id
    )
    db.session.add(new_product)
    db.session.commit()
    return jsonify({"message": "Product added successfully"})

@bp.route('/api/delete_product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    if 'admin' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    product = Product.query.get_or_404(product_id)

    # Delete all invoice items referencing this product
    InvoiceItem.query.filter_by(product_id=product_id).delete()

    # Now delete the product
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product and associated invoice items deleted successfully"})

@bp.route('/api/create_invoice', methods=['POST'])
def create_invoice():
    import traceback
    try:
        # Log the received JSON data
        data = request.get_json()
        logging.debug(f"Received data: {data}")

        if not data:
            logging.error("No data provided in the request.")
            return jsonify({"message": "No data provided"}), 400

        # Extract basic invoice data
        customer_name = data.get('customer_name')
        invoice_number = data.get('invoice_number')
        invoice_date_str = data.get('invoice_date')
        discount = float(data.get('discount', 0))  # Convert to float
        items = data.get('items', [])

        if not customer_name or not invoice_number or not invoice_date_str or not items:
            logging.error("Missing required fields in the request.")
            return jsonify({"message": "Invalid input. All fields are required."}), 400

        # Parse invoice date
        try:
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
            logging.debug(f"Parsed invoice date: {invoice_date}")
        except ValueError:
            logging.error(f"Invalid date format: {invoice_date_str}")
            return jsonify({"message": "Invalid date format. Please use YYYY-MM-DD."}), 400

        # Create the invoice object
        new_invoice = Invoice(
            customer_name=customer_name,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            discount=discount
        )
        db.session.add(new_invoice)
        logging.debug("Created a new invoice object.")

        total_amount = 0.0

        # Process each item
        for item in items:
            product_name = item.get('product_name')
            quantity = float(item.get('quantity', 0))  # Convert to float
            rate = float(item.get('rate', 0))         # Convert to float
            tax = float(item.get('tax', 0))           # Convert to float
            item_discount = float(item.get('discount', 0))  # Convert to float

            # Log the received values for debugging
            logging.debug(f"Processing item: {product_name}, Rate: {rate}, Quantity: {quantity}, Tax: {tax}, Discount: {item_discount}")

            if not product_name or quantity <= 0 or rate < 0:
                logging.error(f"Invalid item data: {item}")
                return jsonify({"message": "Invalid item data"}), 400

            # Fetch product
            product = Product.query.filter_by(name=product_name).first()
            if not product:
                logging.error(f"Product not found: {product_name}")
                return jsonify({"message": f"Product not found: {product_name}"}), 404

            # Calculate item total
            item_total = (rate * quantity) + tax - item_discount
            logging.debug(f"Calculated item total: {item_total}")
            total_amount += item_total

            if product.quantity < quantity:
                logging.error(f"Insufficient stock for product: {product_name}")
                return jsonify({"message": f"Insufficient stock for product: {product_name}"}), 400
            product.quantity -= int(quantity)

            # Add invoice item
            invoice_item = InvoiceItem(
                invoice=new_invoice,
                product=product,
                quantity=int(quantity),  # Ensure this is an integer
                rate=rate,
                tax=tax,
                amount=item_total,
                discount=item_discount
            )
            db.session.add(invoice_item)
            logging.debug(f"Processed invoice item: {item}")

        # Apply overall discount
        total_amount -= discount
        total_amount = max(total_amount, 0)
        new_invoice.total_amount = total_amount
        logging.debug(f"Final total amount for the invoice: {total_amount}")

        db.session.commit()
        logging.info(f"Invoice created successfully with ID: {new_invoice.id}")

        return jsonify({
            "message": "Invoice created successfully",
            "invoice_id": new_invoice.id,
            "redirect_url": url_for('routes.view_invoice', invoice_id=new_invoice.id)
        })

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating invoice: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({"message": "Error creating invoice", "error": str(e)}), 500

# Invoice page
@bp.route('/invoice')
def invoice_page():
    if 'admin' not in session:
        return redirect(url_for('routes.login'))
    return render_template('invoice.html')

@bp.route('/invoice/<int:invoice_id>')
def view_invoice(invoice_id):
    if 'admin' not in session:
        return redirect(url_for('routes.login'))

    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Debugging log: print each invoice item
    for item in invoice.items:
        logging.debug(f"Item ID: {item.id}, Product Name: {item.product.name}, Quantity: {item.quantity}, Rate: {item.rate}, Amount: {item.amount}")

    return render_template('invoice_template.html', invoice=invoice)

@bp.route('/invoices', methods=['GET'])
def view_invoices():
    if 'admin' not in session:
        return redirect(url_for('routes.login'))
    return render_template('all_invoices.html')

@bp.route('/api/invoices', methods=['GET'])
def get_invoices():
    if 'admin' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        # Query all invoices
        invoices = Invoice.query.all()

        # Serialize invoices into JSON
        invoice_list = [
            {
                "id": invoice.id,
                "customer_name": invoice.customer_name,
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date.strftime('%Y-%m-%d'),
                "total_amount": float(invoice.total_amount),  # Convert Decimal to float for JSON
                "discount": float(invoice.discount),  # Include the discount
                "items": [
                    {
                        "product_name": item.product.name,
                        "quantity": item.quantity,
                        "rate": float(item.rate),  # Convert Decimal to float for JSON
                        "amount": float(item.amount)  # Convert Decimal to float for JSON
                    }
                    for item in invoice.items
                ]
            }
            for invoice in invoices
        ]

        logging.debug('Invoices data: %s', invoice_list)

        return jsonify({"invoices": invoice_list})

    except Exception as e:
        logging.error('Error retrieving invoices: %s', str(e))
        return jsonify({"message": "Error retrieving invoices", "error": str(e)}), 500

@bp.route('/api/edit_product/<int:product_id>', methods=['PUT'])
def edit_product(product_id):
    try:
        # Fetch the product by ID
        product = Product.query.get(product_id)
        if not product:
            logging.error(f"Product with ID {product_id} not found.")
            return jsonify({"message": "Product not found"}), 404

        # Get the data from the request
        data = request.get_json()

        # Update product fields
        product.name = data.get('name', product.name)
        product.description = data.get('description', product.description)
        product.price = float(data.get('price', product.price))  # Convert to float for consistency
        product.quantity = int(data.get('quantity', product.quantity))  # Ensure integer
        product.low_stock_threshold = int(data.get('low_stock_threshold', product.low_stock_threshold))  # Ensure integer

        # Commit the changes
        db.session.commit()
        logging.info(f"Product with ID {product_id} updated successfully.")

        return jsonify({"message": "Product updated successfully"})

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating product: {str(e)}")
        return jsonify({"message": "Error updating product", "error": str(e)}), 500
# Route to display the upload page
@bp.route('/upload', methods=['GET'])
def upload_page():
    return render_template('upload_documents.html')


def sanitize_filename(filename):
    import unicodedata
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('utf-8')
    filename = filename.replace(" ", "_")
    return secure_filename(filename)

UPLOAD_FOLDER = '/home/kali/inventory_system/uploads'

for filename in os.listdir(UPLOAD_FOLDER):
    sanitized_filename = sanitize_filename(filename)
    if sanitized_filename != filename:
        old_path = os.path.join(UPLOAD_FOLDER, filename)
        new_path = os.path.join(UPLOAD_FOLDER, sanitized_filename)
        os.rename(old_path, new_path)
        print(f"Renamed: {filename} -> {sanitized_filename}")


@bp.route('/upload_documents', methods=['POST'])
def upload_documents():
    if 'document' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('routes.upload_page'))
    
    file = request.files['document']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('routes.upload_page'))
    
    if file:
        # Sanitize the file name
        sanitized_filename = sanitize_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, sanitized_filename)
        
        # Save the file
        file.save(file_path)
        flash(f'File {file.filename} uploaded successfully as {sanitized_filename}!', 'success')
        return redirect(url_for('routes.view_documents'))



# Serve files from the uploads directory
@bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@bp.route('/view_documents', methods=['GET'])
def view_documents():
    try:
        files = os.listdir(UPLOAD_FOLDER)
        file_urls = [url_for('routes.uploaded_file', filename=file) for file in files]
        zipped_files = zip(files, file_urls)
        return render_template('view_documents.html', zipped_files=zipped_files)
    except Exception as e:
        logging.error(f"Error loading documents: {e}")
        return jsonify({"message": "Error loading documents"}), 500




@bp.route('/delete_file/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        # Decode the filename and build the file path
        decoded_filename = filename
        file_path = os.path.join(UPLOAD_FOLDER, decoded_filename)
        
        # Check if the file exists
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"Deleted file: {decoded_filename}")
            return jsonify({"message": f"File '{decoded_filename}' deleted successfully."}), 200
        else:
            logging.error(f"File not found: {decoded_filename}")
            return jsonify({"message": f"File '{decoded_filename}' not found."}), 404
    except Exception as e:
        logging.error(f"Error deleting file: {e}")
        return jsonify({"message": "Error deleting file", "error": str(e)}), 500
    


@bp.route('/edit_file/<filename>', methods=['POST'])
def edit_file(filename):
    try:
        # Decode the filename and get the new name from the request
        decoded_filename = filename
        data = request.get_json()
        new_filename = data.get('new_filename')

        if not new_filename:
            return jsonify({"message": "New filename is required."}), 400

        old_file_path = os.path.join(UPLOAD_FOLDER, decoded_filename)
        new_file_path = os.path.join(UPLOAD_FOLDER, new_filename)

        # Check if the file exists
        if os.path.exists(old_file_path):
            os.rename(old_file_path, new_file_path)
            logging.info(f"Renamed file: {decoded_filename} to {new_filename}")
            return jsonify({"message": f"File renamed to '{new_filename}' successfully."}), 200
        else:
            logging.error(f"File not found: {decoded_filename}")
            return jsonify({"message": f"File '{decoded_filename}' not found."}), 404
    except Exception as e:
        logging.error(f"Error renaming file: {e}")
        return jsonify({"message": "Error renaming file", "error": str(e)}), 500

