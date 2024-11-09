import telebot
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.exc import NoResultFound
from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory,flash
from flask_sqlalchemy import SQLAlchemy
import psycopg2
from sqlalchemy.exc import IntegrityError
import qrcode
import os
import random
import string
import psycopg2
TOKEN = '7420485098:AAEcDlLy6JKTjL44F3Vin0fOo0HUFwMCup8'
import qrcode
import random
import string
from telebot import types
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
# app.secret_key = 'nima123'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:n1m010@localhost:5432/vimba'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)


DB_HOST = "localhost"
DB_NAME = "vimba"
DB_USER = "vimba_user"
DB_PASS = "vimba"
DB_PORT = "5432"

def create_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        return None


UPLOAD_FOLDER = '../static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


pending_referrals = {}


def update_db_schema():
    metadata = MetaData()
    metadata.reflect(bind=engine)
    product_statuses = Table('product_statuses', metadata, autoload_with=engine)

    if 'status' not in product_statuses.columns:
        try:
            with engine.connect() as conn:
                conn.execute('ALTER TABLE product_statuses ADD COLUMN status TEXT')
        except OperationalError as e:
            pass
    else:
        pass

# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     telegram_id = db.Column(db.Integer, unique=True, nullable=False)
#     phone_number = db.Column(db.String, nullable=False)
#     balance = db.Column(db.Float, default=0)
#     verify_code = db.Column(db.String)  # Assuming this is a field to store verification code
#     unique_code = db.Column(db.String(255), unique=True)
#     qr_code_path = db.Column(db.String(255))
#
#
# class Order(db.Model):
#     order_id = db.Column(db.Integer, primary_key=True)
#     telegram_id = db.Column(db.Integer, db.ForeignKey('user.telegram_id'), nullable=False)
#     url = db.Column(db.String, nullable=False)
#     size = db.Column(db.String, nullable=False)
#     color = db.Column(db.String, nullable=False)
#     status = db.Column(db.String, nullable=False)
#     price = db.Column(db.Float)
#     description = db.Column(db.String)
#
# class Charge(db.Model):
#     charge_id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     amount = db.Column(db.Float, nullable=False)
#     charge_date = db.Column(db.DateTime, default=datetime.utcnow)
#     photo_path = db.Column(db.String)
#
# class ProductStatus(db.Model):
#     status_id = db.Column(db.Integer, primary_key=True)
#     order_id = db.Column(db.Integer, db.ForeignKey('order.order_id'), nullable=False)
#     status = db.Column(db.String, nullable=False)
#     status_date = db.Column(db.DateTime, default=datetime.utcnow)

def user_exists(telegram_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE telegram_id = %s", (str(telegram_id),))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def generate_unique_code(length=10):
    """Generate a unique alphanumeric code of specified length."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def generate_qr_code(unique_code):
    """Generate a QR code for the unique code and return the path."""
    qr_code_path = f"../static/qrcodes/{unique_code}.png"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(unique_code)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    img.save(qr_code_path)
    return qr_code_path


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

@app.route('/scan/<unique_code>', methods=['GET'])
def scan_qr_code(unique_code):
    """Handle QR code scan and display user information based on unique code."""
    user_info = get_user_info(unique_code)
    if user_info:
        return jsonify(user_info)
    else:
        return jsonify({"error": "User not found"}), 404


def register_user(telegram_id, phone_number):
    """Register a new user in the database and set their balance to 0."""

    telegram_id_str = str(telegram_id)

    referrer_id = pending_referrals.get(telegram_id_str, {}).get("referrer_id")

    conn = create_connection()
    if conn is None:
        return None

    try:
        with conn.cursor() as cur:
            unique_code = generate_unique_code()
            qr_code_path = generate_qr_code(unique_code)

            cur.execute(""" 
                INSERT INTO users (telegram_id, phone_number, unique_code, qr_code_path, balance, referrer_id) 
                VALUES (%s, %s, %s, %s, %s, %s) 
                RETURNING id
            """, (telegram_id_str, phone_number, unique_code, qr_code_path, 0, referrer_id))

            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id
    except Exception as e:
        return None
    finally:
        conn.close()


import uuid

def get_referral_count(referrer_id):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = %s", (referrer_id,))
    referral_count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return referral_count


@bot.message_handler(func=lambda message: message.text == "👤 Profile")
def handle_profile(message):
    telegram_id = str(message.from_user.id)
    if not user_exists(telegram_id):
        bot.send_message(message.chat.id,
                         "You need to register first by sharing your phone number. Please use /start to register.")
        return

    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT phone_number, balance, referral_code, referrer_id FROM users WHERE telegram_id = %s", (telegram_id,))
        user_info = cursor.fetchone()

        if user_info:
            phone_number, balance, referral_code, referrer_id = user_info
            balance_message = f"${balance:.2f}" if balance is not None else "Balance not available"

            if not referral_code:
                referral_code = str(uuid.uuid4())[:8]
                cursor.execute("UPDATE users SET referral_code = %s WHERE telegram_id = %s",
                               (referral_code, telegram_id))
                conn.commit()
                bot.send_message(message.chat.id,
                                 f"A unique referral code has been generated for you: `{referral_code}`",
                                 parse_mode='Markdown')

            cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = (SELECT id FROM users WHERE telegram_id = %s)", (telegram_id,))
            number_of_referrals = cursor.fetchone()[0]

            bot.send_message(
                message.chat.id,
                f"Profile Information:\n"
                f"Phone Number: {phone_number}\n"
                f"Balance: {balance_message}\n"
                f"Referral Code: `{referral_code}`\n"  # Use Markdown formatting for the referral code
                f"Number of Users You Referred: {number_of_referrals}",
                reply_markup=create_navigation_menu(),
                parse_mode='Markdown'
            )
        else:
            bot.send_message(message.chat.id, "Unable to retrieve your profile information.")
    except Exception as e:
        bot.send_message(message.chat.id, "An error occurred while retrieving your profile.")
    finally:
        conn.close()



def save_product_status(order_id, status="pending"):
    if order_id is None:
        raise ValueError("order_id cannot be None")
    date=datetime.now()
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO product_statuses (order_id, status,status_date)
        VALUES (%s, %s,%s)
    """, (order_id, status,date))
    conn.commit()
    conn.close()

def get_user_orders(telegram_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, url, size, color, price, description 
        FROM orders 
        WHERE telegram_id = %s
    """, (str(telegram_id),))
    orders = cursor.fetchall()
    conn.close()
    return [
        (
            order[0],
            f"URL: {order[1]}, Size: {order[2]}, Color: {order[3]}, Price: {order[4]}, Description: {order[5]}"
        )
        for order in orders
    ]


def get_product_statuses(order_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, status_date FROM product_statuses WHERE order_id = %s", (order_id,))
    statuses = cursor.fetchall()
    conn.close()
    return [(status[0], status[1]) for status in statuses]



def get_user_balance(telegram_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE telegram_id = %s", (str(telegram_id),))
    row = cursor.fetchone()
    conn.close()
    if row:
        balance = row[0]
        return balance
    else:
        return None

def get_user_charges(telegram_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT amount, description FROM charges
        WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)
        ORDER BY charge_id DESC
    """, (str(telegram_id),))
    charges = cursor.fetchall()
    conn.close()
    return [(charge[0], charge[1]) for charge in charges]


def save_charge(user_id, amount, description, photo_path=None):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO charges (user_id, amount, description, photo_path) VALUES (%s, %s, %s, %s)",
                   (user_id, amount, description, photo_path))
    conn.commit()
    conn.close()


def create_navigation_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    button_order = KeyboardButton("🛒 Order")
    button_profile = KeyboardButton("👤 Profile")
    button_wallet = KeyboardButton("💰 Wallet")
    button_show_orders = KeyboardButton("📦 Show Orders")
    button_charge = KeyboardButton("💳 Charge")
    button_verify = KeyboardButton("🔐 Request Verification Code")
    markup.add(button_order, button_profile, button_wallet, button_show_orders, button_charge, button_verify)
    return markup


def process_charge_amount(message):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError("Amount must be positive.")
    except ValueError:
        bot.send_message(message.chat.id, "Invalid amount. Please enter a valid number.")
        return
    bot.send_message(message.chat.id, "Please upload a photo of the receipt or transaction.")
    bot.register_next_step_handler(message, process_charge_photo, amount)

def process_charge_photo(message, amount):
    if message.photo:
        photo = message.photo[-1].file_id
        photo_file = bot.get_file(photo)
        photo_path = os.path.join("uploads", f"{message.from_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        bot.download_file(photo_file.file_path, photo_path)
        user_id = get_user_id(message.from_user.id)
        bot.send_message(message.chat.id, f"Charge of ${amount:.2f} successfully wait foe admin accept.")
    else:
        bot.send_message(message.chat.id, "Please upload a photo.")



@bot.message_handler(func=lambda message: user_order_data.get(message.from_user.id, {}).get("step") == "price")
def handle_order_price(message):
    telegram_id = message.from_user.id
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "Invalid price. Please enter a valid number.")
        return

    user_order_data[telegram_id]["price"] = price


    balance = get_user_balance(telegram_id)
    if balance < price:
        bot.send_message(message.chat.id, f"Your balance is insufficient. You need an additional ${price - balance:.2f} to place this order.",
                         reply_markup=create_navigation_menu())
        del user_order_data[telegram_id]
        return
    save_order(telegram_id, user_order_data[telegram_id])
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM orders WHERE telegram_id=? ORDER BY id DESC LIMIT 1", (str(telegram_id),))
    order_id = cursor.fetchone()[0]
    conn.close()
    save_product_status(order_id, "Created")
    del user_order_data[telegram_id]
    bot.send_message(message.chat.id, "Your order has been placed successfully!", reply_markup=create_navigation_menu())

def create_wallet_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    button_back = KeyboardButton("🔙 Back to Menu")
    button_show_charges = KeyboardButton("💳 Show Previous Charges")
    markup.add(button_back, button_show_charges)
    return markup

user_order_data = {}
user_charge_data = {}


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    telegram_id = message.from_user.id
    phone_number = message.contact.phone_number

    if not user_exists(telegram_id):
        register_user(telegram_id, phone_number)
        markup = create_navigation_menu()
        bot.send_message(message.chat.id, "You have been registered. Please choose an option below.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "You are already registered.")



@bot.message_handler(func=lambda message: message.text == "🛒 Order")
def handle_order(message):
    telegram_id = message.from_user.id
    if not user_exists(telegram_id):
        bot.send_message(message.chat.id, "You need to register first by sharing your phone number. Please use /start to register.")
        return
    bot.send_message(message.chat.id, "Please provide the product URL:", reply_markup=ReplyKeyboardRemove())
    user_order_data[telegram_id] = {"step": "url"}



@bot.message_handler(func=lambda message: user_order_data.get(message.from_user.id, {}).get("step") == "url")
def handle_order_url(message):
    telegram_id = message.from_user.id
    user_order_data[telegram_id]["url"] = message.text
    user_order_data[telegram_id]["step"] = "size"
    bot.send_message(message.chat.id, "Please provide the size you want:", reply_markup=create_wallet_menu())



@bot.message_handler(func=lambda message: user_order_data.get(message.from_user.id, {}).get("step") == "size")
def handle_order_size(message):
    telegram_id = message.from_user.id
    if message.text == "🔙 Back to Menu":
        markup = create_navigation_menu()
        bot.send_message(message.chat.id, "Returning to main menu.", reply_markup=markup)
        del user_order_data[telegram_id]
        return

    user_order_data[telegram_id]["size"] = message.text
    user_order_data[telegram_id]["step"] = "color"
    bot.send_message(message.chat.id, "Please provide the color you want:", reply_markup=create_wallet_menu())


def save_order(telegram_id, order_details):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO orders (telegram_id, url, size, color, status, price, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            str(telegram_id),
            order_details.get('url'),
            order_details.get('size'),
            order_details.get('color'),
            order_details.get('status', 'Pending'),
            order_details.get('price', 0.0),
            order_details.get('description', '')
        ))
        conn.commit()
    except Exception as e:
        print(e)
        logger.error(f"Error saving order: {e}")
    finally:
        conn.close()



@bot.message_handler(func=lambda message: user_order_data.get(message.from_user.id, {}).get("step") == "color")
def handle_order_color(message):
    telegram_id = message.from_user.id

    if message.text == "🔙 Back to Menu":
        markup = create_navigation_menu()
        bot.send_message(message.chat.id, "Returning to main menu.", reply_markup=markup)
        del user_order_data[telegram_id]
        return

    user_order_data[telegram_id]["color"] = message.text

    order_details = {
        "url": user_order_data[telegram_id]["url"],
        "size": user_order_data[telegram_id]["size"],
        "color": user_order_data[telegram_id]["color"],
    }
    save_order(telegram_id, order_details)

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id
        FROM orders
        WHERE telegram_id=%s
        ORDER BY id DESC
        LIMIT 1
    """, (str(telegram_id),))
    result = cursor.fetchone()
    conn.close()

    if result:
        order_id = result[0]
        if order_id is not None:
            save_product_status(order_id, "Created")
            bot.send_message(message.chat.id, "Your order has been saved successfully!",
                             reply_markup=create_navigation_menu())
        else:
            bot.send_message(message.chat.id, "There was an error saving your order. Please try again.")
    else:
        bot.send_message(message.chat.id, "No orders found. Please try again.")

    del user_order_data[telegram_id]

from datetime import datetime


def save_charge(user_id, amount, photo_path, description=None):
    charge_date = datetime.now()

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO charges (user_id, amount, charge_date, photo_path, description)
        VALUES (%s, %s, %s, %s, %s,%s)
    """, (user_id, amount, datetime.now(), photo_path, description))
    conn.commit()
    conn.close()


user_charge_data = {}


def handle_charge_photo(photo_id, chat_id, from_user_id):
    if from_user_id not in user_charge_data or user_charge_data[from_user_id].get("step") != "photo":
        return
    try:
        file_info = bot.get_file(photo_id)
        file_path = file_info.file_path
        downloaded_file = bot.download_file(file_path)
        local_filename = os.path.join(UPLOAD_FOLDER, f"{photo_id}.jpg")
        with open(local_filename, 'wb') as new_file:
            new_file.write(downloaded_file)
        amount = user_charge_data[from_user_id]["amount"]
        user_id = get_user_id(from_user_id)
        save_charge(user_id, amount, "Photo charge", local_filename)

        del user_charge_data[from_user_id]

        bot.send_message(
            chat_id=chat_id,
            text="Charge successful! Your balance has been updated.",
            reply_markup=create_navigation_menu()
        )
    except Exception as e:
        bot.send_message(
            chat_id=chat_id,
            text=f"An error occurred while processing your photo: {str(e)}"
        )
@bot.message_handler(content_types=['photo'])
def handle_photo_message(message):
    photo_id = message.photo[-1].file_id
    chat_id = message.chat.id
    from_user_id = message.from_user.id
    handle_charge_photo(photo_id, chat_id, from_user_id)

@bot.message_handler(func=lambda message: message.text == "📦 Show Orders")
def handle_show_orders(message):
    telegram_id = message.from_user.id

    if not user_exists(telegram_id):
        bot.send_message(message.chat.id, "You need to register first by sharing your phone number. Please use /start to register.")
        return

    orders = get_user_orders(telegram_id)

    if not orders:
        bot.send_message(message.chat.id, "You have no orders yet.", reply_markup=create_navigation_menu())
    else:
        order_texts = []
        for order in orders:
            order_id, order_details = order
            statuses = get_product_statuses(order_id)
            status_texts = [f"Status: {status[0]} on {status[1].strftime('%Y-%m-%d')}" for status in statuses]
            statuses_message = "\n".join(status_texts) if statuses else "No statuses yet"
            order_texts.append(f"Order ID {order_id}: {order_details}\nStatuses:\n{statuses_message}")
        orders_message = "\n\n".join(order_texts)
        bot.send_message(message.chat.id, f"Your orders:\n\n{orders_message}", reply_markup=create_navigation_menu())



@bot.message_handler(func=lambda message: message.text == "💰 Wallet")
def handle_wallet(message):
    telegram_id = message.from_user.id
    if not user_exists(telegram_id):
        bot.send_message(message.chat.id, "You need to register first by sharing your phone number. Please use /start to register.")
        return
    balance = get_user_balance(telegram_id)
    if balance is None:
        bot.send_message(message.chat.id, "Unable to retrieve your balance. Please try again later.")
        return
    markup = create_wallet_menu()
    bot.send_message(message.chat.id, f"Your current balance is: ${balance:.2f}", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "💳 Show Previous Charges")
def handle_show_charges(message):
    telegram_id = message.from_user.id
    if not user_exists(telegram_id):
        bot.send_message(message.chat.id, "You need to register first by sharing your phone number. Please use /start to register.")
        return
    charges = get_user_charges(telegram_id)
    if not charges:
        bot.send_message(message.chat.id, "You have no previous charges.", reply_markup=create_wallet_menu())
    else:
        charge_texts = [f"Charge {i + 1}: ${charge[0]:.2f} - {charge[1]}" for i, charge in enumerate(charges)]
        charges_message = "\n\n".join(charge_texts)
        bot.send_message(message.chat.id, f"Your previous charges:\n\n{charges_message}", reply_markup=create_wallet_menu())


@bot.message_handler(func=lambda message: message.text == "💳 Charge")
def handle_charge(message):
    telegram_id = message.from_user.id
    if not user_exists(telegram_id):
        bot.send_message(message.chat.id, "You need to register first by sharing your phone number. Please use /start to register.")
        return
    bot.send_message(message.chat.id, "Please enter the amount to charge:", reply_markup=ReplyKeyboardRemove())
    user_charge_data[telegram_id] = {"step": "amount"}


@bot.message_handler(func=lambda message: user_charge_data.get(message.from_user.id, {}).get("step") == "amount")
def handle_charge_amount(message):
    telegram_id = message.from_user.id
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "Invalid amount. Please enter a valid number.")
        return
    user_charge_data[telegram_id] = {"amount": amount, "step": "photo"}
    bot.send_message(message.chat.id, "Please send a photo related to this charge:", reply_markup=ReplyKeyboardRemove())


@bot.message_handler(func=lambda message: message.text == "🔙 Back to Menu")
def handle_back_to_menu(message):
    markup = create_navigation_menu()
    bot.send_message(message.chat.id, "Returning to main menu.", reply_markup=markup)


def get_user_id(telegram_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (str(telegram_id),))
    user_id = cursor.fetchone()[0]
    conn.close()
    return user_id


def save_charge(user_id, amount, description, photo_path=None):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO charges (user_id, amount, description, photo_path) VALUES (%s, %s, %s, %s)",
        (user_id, amount, description, photo_path)
    )
    conn.commit()
    conn.close()


def update_db_schema():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'verify_code'
    """)
    column_exists = cursor.fetchone() is not None
    if not column_exists:
        cursor.execute("ALTER TABLE users ADD COLUMN verify_code TEXT")

    conn.commit()


def generate_verification_code(length=6):
    """Generate a random verification code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def set_verification_code(telegram_id, code):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET verify_code = %s WHERE telegram_id = %s", (code, str(telegram_id)))
    conn.commit()
    conn.close()


@bot.message_handler(func=lambda message: message.text == "🔐 Request Verification Code")
def handle_request_verification_code(message):
    telegram_id = message.from_user.id
    if not user_exists(telegram_id):
        bot.send_message(message.chat.id,
                         "You need to register first by sharing your phone number. Please use /start to register.")
        return
    verification_code = generate_verification_code()
    set_verification_code(telegram_id, verification_code)
    bot.send_message(
        message.chat.id,
        f"🔐 Your verification code is:\n\n`{verification_code}`\n\n(copy the code above)",
        parse_mode="Markdown"
    )


def check_balance_and_orders(telegram_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE telegram_id = %s", (str(telegram_id),))
    balance = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(price) FROM orders WHERE telegram_id = %s", (str(telegram_id),))
    total_order_price = cursor.fetchone()[0] or 0  # Default to 0 if no orders
    conn.close()
    return balance, total_order_price


from telebot import types
import logging

# A dictionary to temporarily store user data, like referral codes
user_data = {}

# Initialize a temporary dictionary to store pending referral information by phone number




@bot.message_handler(commands=['start'])
def handle_start(message):
    telegram_id = message.from_user.id
    try:
        if not user_exists(telegram_id):
            # Ask for referral code first
            bot.send_message(message.chat.id,
                             "Welcome! If you have a referral code, please enter it. If not, type 'No'.")

            # Save user id temporarily for referral handling
            user_data[telegram_id] = {"stage": "awaiting_referral"}
        else:
            balance, total_order_price = check_balance_and_orders(telegram_id)

            if balance >= total_order_price:
                bot.send_message(message.chat.id,
                                 f"Your balance is sufficient: ${balance:.2f}. Total order cost: ${total_order_price:.2f}.")
            else:
                bot.send_message(message.chat.id,
                                 f"Your balance (${balance:.2f}) is insufficient to cover your total order cost of ${total_order_price:.2f}. Please add funds.")

            markup = create_navigation_menu()
            bot.send_message(message.chat.id, "Welcome back! Please choose an option below.", reply_markup=markup)

    except Exception as e:
        logging.error(f"Error in handle_start: {e}")
        bot.send_message(message.chat.id, "An error occurred. Please try again later.")




@bot.message_handler(func=lambda message: True)
def handle_referral_code(message):
    telegram_id = str(message.from_user.id)
    referral_code = message.text.strip().lower()

    if referral_code == "no":
        referral_code = None
        bot.send_message(message.chat.id, "No problem! Let's proceed with your registration.")
        request_phone_number(message.chat.id)
        return

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE referral_code = %s LIMIT 1", (referral_code,))
    referrer = cursor.fetchone()

    if referrer:
        referrer_db_id = referrer[0]
        bot.send_message(message.chat.id, "Referral code accepted! You will be linked to your referrer upon registration.")

        # Store the pending referral by Telegram ID
        pending_referrals[telegram_id] = {"referrer_id": referrer_db_id}  # Save the referrer ID here

        # Ask for the phone number to complete the registration
        request_phone_number(message.chat.id)

        # Optional: You might want to confirm that the referrer ID is saved correctly

    else:
        bot.send_message(message.chat.id, "Invalid referral code. Please try again or type 'No'.")
    conn.close()  # Ensure connection is closed


@bot.message_handler(content_types=['contact'])
def handle_phone_number(message):
    telegram_id = str(message.from_user.id)

    if message.contact:
        phone_number = message.contact.phone_number  # Get the phone number from contact

        conn = create_connection()

        try:
            # Register the user without passing referrer_id, it will be fetched inside the function
            user_id = register_user(telegram_id, phone_number)  # No referrer_id passed now

            if user_id:

                # Clean up the pending referrals after registration
                if telegram_id in pending_referrals:
                    del pending_referrals[telegram_id]  # Clean up the pending referrals

                bot.send_message(message.chat.id, "Registration complete! Welcome to the service.")
            else:
                pass
        except Exception as e:
            logging.error(f"Error saving phone number: {e}")
            bot.send_message(message.chat.id, "An error occurred while saving your information. Please try again.")
        finally:
            conn.close()  # Ensure connection is closed after operation

    else:
        bot.send_message(message.chat.id, "Please share your phone number to continue.")




@bot.message_handler(content_types=['text'])
def handle_text_message(message):
    bot.send_message(message.chat.id, "Please use the button to share your phone number.")


def request_phone_number(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("Share phone number", request_contact=True)
    markup.add(button)

    bot.send_message(chat_id, "Please share your phone number to complete your registration.", reply_markup=markup)



def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_unique_referral_code():
    import uuid
    return str(uuid.uuid4())[:8]

bot.polling()


