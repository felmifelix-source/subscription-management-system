from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta
import secrets
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret")
DB_PATH = Path("instance/brightloop.db")
DB_PATH.parent.mkdir(exist_ok=True)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','staff','customer')),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            product_type TEXT NOT NULL,
            sales_price REAL NOT NULL,
            cost_price REAL NOT NULL DEFAULT 0,
            notes TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS plans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            billing_cycle TEXT NOT NULL,
            price REAL NOT NULL,
            min_quantity INTEGER NOT NULL DEFAULT 1,
            allow_pause INTEGER NOT NULL DEFAULT 1,
            allow_early_close INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS discounts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            discount_type TEXT NOT NULL,
            value REAL NOT NULL,
            minimum_quantity INTEGER NOT NULL DEFAULT 1,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            usage_limit INTEGER NOT NULL DEFAULT 100,
            used_count INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS subscriptions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL UNIQUE,
            customer_id INTEGER NOT NULL REFERENCES users(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            plan_id INTEGER NOT NULL REFERENCES plans(id),
            quantity INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            expiry_date TEXT,
            payment_terms TEXT NOT NULL DEFAULT 'Due on receipt',
            status TEXT NOT NULL DEFAULT 'Draft',
            discount_id INTEGER REFERENCES discounts(id),
            unit_price REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS invoices(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL UNIQUE,
            subscription_id INTEGER NOT NULL REFERENCES subscriptions(id),
            customer_id INTEGER NOT NULL REFERENCES users(id),
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            subtotal REAL NOT NULL,
            tax_rate REAL NOT NULL,
            tax_amount REAL NOT NULL,
            discount_amount REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Draft'
        );
        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL REFERENCES invoices(id),
            method TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            note TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS reset_tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            token TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0
        );
        """)
        if not con.execute("SELECT id FROM users WHERE email=?", ("admin@brightloop.local",)).fetchone():
            con.execute("INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                        ("Demo Admin","admin@brightloop.local",generate_password_hash("Admin@12345"),"admin",str(date.today())))
        if con.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"] == 0:
            con.executemany("INSERT INTO products(name,product_type,sales_price,cost_price,notes) VALUES(?,?,?,?,?)", [
                ("Starter Business Suite","Software",499,180,"Basic tools for small businesses"),
                ("Pro Business Suite","Software",999,350,"Advanced tools and reporting"),
                ("Cloud Storage Add-on","Add-on",199,60,"Additional cloud storage")
            ])
        if con.execute("SELECT COUNT(*) AS n FROM plans").fetchone()["n"] == 0:
            con.executemany("INSERT INTO plans(name,billing_cycle,price,min_quantity) VALUES(?,?,?,?)", [
                ("Monthly Starter","Monthly",499,1),("Quarterly Pro","Monthly",899,1),
                ("Annual Business","Yearly",9999,1),("Weekly Trial","Weekly",149,1)
            ])

def current_user():
    if "user_id" not in session:
        return None
    with db() as con:
        return con.execute("SELECT id,name,email,role FROM users WHERE id=?", (session["user_id"],)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login"))
            if user["role"] not in roles:
                flash("You do not have permission to open that page.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def money(value):
    return f"₹{float(value or 0):,.2f}"

@app.context_processor
def inject_globals():
    return {"me": current_user(), "money": money, "today": str(date.today())}

@app.route("/")
def index():
    return redirect(url_for("dashboard") if current_user() else url_for("login"))

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not name or not email or not password:
            flash("Please fill in every field.", "error")
        elif len(password) <= 8 or not any(c.isupper() for c in password) or not any(c.islower() for c in password) or not any(not c.isalnum() for c in password):
            flash("Password must be more than 8 characters and include uppercase, lowercase and a special character.", "error")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                                (name,email,generate_password_hash(password),"customer",str(date.today())))
                flash("Account created. You can now log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That email is already registered. Use another email.", "error")
    return render_template("auth.html", mode="signup")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash(f"Welcome, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/forgot-password", methods=["GET","POST"])
def forgot_password():
    demo_link = None
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        with db() as con:
            user = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if user:
                token = secrets.token_urlsafe(24)
                expiry = (datetime.now() + timedelta(hours=1)).isoformat()
                con.execute("INSERT INTO reset_tokens(user_id,token,expires_at) VALUES(?,?,?)",(user["id"],token,expiry))
                demo_link = url_for("reset_password", token=token, _external=True)
        flash("If the email exists, a reset link has been generated. In this demo, the link is displayed below instead of being emailed.", "success")
    return render_template("forgot.html", demo_link=demo_link)

@app.route("/reset/<token>", methods=["GET","POST"])
def reset_password(token):
    with db() as con:
        row = con.execute("""SELECT * FROM reset_tokens WHERE token=? AND used=0 AND expires_at>?""",
                           (token,datetime.now().isoformat())).fetchone()
        if not row:
            flash("This reset link is invalid or expired.", "error")
            return redirect(url_for("login"))
        if request.method == "POST":
            password = request.form.get("password","")
            if len(password) <= 8 or not any(c.isupper() for c in password) or not any(c.islower() for c in password) or not any(not c.isalnum() for c in password):
                flash("Use more than 8 characters with uppercase, lowercase and a special character.", "error")
            else:
                con.execute("UPDATE users SET password_hash=? WHERE id=?",(generate_password_hash(password),row["user_id"]))
                con.execute("UPDATE reset_tokens SET used=1 WHERE id=?",(row["id"],))
                flash("Password updated. Please log in.", "success")
                return redirect(url_for("login"))
    return render_template("reset.html")

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    with db() as con:
        if user["role"] == "customer":
            subs = con.execute("SELECT COUNT(*) n FROM subscriptions WHERE customer_id=?",(user["id"],)).fetchone()["n"]
            invoices = con.execute("SELECT COUNT(*) n FROM invoices WHERE customer_id=?",(user["id"],)).fetchone()["n"]
            outstanding = con.execute("SELECT COALESCE(SUM(total),0) n FROM invoices WHERE customer_id=? AND status!='Paid'",(user["id"],)).fetchone()["n"]
            revenue = con.execute("""SELECT COALESCE(SUM(p.amount),0) n FROM payments p JOIN invoices i ON p.invoice_id=i.id WHERE i.customer_id=?""",(user["id"],)).fetchone()["n"]
        else:
            subs = con.execute("SELECT COUNT(*) n FROM subscriptions").fetchone()["n"]
            invoices = con.execute("SELECT COUNT(*) n FROM invoices").fetchone()["n"]
            outstanding = con.execute("SELECT COALESCE(SUM(total),0) n FROM invoices WHERE status!='Paid'").fetchone()["n"]
            revenue = con.execute("SELECT COALESCE(SUM(amount),0) n FROM payments").fetchone()["n"]
        if user["role"] == "customer":
            recent = con.execute("""SELECT i.*,s.number sub_number FROM invoices i JOIN subscriptions s ON s.id=i.subscription_id WHERE i.customer_id=? ORDER BY i.id DESC LIMIT 5""",(user["id"],)).fetchall()
        else:
            recent = con.execute("""SELECT i.*,s.number sub_number,u.name customer_name FROM invoices i JOIN subscriptions s ON s.id=i.subscription_id JOIN users u ON u.id=i.customer_id ORDER BY i.id DESC LIMIT 5""").fetchall()
    return render_template("dashboard.html", stats={"subs":subs,"invoices":invoices,"outstanding":outstanding,"revenue":revenue}, recent=recent)

@app.route("/products", methods=["GET","POST"])
@login_required
@roles_required("admin")
def products():
    if request.method == "POST":
        with db() as con:
            con.execute("INSERT INTO products(name,product_type,sales_price,cost_price,notes) VALUES(?,?,?,?,?)",
                (request.form["name"].strip(),request.form["product_type"],float(request.form["sales_price"]),float(request.form.get("cost_price") or 0),request.form.get("notes","")))
        flash("Product added.", "success")
        return redirect(url_for("products"))
    with db() as con:
        rows = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template("products.html", rows=rows)

@app.route("/plans", methods=["GET","POST"])
@login_required
@roles_required("admin")
def plans():
    if request.method == "POST":
        with db() as con:
            con.execute("INSERT INTO plans(name,billing_cycle,price,min_quantity,allow_pause,allow_early_close) VALUES(?,?,?,?,?,?)",
                (request.form["name"].strip(),request.form["billing_cycle"],float(request.form["price"]),int(request.form.get("min_quantity") or 1),int("allow_pause" in request.form),int("allow_early_close" in request.form)))
        flash("Plan added.", "success")
        return redirect(url_for("plans"))
    with db() as con:
        rows = con.execute("SELECT * FROM plans ORDER BY id DESC").fetchall()
    return render_template("plans.html", rows=rows)

@app.route("/discounts", methods=["GET","POST"])
@login_required
@roles_required("admin")
def discounts():
    if request.method == "POST":
        with db() as con:
            con.execute("""INSERT INTO discounts(name,discount_type,value,minimum_quantity,start_date,end_date,usage_limit)
                VALUES(?,?,?,?,?,?,?)""",(request.form["name"],request.form["discount_type"],float(request.form["value"]),int(request.form.get("minimum_quantity") or 1),request.form["start_date"],request.form["end_date"],int(request.form.get("usage_limit") or 100)))
        flash("Discount rule created.", "success")
        return redirect(url_for("discounts"))
    with db() as con:
        rows = con.execute("SELECT * FROM discounts ORDER BY id DESC").fetchall()
    return render_template("discounts.html", rows=rows)

@app.route("/subscriptions", methods=["GET","POST"])
@login_required
def subscriptions():
    user = current_user()
    with db() as con:
        if request.method == "POST":
            if user["role"] == "customer":
                customer_id = user["id"]
            else:
                customer_id = int(request.form["customer_id"])
            product = con.execute("SELECT * FROM products WHERE id=? AND active=1",(request.form["product_id"],)).fetchone()
            plan = con.execute("SELECT * FROM plans WHERE id=?",(request.form["plan_id"],)).fetchone()
            if not product or not plan:
                flash("Choose a valid product and plan.", "error")
                return redirect(url_for("subscriptions"))
            quantity = max(1,int(request.form.get("quantity") or 1))
            if quantity < plan["min_quantity"]:
                flash(f"This plan requires at least {plan['min_quantity']} units.", "error")
                return redirect(url_for("subscriptions"))
            start = request.form.get("start_date") or str(date.today())
            expiry = request.form.get("expiry_date") or ""
            sub_number = "SUB-" + datetime.now().strftime("%y%m%d%H%M%S") + secrets.token_hex(2).upper()
            discount_value = request.form.get("discount_id") or None
            if discount_value:
                discount_row = con.execute("SELECT id FROM discounts WHERE id=? AND active=1", (discount_value,)).fetchone()
                discount_value = discount_row["id"] if discount_row else None
            con.execute("""INSERT INTO subscriptions(number,customer_id,product_id,plan_id,quantity,start_date,expiry_date,payment_terms,status,discount_id,unit_price,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(sub_number,customer_id,product["id"],plan["id"],quantity,start,expiry,request.form.get("payment_terms","Due on receipt"),"Draft",discount_value,float(plan["price"]),datetime.now().isoformat()))
            flash(f"Subscription {sub_number} created as Draft. Confirm it to generate an invoice.", "success")
            return redirect(url_for("subscriptions"))
        if user["role"] == "customer":
            rows = con.execute("""SELECT s.*,u.name customer,p.name product,pl.name plan FROM subscriptions s JOIN users u ON u.id=s.customer_id JOIN products p ON p.id=s.product_id JOIN plans pl ON pl.id=s.plan_id WHERE s.customer_id=? ORDER BY s.id DESC""",(user["id"],)).fetchall()
        else:
            rows = con.execute("""SELECT s.*,u.name customer,p.name product,pl.name plan FROM subscriptions s JOIN users u ON u.id=s.customer_id JOIN products p ON p.id=s.product_id JOIN plans pl ON pl.id=s.plan_id ORDER BY s.id DESC""").fetchall()
        products_rows = con.execute("SELECT * FROM products WHERE active=1").fetchall()
        plans_rows = con.execute("SELECT * FROM plans").fetchall()
        discounts_rows = con.execute("SELECT * FROM discounts WHERE active=1 AND start_date<=? AND end_date>=? AND used_count<usage_limit", (str(date.today()),str(date.today()))).fetchall()
        customers = con.execute("SELECT id,name,email FROM users WHERE role='customer' ORDER BY name").fetchall()
    return render_template("subscriptions.html", rows=rows, products=products_rows, plans=plans_rows, discounts=discounts_rows, customers=customers)

@app.route("/subscription/<int:sid>/<action>", methods=["POST"])
@login_required
def subscription_action(sid, action):
    user = current_user()
    with db() as con:
        sub = con.execute("SELECT * FROM subscriptions WHERE id=?",(sid,)).fetchone()
        if not sub or (user["role"]=="customer" and sub["customer_id"] != user["id"]):
            flash("Subscription not found.", "error")
            return redirect(url_for("subscriptions"))
        if user["role"] == "customer" and action not in ("pause","close"):
            flash("Only staff can perform this action.", "error")
            return redirect(url_for("subscriptions"))
        if action == "confirm" and user["role"] in ("admin","staff"):
            con.execute("UPDATE subscriptions SET status='Active' WHERE id=?",(sid,))
            existing = con.execute("SELECT id FROM invoices WHERE subscription_id=?",(sid,)).fetchone()
            if not existing:
                create_invoice(con, sub)
            flash("Subscription confirmed and invoice generated.", "success")
        elif action == "pause" and sub["status"]=="Active":
            con.execute("UPDATE subscriptions SET status='Paused' WHERE id=?",(sid,))
            flash("Subscription paused.", "success")
        elif action == "renew":
            if user["role"] not in ("admin","staff"):
                flash("Only staff can renew.", "error")
            else:
                con.execute("UPDATE subscriptions SET status='Active' WHERE id=?",(sid,))
                flash("Subscription renewed.", "success")
        elif action == "close":
            con.execute("UPDATE subscriptions SET status='Closed' WHERE id=?",(sid,))
            flash("Subscription closed.", "success")
        else:
            flash("That action is not available for the current status.", "warning")
    return redirect(url_for("subscriptions"))

def create_invoice(con, sub):
    subtotal = float(sub["unit_price"]) * int(sub["quantity"])
    today = date.today()
    tax_rate = 18.0
    discount_amount = 0.0
    discount_id = sub["discount_id"]
    if discount_id:
        disc = con.execute("SELECT * FROM discounts WHERE id=? AND active=1",(discount_id,)).fetchone()
        if disc and disc["start_date"] <= str(today) <= disc["end_date"] and disc["used_count"] < disc["usage_limit"] and sub["quantity"] >= disc["minimum_quantity"]:
            discount_amount = subtotal * disc["value"] / 100 if disc["discount_type"]=="Percentage" else disc["value"]
            discount_amount = min(discount_amount, subtotal)
            con.execute("UPDATE discounts SET used_count=used_count+1 WHERE id=?",(discount_id,))
    taxable = max(0, subtotal-discount_amount)
    tax_amount = taxable * tax_rate / 100
    total = taxable + tax_amount
    inv_number = "INV-" + datetime.now().strftime("%y%m%d%H%M%S") + secrets.token_hex(2).upper()
    due = today + timedelta(days=15)
    con.execute("""INSERT INTO invoices(number,subscription_id,customer_id,issue_date,due_date,subtotal,tax_rate,tax_amount,discount_amount,total,status)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(inv_number,sub["id"],sub["customer_id"],str(today),str(due),subtotal,tax_rate,tax_amount,discount_amount,total,"Confirmed"))

@app.route("/invoices")
@login_required
def invoices():
    user = current_user()
    with db() as con:
        if user["role"] == "customer":
            rows = con.execute("""SELECT i.*,s.number sub_number,u.name customer FROM invoices i JOIN subscriptions s ON s.id=i.subscription_id JOIN users u ON u.id=i.customer_id WHERE i.customer_id=? ORDER BY i.id DESC""",(user["id"],)).fetchall()
        else:
            rows = con.execute("""SELECT i.*,s.number sub_number,u.name customer FROM invoices i JOIN subscriptions s ON s.id=i.subscription_id JOIN users u ON u.id=i.customer_id ORDER BY i.id DESC""").fetchall()
    return render_template("invoices.html", rows=rows)

@app.route("/invoice/<int:iid>/send", methods=["POST"])
@login_required
@roles_required("admin","staff")
def send_invoice(iid):
    with db() as con:
        con.execute("UPDATE invoices SET status='Sent' WHERE id=? AND status='Confirmed'",(iid,))
    flash("Invoice marked as sent.", "success")
    return redirect(url_for("invoices"))

@app.route("/payments", methods=["GET","POST"])
@login_required
def payments():
    user = current_user()
    with db() as con:
        if request.method == "POST":
            invoice_id = int(request.form["invoice_id"])
            invoice = con.execute("SELECT * FROM invoices WHERE id=?",(invoice_id,)).fetchone()
            if not invoice or (user["role"]=="customer" and invoice["customer_id"] != user["id"]):
                flash("Invoice not found.", "error")
                return redirect(url_for("payments"))
            already = con.execute("SELECT COALESCE(SUM(amount),0) n FROM payments WHERE invoice_id=?",(invoice_id,)).fetchone()["n"]
            amount = float(request.form["amount"])
            balance = max(0,float(invoice["total"])-already)
            if amount <= 0 or amount > balance + 0.001:
                flash(f"Enter an amount between 0 and {money(balance)}.", "error")
            else:
                con.execute("INSERT INTO payments(invoice_id,method,amount,payment_date,note) VALUES(?,?,?,?,?)",
                    (invoice_id,request.form["method"],amount,request.form.get("payment_date") or str(date.today()),request.form.get("note","")))
                paid = already + amount
                con.execute("UPDATE invoices SET status=? WHERE id=?",("Paid" if paid >= invoice["total"]-0.001 else "Partially Paid",invoice_id))
                flash("Payment recorded.", "success")
            return redirect(url_for("payments"))
        if user["role"]=="customer":
            invs = con.execute("""SELECT i.* FROM invoices i WHERE i.customer_id=? AND i.status!='Paid' ORDER BY i.id DESC""",(user["id"],)).fetchall()
            rows = con.execute("""SELECT p.*,i.number invoice_number FROM payments p JOIN invoices i ON i.id=p.invoice_id WHERE i.customer_id=? ORDER BY p.id DESC""",(user["id"],)).fetchall()
        else:
            invs = con.execute("SELECT * FROM invoices WHERE status!='Paid' ORDER BY id DESC").fetchall()
            rows = con.execute("SELECT p.*,i.number invoice_number FROM payments p JOIN invoices i ON i.id=p.invoice_id ORDER BY p.id DESC").fetchall()
    return render_template("payments.html", invoices=invs, rows=rows)

@app.route("/staff", methods=["GET","POST"])
@login_required
@roles_required("admin")
def staff():
    if request.method == "POST":
        name=request.form["name"].strip(); email=request.form["email"].strip().lower()
        password=request.form["password"]
        if len(password)<=8 or not any(c.isupper() for c in password) or not any(c.islower() for c in password) or not any(not c.isalnum() for c in password):
            flash("Password must be more than 8 characters with uppercase, lowercase and a special character.","error")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                        (name,email,generate_password_hash(password),"staff",str(date.today())))
                flash("Staff account created.","success")
            except sqlite3.IntegrityError:
                flash("Email already exists.","error")
        return redirect(url_for("staff"))
    with db() as con:
        rows=con.execute("SELECT id,name,email,created_at FROM users WHERE role='staff' ORDER BY id DESC").fetchall()
    return render_template("staff.html",rows=rows)

@app.route("/reports")
@login_required
@roles_required("admin","staff")
def reports():
    with db() as con:
        by_status=con.execute("SELECT status,COUNT(*) count FROM subscriptions GROUP BY status").fetchall()
        paid=con.execute("SELECT COALESCE(SUM(amount),0) total FROM payments").fetchone()["total"]
        unpaid=con.execute("SELECT COALESCE(SUM(total),0) total FROM invoices WHERE status!='Paid'").fetchone()["total"]
        overdue=con.execute("SELECT COUNT(*) count FROM invoices WHERE status!='Paid' AND due_date<?",(str(date.today()),)).fetchone()["count"]
        customers=con.execute("SELECT COUNT(*) count FROM users WHERE role='customer'").fetchone()["count"]
    return render_template("reports.html",by_status=by_status,paid=paid,unpaid=unpaid,overdue=overdue,customers=customers)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
