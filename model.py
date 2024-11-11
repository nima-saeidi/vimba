from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship




db = SQLAlchemy()


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
    referred_users = db.relationship('User', backref='referrer', remote_side=[id])

    def generate_default_referral_code(self):
        return str(uuid.uuid4())[:8]  # Generates a short unique code


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
    charge_date = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)



class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric, nullable=False)
    photo_path = db.Column(db.String(255), nullable=False)
    options = db.Column(JSON)
    rate = db.Column(db.Integer, nullable=True)
    comments = relationship('Comment', backref='product', lazy=True)


class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_name = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    rating = db.Column(db.Integer, nullable=True)
