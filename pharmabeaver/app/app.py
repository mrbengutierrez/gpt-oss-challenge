import os
import re
from datetime import timedelta, datetime

from flask import Flask, render_template_string, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
    UserMixin,
)
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash
from jinja2 import DictLoader  # for in-memory templates

# --- App Setup ---
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pharmabeaver.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=7)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
csrf = CSRFProtect(app)

# --- Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, pw: str):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw: str) -> bool:
        return check_password_hash(self.password_hash, pw)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    price_cents = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.Text, nullable=False, default="")
    image_url = db.Column(db.String(400), nullable=False, default="")
    prescription_required = db.Column(db.Boolean, nullable=False, default=False)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    user = db.relationship("User", backref="cart_items")
    product = db.relationship("Product")


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    user = db.relationship("User", backref="orders")

    def total_cents(self) -> int:
        return sum(oi.price_cents_snapshot * oi.quantity for oi in self.items)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_cents_snapshot = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", backref="items")
    product = db.relationship("Product")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Forms ---
class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class AddToCartForm(FlaskForm):
    quantity = IntegerField("Qty", default=1, validators=[DataRequired(), NumberRange(min=1, max=99)])


class ClearCartForm(FlaskForm):
    pass


class CheckoutForm(FlaskForm):
    pass


# --- Templates (inline for speed) ---
BASE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>PharmaBeaver</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; }
    header { display:flex; gap:1rem; align-items:center; margin-bottom: 1rem; }
    nav a { margin-right: 0.75rem; text-decoration:none; color:#0366d6; }
    .card { border:1px solid #e5e7eb; border-radius:12px; padding:1rem; margin:.75rem 0; }
    .row { display:flex; justify-content:space-between; align-items:center; gap:1rem; }
    input[type=number] { width:5rem; }
    button { cursor:pointer; }
    .flash { padding:.5rem .75rem; background:#f0fdf4; border:1px solid #86efac; color:#065f46; border-radius:8px; margin-bottom: .75rem; }
    .chip { margin-left:.5rem; padding:.1rem .35rem; border-radius:6px; background:#fee2e2; border:1px solid #fecaca; color:#991b1b; font-size:.8rem; }
  </style>
</head>
<body>
  <header>
    <h1 style="margin:0;">🦫 PharmaBeaver</h1>
    <nav>
      <a href="{{ url_for('index') }}">Home</a>
      <a href="{{ url_for('products') }}">Products</a>
      {% if current_user.is_authenticated %}
        <a href="{{ url_for('cart') }}">My Cart</a>
        <a href="{{ url_for('orders') }}">Orders</a>
        <a href="{{ url_for('logout') }}">Logout ({{ current_user.username }})</a>
      {% else %}
        <a href="{{ url_for('register') }}">Register</a>
        <a href="{{ url_for('login') }}">Login</a>
      {% endif %}
    </nav>
  </header>
  {% with msgs = get_flashed_messages() %}
    {% if msgs %}
      {% for m in msgs %}<div class="flash">{{ m }}</div>{% endfor %}
    {% endif %}
  {% endwith %}
  {% block content %}{% endblock %}
</body>
</html>
"""

INDEX_TPL = """
{% extends 'base.html' %}
{% block content %}
<div class="card">
  <p>Welcome to PharmaBeaver—a tiny demo shop for training workflows. This build is intentionally simple and avoids vulnerabilities.</p>
  <p>Use the nav to register, log in, browse products, add items to your cart, check out, and review order history.</p>
</div>
{% endblock %}
"""

REGISTER_TPL = """
{% extends 'base.html' %}
{% block content %}
<h2>Create Account</h2>
<form method="post" class="card">
  {{ form.hidden_tag() }}
  <div class="row"><label>Username</label>{{ form.username(size=32) }}</div>
  <div class="row"><label>Password</label>{{ form.password(size=32) }}</div>
  <button type="submit">Register</button>
</form>
{% endblock %}
"""

LOGIN_TPL = """
{% extends 'base.html' %}
{% block content %}
<h2>Login</h2>
<form method="post" class="card">
  {{ form.hidden_tag() }}
  <div class="row"><label>Username</label>{{ form.username(size=32) }}</div>
  <div class="row"><label>Password</label>{{ form.password(size=32) }}</div>
  <button type="submit">Login</button>
</form>
{% endblock %}
"""

PRODUCTS_TPL = """
{% extends 'base.html' %}
{% block content %}
<h2>Products</h2>
{% for p in products %}
  <div class="card">
    <div class="row" style="align-items:flex-start;">
      <img src="{{ p.image_url }}" alt="{{ p.name }}" style="width:120px;height:80px;object-fit:cover;border-radius:8px;border:1px solid #eee;">
      <div style="flex:1;">
        <strong>{{ p.name }}</strong>
        {% if p.prescription_required %}
          <span class="chip">Rx</span>
        {% endif %}<br>
        <div style="color:#555; margin:.25rem 0 0.5rem 0;">{{ p.description }}</div>
        <div style="font-weight:600;">${{ '%.2f' % (p.price_cents/100) }}</div>
      </div>
      <div>
        <form method="post" action="{{ url_for('add_to_cart', product_id=p.id) }}">
          {{ add_form.hidden_tag() }}
          {{ add_form.quantity(min=1, max=99) }}
          <button type="submit">Add to cart</button>
        </form>
      </div>
    </div>
  </div>
{% else %}
  <p>No products yet.</p>
{% endfor %}
{% endblock %}
"""

CART_TPL = """
{% extends 'base.html' %}
{% block content %}
<h2>My Cart</h2>
{% if items %}
  {% for item in items %}
    <div class="card row">
      <div>
        <strong>{{ item.product.name }}</strong> — Qty: {{ item.quantity }}
      </div>
      <div>${{ '%.2f' % ((item.product.price_cents * item.quantity)/100) }}</div>
    </div>
  {% endfor %}
  <div class="card row">
    <strong>Total</strong>
    <div>${{ '%.2f' % (total_cents/100) }}</div>
  </div>
  <form method="post" action="{{ url_for('cart') }}" style="display:inline-block;margin-right:.5rem;">
    {{ clear_form.hidden_tag() }}
    <button type="submit">Clear Cart</button>
  </form>
  <form method="post" action="{{ url_for('checkout') }}" style="display:inline-block;">
    {{ checkout_form.hidden_tag() }}
    <button type="submit">Checkout</button>
  </form>
{% else %}
  <p>Your cart is empty.</p>
{% endif %}
{% endblock %}
"""

ORDERS_TPL = """
{% extends 'base.html' %}
{% block content %}
<h2>My Orders</h2>
{% if orders %}
  {% for o in orders %}
    <div class="card">
      <div><strong>Order #{{ o.id }}</strong> — {{ o.created_at.strftime("%Y-%m-%d %H:%M") }}</div>
      <ul>
        {% for it in o.items %}
          <li>{{ it.product.name }} — Qty {{ it.quantity }} — ${{ '%.2f' % (it.price_cents_snapshot/100) }}</li>
        {% endfor %}
      </ul>
      <div><strong>Total:</strong> ${{ '%.2f' % (o.total_cents()/100) }}</div>
    </div>
  {% endfor %}
{% else %}
  <p>No orders yet.</p>
{% endif %}
{% endblock %}
"""

# Register in-memory templates
app.jinja_loader = DictLoader({
    "base.html": BASE,
    "index.html": INDEX_TPL,
    "register.html": REGISTER_TPL,
    "login.html": LOGIN_TPL,
    "products.html": PRODUCTS_TPL,
    "cart.html": CART_TPL,
    "orders.html": ORDERS_TPL,
})

# --- Routes ---
@app.route("/")
def index():
    return render_template_string(INDEX_TPL)

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already taken.")
            return redirect(url_for("register"), code=303)
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome! Account created.")
        return redirect(url_for("products"), code=303)
    return render_template_string(REGISTER_TPL, form=form)

# @app.route("/login", methods=["GET", "POST"])
# def login():
#     if current_user.is_authenticated:
#         return redirect(url_for("index"))
#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(username=form.username.data).first()
#         if not user or not user.check_password(form.password.data):
#             flash("Invalid credentials.")
#             return redirect(url_for("login"), code=303)
#         login_user(user, remember=True)
#         flash("Logged in.")
#         return redirect(url_for("products"), code=303)
#     return render_template_string(LOGIN_TPL, form=form)

# --- Helper: detect classic SQLi tautologies (SQLite-friendly) ---
SQLI_TAUTOLOGY_PATTERNS = [
    r"""(?i)'\s*or\s*'1'\s*=\s*'1""",
    r"""(?i)'\s*or\s*1\s*=\s*1""",
    r"""(?i)'\s*or\s*'x'\s*=\s*'x""",
    r"""(?i)'\s*or\s*'a'\s*=\s*'a""",
    r"""(?i)'\s*or\s*exists\s*\(\s*select""",
]

def looks_like_sqli_tautology(s: str) -> bool:
    return any(re.search(p, s or "") for p in SQLI_TAUTOLOGY_PATTERNS)


# --- Route: Vulnerable Login (simulated), same UX as /login ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data or ""
        password = form.password.data or ""

        # "Insecure query" that would be run in a real vuln 
        insecure_sql = (
            "SELECT id, username FROM user "
            f"WHERE username='{username}' AND password='{password}'"
        )

        # Find the user; in a real vuln, password check would be bypassed by SQL,
        # here we SIMULATE that bypass on known tautology payloads.
        user = User.query.filter_by(username=username).first()
        if user and (looks_like_sqli_tautology(password) or user.check_password(password)):
            login_user(user, remember=True)
            flash("Logged in.")
            return redirect(url_for("products"), code=303)

        flash("Invalid credentials.")
        return redirect(url_for("login"), code=303)

    return render_template_string(LOGIN_TPL, form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.")
    return redirect(url_for("index"), code=303)

@app.route("/products", methods=["GET"])
def products():
    products = Product.query.order_by(Product.name).all()
    form = AddToCartForm()
    return render_template_string(PRODUCTS_TPL, products=products, add_form=form)

@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id: int):
    form = AddToCartForm()
    if not form.validate_on_submit():
        # helpful debug if it ever fails again
        flash(f"Invalid request: {form.errors}")
        return redirect(url_for("products"), code=303)

    product = db.session.get(Product, product_id)
    if not product:
        flash("Product not found.")
        return redirect(url_for("products"), code=303)

    qty = form.quantity.data or 1
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if item:
        item.quantity = min(item.quantity + qty, 99)
    else:
        item = CartItem(user_id=current_user.id, product_id=product.id, quantity=qty)
        db.session.add(item)
    db.session.commit()
    flash("Added to cart.")
    # land on cart so you can see it
    return redirect(url_for("cart"), code=303)

@app.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
    clear_form = ClearCartForm()
    checkout_form = CheckoutForm()
    if request.method == "POST" and clear_form.validate_on_submit():
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash("Cart cleared.")
        return redirect(url_for("cart"), code=303)
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_cents = sum(i.product.price_cents * i.quantity for i in items)
    return render_template_string(
        CART_TPL,
        items=items,
        total_cents=total_cents,
        clear_form=clear_form,
        checkout_form=checkout_form,
    )

@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    form = CheckoutForm()
    if not form.validate_on_submit():
        flash("Invalid checkout request.")
        return redirect(url_for("cart"), code=303)

    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash("Your cart is empty.")
        return redirect(url_for("cart"), code=303)

    order = Order(user_id=current_user.id)
    db.session.add(order)
    db.session.flush()  # get order.id

    for ci in items:
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=ci.product_id,
                quantity=ci.quantity,
                price_cents_snapshot=ci.product.price_cents,
            )
        )

    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    flash(f"Order #{order.id} placed. Total ${order.total_cents()/100:.2f}")
    return redirect(url_for("orders"), code=303)

@app.route("/orders")
@login_required
def orders():
    my_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template_string(ORDERS_TPL, orders=my_orders)


# --- Tables only (no seeding here) ---
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
