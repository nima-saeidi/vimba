from flask import Flask,jsonify, request, render_template, redirect, url_for, session, send_from_directory,flash
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2
from flask_sqlalchemy import SQLAlchemy
import json
from werkzeug.security import generate_password_hash
from datetime import datetime
from flask import session, redirect, url_for, request
from model import Admin
from flask import request, redirect, url_for, session
from datetime import datetime
from model import db,Admin,Charge,Product,Comment,ProductStatus,User,Order
from model import Admin
from sqlalchemy.types import JSON
from decimal import Decimal
from flask import request, render_template, redirect, url_for, session
from sqlalchemy import or_, and_, text
from werkzeug.utils import secure_filename
import  os
from flask_cors import CORS


app = Flask(__name__)
app.secret_key = 'nima123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://vimba_user:vimba@localhost:5432/vimbauser'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

CORS(app)
CORS(app, methods=["GET", "POST"])
CORS(app, allow_headers=["Content-Type", "Authorization"])


class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(255), unique=True, nullable=False)
    phone_number = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Numeric, default=0)
    orders = db.relationship('Order', backref='user', lazy=True)
    unique_code = db.Column(db.String(255), unique=True)
    qr_code_path = db.Column(db.String(255))
    verify_code = db.Column(db.String)
    referral_code = db.Column(db.String(255), unique=True, nullable=True)
    referrer_id = db.Column(db.Integer, nullable=True)  # New field for referrer


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(255), db.ForeignKey('users.telegram_id'), nullable=False)
    price = db.Column(db.Numeric, nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.Text)
    size = db.Column(db.Text)
    url = db.Column(db.Text)
    user_id = db.Column(db.Integer)
    status = db.Column(db.String(50))
    statuses = db.relationship('ProductStatus', backref='order', lazy=True)

class ProductStatus(db.Model):
    __tablename__ = 'product_statuses'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    status_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Charge(db.Model):
    __tablename__ = 'charges'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric, nullable=False)
    photo_path = db.Column(db.Text)
    description = db.Column(db.String, nullable=True)
    charge_id = db.Column(db.Integer)
    charge_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric, nullable=False)
    photo_path = db.Column(db.String(255), nullable=False)
    options = db.Column(JSON)

class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_name = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    rating = db.Column(db.Integer, nullable=True)




@app.route('/admin/product_statuses', methods=['GET'])
def view_product_statuses():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    statuses = ProductStatus.query.all()

    return render_template('product_statuses.html', statuses=statuses)


@app.route('/admin/update_status', methods=['POST'])
def update_status():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    order_id = request.form.get('order_id')
    new_status = request.form.get('new_status')
    user_id = request.form.get('user_id')

    if order_id and new_status and user_id:
        conn = create_connection()
        cursor = conn.cursor()

        # Use the current datetime as status_date
        status_date = datetime.now()

        cursor.execute(
            'INSERT INTO product_statuses (order_id, status, status_date) VALUES (%s, %s, %s)',
            (order_id, new_status, status_date)
        )

        cursor.execute('''
            UPDATE orders
            SET status = (
                SELECT status
                FROM product_statuses
                WHERE order_id = %s
                ORDER BY status_date DESC
                LIMIT 1
            )
            WHERE id = %s
        ''', (order_id, order_id))

        conn.commit()
        cursor.close()  # Close the cursor explicitly
        conn.close()

    return redirect(url_for('view_user', user_id=user_id))

def add_status_column():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        ALTER TABLE orders ADD COLUMN status TEXT
    ''')
    conn.commit()
    conn.close()

@app.route('/admin/delete_status/<int:status_id>', methods=['POST'])
def delete_status(status_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    status_to_delete = ProductStatus.query.get(status_id)
    if status_to_delete:
        db.session.delete(status_to_delete)
        db.session.commit()
    return redirect(url_for('view_product_statuses'))


@app.route('/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/admin/manage_orders')
def manage_orders():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    orders = db.session.query(Order, User).join(User).all()
    orders_data = [
        {
            'order_id': order.id,
            'url': order.url,
            'size': order.size,
            'color': order.color,
            'order_status': order.status,
            'price': order.price,
            'description': order.description,
            'telegram_id': user.telegram_id
        }
        for order, user in orders
    ]

    return render_template('manage_orders.html', orders=orders_data)

@app.route('/admin/update_order/<int:order_id>', methods=['POST'])
def update_order(order_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    new_price = request.form.get('new_price')
    new_description = request.form.get('new_description')
    new_status = request.form.get('status')
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM orders WHERE id = %s", (order_id,))
    result = cursor.fetchone()
    if result is None:
        return 'Order not found'
    telegram_id = result[0]
    cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
    user_result = cursor.fetchone()
    if user_result is None:
        return 'User not found'
    user_id = user_result[0]
    if new_price:
        try:
            new_price = float(new_price)
            cursor.execute('UPDATE orders SET price = %s WHERE id = %s', (new_price, order_id))
        except ValueError:
            return 'Invalid price format'
    if new_description:
        cursor.execute('UPDATE orders SET description = %s WHERE id = %s', (new_description, order_id))
    if new_status:
        cursor.execute('UPDATE orders SET status = %s WHERE id = %s', (new_status, order_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('user_details', user_id=user_id))


@app.route('/admin/change_order_status/<int:order_id>', methods=['POST'])
def change_order_status(order_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    new_status = request.form['status']
    order = Order.query.get(id)
    if not order:
        return 'Order not found'
    new_product_status = ProductStatus(
        order_id=order_id,
        status=new_status,
        status_date=datetime.now()
    )
    db.session.add(new_product_status)
    order.status = new_status
    db.session.commit()

    return redirect(url_for('user_orders', user_id=order.user_id))
def create_connection():
    """Create and return a connection to the PostgreSQL database."""
    try:
        connection = psycopg2.connect(
            dbname='vimba',
            user='vimba',
            password='password',
            host='localhost',
            port='5432'
        )
        return connection
    except psycopg2.OperationalError as e:
        return None

def initialize_db():
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='nima').first():
            admin = Admin(username='nima', password="123")
            db.session.add(admin)
            db.session.commit()
        else:
            pass

@app.route('/')
def index():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.password:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('index'))
        else:
            return 'Invalid username or password'

    return render_template('login.html')

@app.route('/admin/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('login'))


from flask import request


@app.route('/admin/users')
def view_users():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)

    per_page = 10

    users_pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('users.html', users=users_pagination.items, pagination=users_pagination)


@app.route('/admin/user/<int:user_id>', methods=['GET'])
def view_user(user_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        return 'User not found', 404

    # Count how many users this user has referred
    referral_count = User.query.filter_by(referrer_id=user_id).count()

    # Get the current page numbers for orders, charges, and manage orders
    page_orders = request.args.get('page_orders', 1, type=int)
    page_charges = request.args.get('page_charges', 1, type=int)
    page_manage_orders = request.args.get('page_manage_orders', 1, type=int)

    # Define how many orders/charges/manage orders to show per page
    orders_per_page = 5
    charges_per_page = 5
    manage_orders_per_page = 5

    # Paginate orders for the user
    paginated_orders = Order.query.filter_by(telegram_id=user.telegram_id).paginate(
        page=page_orders, per_page=orders_per_page, error_out=False
    )

    paginated_charges = Charge.query.filter_by(user_id=user_id).paginate(
        page=page_charges, per_page=charges_per_page, error_out=False
    )

    # Paginate manage orders for the user
    paginated_manage_orders = Order.query.filter_by(user_id=user_id).paginate(
        page=page_manage_orders, per_page=manage_orders_per_page, error_out=False
    )

    # Pass variables to the template
    return render_template(
        'user_detail.html',
        user=user,
        orders=paginated_orders.items,  # List of user orders for the current page
        charges=paginated_charges.items,  # List of charges for the current page
        total_pages_orders=paginated_orders.pages,  # Total number of order pages
        total_pages_charges=paginated_charges.pages,  # Total number of charge pages
        current_page_orders=paginated_orders.page,  # Current order page
        current_page_charges=paginated_charges.page,  # Current charge page
        paginated_manage_orders=paginated_manage_orders.items,  # List of manage orders for the current page
        current_page_manage_orders=paginated_manage_orders.page,  # Current manage orders page
        total_pages_manage_orders=paginated_manage_orders.pages,  # Total pages for manage orders
        referral_count=referral_count  # Number of users referred by this user
    )



from sqlalchemy import func
@app.route('/admin/user/<int:user_id>')
def user_details(user_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        return 'User not found', 404

    # Fetch the user's orders
    orders = (
        db.session.query(Order, func.max(ProductStatus.status_date).label('latest_status_date'))
        .outerjoin(ProductStatus, ProductStatus.order_id == Order.id)
        .filter(Order.telegram_id == user.telegram_id)
        .group_by(Order.id)
        .all()
    )

    # Fetch the user's charges
    charges = Charge.query.filter_by(user_id=user_id).order_by(Charge.charge_date.desc()).all()

    # Fetch the number of referrals
    referral_count = db.session.query(func.count(Referral.id)).filter(Referral.referrer_id == user.id).scalar()

    is_admin_update = session.pop('is_admin_update', False)

    return render_template('user_detail.html', user=user, orders=orders, charges=charges, referral_count=referral_count)


from flask import session


@app.route('/admin/update_balance/<int:user_id>', methods=['POST'])
def update_balance(user_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    charge_amount = request.form.get('charge_amount')

    if charge_amount is not None:
        try:
            charge_amount = Decimal(charge_amount)
        except ValueError:
            flash('Invalid charge amount', 'error')
            return redirect(url_for('user_details', user_id=user_id))

        user = User.query.get(user_id)
        if user is None:
            flash('User not found', 'error')
            return redirect(url_for('user_details', user_id=user_id))

        user.balance += charge_amount
        db.session.commit()

        # Set session variable to indicate an admin update
        session['is_admin_update'] = True

        # Flash a success message
        flash('Balance updated successfully!', 'success')

    return redirect(url_for('user_details', user_id=user_id))


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    user = User.query.get(user_id)
    if user:
        orders = Order.query.filter_by(telegram_id=user.telegram_id).all()
        for order in orders:
            ProductStatus.query.filter_by(order_id=order.order_id).delete()
            db.session.delete(order)
        Charge.query.filter_by(user_id=user_id).delete()
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('view_users'))


@app.route('/admin/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    order = Order.query.get(id)
    if order:
        ProductStatus.query.filter_by(order_id=order_id).delete()
        db.session.delete(order)
        db.session.commit()
    return redirect(url_for('view_orders'))



@app.route('/admin/delete_charge/<int:charge_id>', methods=['POST'])
def delete_charge(charge_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    charge = Charge.query.get(charge_id)
    if charge:
        db.session.delete(charge)
        db.session.commit()
    return redirect(url_for('view_charges'))

@app.route('/admin/orders', methods=['GET'])
def view_orders():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    sort_by = request.args.get('sort_by', 'order_id')
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    valid_sort_columns = ['order_id', 'status', 'price']
    sort_by = sort_by if sort_by in valid_sort_columns else 'order_id'
    query = db.session.query(Order)
    if search_query:
        search_query = f"%{search_query}%"
        query = query.filter(
            or_(
                Order.telegram_id.ilike(search_query),
                Order.description.ilike(search_query)
            )
        )

    if status_filter:
        query = query.filter(Order.status == status_filter)
    query = query.order_by(text(sort_by))
    orders = query.all()
    return render_template('orders.html', orders=orders)


@app.route('/admin/charges', methods=['GET'])
def view_charges():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    charges = db.session.query(Charge).all()
    return render_template('charges.html', charges=charges)


@app.route('/admin/user_orders/<int:user_id>')
def user_orders(user_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    orders = (
        db.session.query(Order.id, Order.order_date, Order.status, Product.product_name)
        .join(OrderItem, Order.id == OrderItem.id)
        .join(Product, OrderItem.product_id == Product.product_id)
        .filter(Order.user_id == user_id)
        .all()
    )
    return render_template('user_orders.html', orders=orders)


@app.route('/admin/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)




UPLOAD_FOLDER = '/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        photo = request.files['photo']

        options = []
        option_names = request.form.getlist('options[]')
        option_values = request.form.getlist('values[]')


        for name, value in zip(option_names, option_values):
            if name and value:
                options.append({'name': name, 'value': value})

        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_path = os.path.join("static", filename)
            photo.save(photo_path)

            new_product = Product(
                name=name,
                description=description,
                price=price,
                photo_path=filename,
                options=options
            )
            db.session.add(new_product)
            db.session.commit()

            return redirect(url_for('view_product', product_id=new_product.id))

    return render_template('add_product.html')
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/scan/<unique_code>', methods=['GET'])
def scan_qr_code(unique_code):
    """Handle QR code scan and display user information based on unique code."""
    user_info = get_user_info(unique_code)
    if user_info:
        return jsonify(user_info)
    else:
        return jsonify({"error": "User not found"}), 404
def get_user_info(unique_code):
    """Retrieve user information based on the unique code."""
    conn = create_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT telegram_id, phone_number, balance, qr_code_path
                FROM users
                WHERE unique_code = %s
            """, (unique_code,))
            user = cur.fetchone()
            if user:
                return {
                    "telegram_id": user[0],
                    "phone_number": user[1],
                    "balance": user[2],
                    "qr_code_path": user[3]
                }
            else:
                return None
    except Exception as e:
        return None
    finally:
        conn.close()

@app.route('/admin/product/<int:product_id>')
def view_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return 'Product not found', 404
    options = product.options
    return render_template('product_detail.html', product=product, options=options)



@app.route('/admin/product/<int:product_id>')
def product_detail(product_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    product = Product.query.get(product_id)
    if not product:
        return 'Product not found', 404
    options = json.loads(product.options)  # Assuming options are stored as JSON

    return render_template('product_detail.html', product=product, options=options)
@app.route('/admin/products', methods=['GET'])
def view_products():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    products = Product.query.all()

    return render_template('products.html', products=products)


@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = request.form['price']

        # Update options
        options = []
        option_names = request.form.getlist('options[]')
        option_values = request.form.getlist('values[]')

        for name, value in zip(option_names, option_values):
            if name and value:
                options.append({'name': name, 'value': value})

        product.options = options

        # Handle photo update if a new one is provided
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(photo_path)
                product.photo_path = filename

        db.session.commit()
        return redirect(url_for('view_product', product_id=product.id))

    return render_template('edit_product.html', product=product)


@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    product = Product.query.get_or_404(product_id)

    # Delete the product from the database
    db.session.delete(product)
    db.session.commit()

    return redirect(url_for('view_products'))


#-------------------------------------------------------------------------------------

from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta


app.config['JWT_SECRET_KEY'] = 'kjsdfisfnkskfnskdfk'  # Replace with your actual JWT secret key

jwt = JWTManager(app)

@app.route('/user/login', methods=['POST'])
def userlogin():
    data = request.get_json()
    phone_number = data.get('phone_number')
    verify_code = data.get('verify_code')

    if not phone_number or not verify_code:
        return jsonify({'message': 'Phone number and verification code are required'}), 400

    user = User.query.filter_by(phone_number=phone_number, verify_code=verify_code).first()
    if user:
        access_token = create_access_token(identity=user.id, expires_delta=timedelta(hours=1))
        return jsonify({
            'token': str(access_token),
            'id': user.id,
            'phone_number': user.phone_number,
            'balance': user.balance,
            'telegram_id': user.telegram_id
        }), 200
    else:
        return jsonify({'message': 'Invalid phone number or verification code'}), 401

@app.route('/user/user_info/<int:user_id>', methods=['GET'])
@jwt_required()
def user_info(user_id):
    user = User.query.get(user_id)

    if user:
        user_info = {
            'id': user.id,
            'telegram_id': user.telegram_id,
            'phone_number': user.phone_number,
            'balance': user.balance
        }
        return jsonify(user_info), 200
    else:
        return jsonify({'message': 'User not found'}), 404

@app.route('/user/orders/<int:telegram_id>', methods=['GET'])
@jwt_required()
def orders(telegram_id):
    orders = Order.query.filter_by(telegram_id=str(telegram_id)).all()
    orders_list = [{
        'order_id': order.id,
        'url': order.url,
        'size': order.size,
        'color': order.color
    } for order in orders]
    return jsonify(orders_list), 200

@app.route('/user/charges/<int:user_id>', methods=['GET'])
@jwt_required()
def charges(user_id):
    charges = Charge.query.filter_by(user_id=user_id).all()
    charges_list = [{
        'id': charge.id,
        'description': charge.description,
        'date': charge.charge_date,
        'amount': charge.amount
    } for charge in charges]
    return jsonify(charges_list), 200

@app.route('/user/product_statuses/<int:order_id>', methods=['GET'])
@jwt_required()
def product_statuses(order_id):
    statuses = ProductStatus.query.filter_by(order_id=order_id).all()
    statuses_list = [{
        'id': status.id,
        'order_id': status.order_id,
        'status_date': status.status_date,
        'status': status.status
    } for status in statuses]
    return jsonify(statuses_list), 200

# Public route to fetch available products
@app.route('/user/products', methods=['GET'])
def api_products():
    products = Product.query.all()
    product_list = [{
        "id":product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'photo_path': product.photo_path,
        'options': product.options
    } for product in products]
    return jsonify(product_list), 200


@app.route('/products/<int:product_id>/comments', methods=['GET', 'POST'])
def handle_comments(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        data = request.get_json()
        user_name = data.get('user_name')
        content = data.get('content')

        if not user_name or not content:
            return jsonify({"error": "User name and content are required"}), 400

        new_comment = Comment(
            product_id=product.id,
            user_name=user_name,
            content=content
        )

        db.session.add(new_comment)
        db.session.commit()

        return jsonify({"message": "Comment added successfully"}), 201

    elif request.method == 'GET':
        comments = Comment.query.filter_by(product_id=product.id).all()

        comments_list = [
            {
                "id": comment.id,
                "user_name": comment.user_name,
                "content": comment.content,
                "rating": comment.rating,  # Include the rating field
                "created_at": comment.created_at  # Assuming you have a timestamp field
            }
            for comment in comments
        ]

        return jsonify(comments_list), 200






@app.route('/comments/<int:comment_id>/rate', methods=['PUT'])
def rate_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    data = request.get_json()
    rating = data.get('rating')

    if rating is None or not (1 <= rating <= 5):
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400
    comment.rating = rating
    db.session.commit()
    return jsonify({"message": "Rating added/updated successfully"}), 200


@app.route('/admin/comments')
def admin_comments():
    comments = Comment.query.all()

    comments_with_products = []
    for comment in comments:
        product = Product.query.get(comment.product_id)  # Adjust this according to your model
        comments_with_products.append({
            'comment': comment,
            'product': product
        })

    return render_template('admin_comments.html', comments_with_products=comments_with_products)

@app.route('/admin/comments/<int:comment_id>/rate', methods=['POST'])
def update_comment_rating(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    rating = request.form.get('rating')

    if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
        return "Invalid rating. It must be between 1 and 5.", 400

    comment.rating = int(rating)
    db.session.commit()

    return redirect('/admin/comments')


if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0",port="5005")
