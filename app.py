import os
from datetime import date, datetime
from io import BytesIO
import base64

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")

DEFAULT_CATEGORIES = [
    ("Food", "expense"), ("Transport", "expense"), ("Rent", "expense"),
    ("Healthcare", "expense"), ("Education", "expense"), ("Shopping", "expense"),
    ("Entertainment", "expense"), ("Utilities", "expense"), ("Other", "expense"),
    ("Salary", "income"), ("Allowance", "income"), ("Other income", "income")
]

def make_engine():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        # Render and some providers supply postgres://; normalize if needed.
        if url.startswith("mysql://"):
            url = url.replace("mysql://", "mysql+pymysql://", 1)
        return create_engine(url, pool_pre_ping=True, future=True)
    # Convenient local fallback; set DATABASE_URL to MySQL for MySQL persistence.
    return create_engine("sqlite:///expenses.db", connect_args={"check_same_thread": False}, future=True)

engine = make_engine()

def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTO_INCREMENT,
                category_name VARCHAR(80) NOT NULL,
                category_type VARCHAR(20) NOT NULL,
                UNIQUE(category_name, category_type)
            )
        """) if engine.dialect.name == "mysql" else text("""
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name VARCHAR(80) NOT NULL,
                category_type VARCHAR(20) NOT NULL,
                UNIQUE(category_name, category_type)
            )
        """))
        if engine.dialect.name == "mysql":
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS expenses (
                    expense_id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    expense_date DATE NOT NULL,
                    category_id INTEGER NOT NULL,
                    amount DECIMAL(12,2) NOT NULL,
                    description VARCHAR(255) NOT NULL,
                    payment_method VARCHAR(40) NOT NULL,
                    CONSTRAINT fk_expense_category FOREIGN KEY (category_id)
                    REFERENCES categories(category_id),
                    CONSTRAINT chk_amount_positive CHECK (amount > 0)
                )
            """))
        else:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS expenses (
                    expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expense_date DATE NOT NULL,
                    category_id INTEGER NOT NULL,
                    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
                    description VARCHAR(255) NOT NULL,
                    payment_method VARCHAR(40) NOT NULL,
                    FOREIGN KEY (category_id) REFERENCES categories(category_id)
                )
            """))
        for name, kind in DEFAULT_CATEGORIES:
            exists = conn.execute(text(
                "SELECT category_id FROM categories WHERE category_name=:n AND category_type=:t"
            ), {"n": name, "t": kind}).first()
            if not exists:
                conn.execute(text(
                    "INSERT INTO categories (category_name, category_type) VALUES (:n, :t)"
                ), {"n": name, "t": kind})

try:
    init_db()
except SQLAlchemyError as exc:
    print("Database initialization failed. Check DATABASE_URL and schema permissions:", exc)

def read_df(query, params=None):
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params or {})

def chart_base64(fig):
    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

def build_charts(df):
    charts = {}
    expenses = df[df["category_type"] == "expense"].copy() if not df.empty else df
    if not expenses.empty:
        by_cat = expenses.groupby("category_name")["amount"].sum().sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.pie(by_cat.values, labels=by_cat.index, autopct="%1.1f%%", startangle=90)
        ax.set_title("Expense Distribution by Category")
        charts["category"] = chart_base64(fig)

        expenses["month"] = pd.to_datetime(expenses["expense_date"]).dt.to_period("M").astype(str)
        by_month = expenses.groupby("month")["amount"].sum().sort_index()
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(by_month.index, by_month.values)
        ax.set_title("Monthly Expenses")
        ax.set_xlabel("Month")
        ax.set_ylabel("Amount")
        ax.tick_params(axis="x", rotation=35)
        charts["monthly"] = chart_base64(fig)

    if not df.empty:
        df["month"] = pd.to_datetime(df["expense_date"]).dt.to_period("M").astype(str)
        totals = df.pivot_table(index="month", columns="category_type", values="amount", aggfunc="sum", fill_value=0)
        fig, ax = plt.subplots(figsize=(7, 4))
        for kind in ["income", "expense"]:
            if kind in totals.columns:
                ax.plot(totals.index, totals[kind], marker="o", label=kind.title())
        ax.set_title("Monthly Income vs Expenses")
        ax.set_xlabel("Month")
        ax.set_ylabel("Amount")
        ax.legend()
        ax.tick_params(axis="x", rotation=35)
        charts["income_expense"] = chart_base64(fig)
    return charts

@app.route("/")
def dashboard():
    today = date.today()
    month = request.args.get("month", today.strftime("%Y-%m"))
    category_id = request.args.get("category", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    query = """
        SELECT e.expense_id, e.expense_date, e.category_id, c.category_name,
               c.category_type, e.amount, e.description, e.payment_method
        FROM expenses e JOIN categories c ON c.category_id=e.category_id
        WHERE 1=1
    """
    params = {}
    if month and not (start_date or end_date):
        query += " AND " + ("DATE_FORMAT(e.expense_date, '%Y-%m')=:month" if engine.dialect.name == "mysql" else "strftime('%Y-%m', e.expense_date)=:month")
        params["month"] = month
    if category_id.isdigit():
        query += " AND e.category_id=:category_id"
        params["category_id"] = int(category_id)
    if start_date:
        query += " AND e.expense_date >= :start_date"
        params["start_date"] = start_date
    if end_date:
        query += " AND e.expense_date <= :end_date"
        params["end_date"] = end_date
    query += " ORDER BY e.expense_date DESC, e.expense_id DESC"
    try:
        df = read_df(query, params)
        all_df = read_df("""
            SELECT e.expense_date, c.category_name, c.category_type, e.amount
            FROM expenses e JOIN categories c ON c.category_id=e.category_id
        """)
        categories = read_df("SELECT category_id, category_name, category_type FROM categories ORDER BY category_type, category_name")
    except SQLAlchemyError as exc:
        flash("Database error. Check your database configuration: " + str(exc), "error")
        df, all_df = pd.DataFrame(), pd.DataFrame()
        categories = pd.DataFrame(columns=["category_id", "category_name", "category_type"])

    month_df = all_df.copy()
    if not month_df.empty:
        month_df["expense_date"] = pd.to_datetime(month_df["expense_date"])
        month_df = month_df[month_df["expense_date"].dt.strftime("%Y-%m") == month]
    income_total = float(month_df.loc[month_df["category_type"] == "income", "amount"].sum()) if not month_df.empty else 0
    expense_total = float(month_df.loc[month_df["category_type"] == "expense", "amount"].sum()) if not month_df.empty else 0
    expense_rows = all_df[all_df["category_type"] == "expense"] if not all_df.empty else all_df
    highest_category = "—"
    if not expense_rows.empty:
        totals = expense_rows.groupby("category_name")["amount"].sum()
        if not totals.empty:
            highest_category = str(totals.idxmax())
    charts = build_charts(all_df.copy()) if not all_df.empty else {}
    records = df.to_dict("records") if not df.empty else []
    return render_template("index.html", records=records, categories=categories.to_dict("records"),
        selected_month=month, selected_category=category_id, start_date=start_date, end_date=end_date,
        income_total=income_total, expense_total=expense_total, savings=income_total-expense_total,
        highest_category=highest_category, charts=charts, today=today.isoformat())

@app.route("/add", methods=["POST"])
def add_expense():
    try:
        expense_date = datetime.strptime(request.form.get("expense_date", ""), "%Y-%m-%d").date()
        amount = float(request.form.get("amount", "0"))
        description = request.form.get("description", "").strip()
        category_id = int(request.form.get("category_id", "0"))
        payment_method = request.form.get("payment_method", "").strip()
        if not np.isfinite(amount) or amount <= 0:
            raise ValueError("Amount must be a positive number.")
        if not description or len(description) > 255:
            raise ValueError("Description is required and must be at most 255 characters.")
        if not payment_method:
            raise ValueError("Please choose a payment method.")
        with engine.begin() as conn:
            category = conn.execute(text("SELECT category_id FROM categories WHERE category_id=:id"),
                                    {"id": category_id}).first()
            if not category:
                raise ValueError("Please choose a valid category.")
            conn.execute(text("""
                INSERT INTO expenses (expense_date, category_id, amount, description, payment_method)
                VALUES (:d, :c, :a, :desc, :p)
            """), {"d": expense_date, "c": category_id, "a": amount, "desc": description, "p": payment_method})
        flash("Transaction added successfully.", "success")
    except (ValueError, TypeError) as exc:
        flash(str(exc), "error")
    except SQLAlchemyError:
        flash("Could not save the transaction. Check the database connection.", "error")
    return redirect(url_for("dashboard"))

@app.route("/edit/<int:expense_id>", methods=["POST"])
def edit_expense(expense_id):
    try:
        expense_date = datetime.strptime(request.form.get("expense_date", ""), "%Y-%m-%d").date()
        amount = float(request.form.get("amount", "0"))
        category_id = int(request.form.get("category_id", "0"))
        description = request.form.get("description", "").strip()
        payment_method = request.form.get("payment_method", "").strip()
        if not np.isfinite(amount) or amount <= 0:
            raise ValueError("Amount must be positive.")
        if not description or not payment_method:
            raise ValueError("Description and payment method are required.")
        with engine.begin() as conn:
            conn.execute(text("""UPDATE expenses SET expense_date=:d, category_id=:c, amount=:a,
                description=:desc, payment_method=:p WHERE expense_id=:id"""),
                {"d": expense_date, "c": category_id, "a": amount, "desc": description,
                 "p": payment_method, "id": expense_id})
        flash("Transaction updated.", "success")
    except (ValueError, TypeError) as exc:
        flash(str(exc), "error")
    except SQLAlchemyError:
        flash("Could not update this transaction.", "error")
    return redirect(url_for("dashboard"))

@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM expenses WHERE expense_id=:id"), {"id": expense_id})
        flash("Transaction deleted.", "success")
    except SQLAlchemyError:
        flash("Could not delete this transaction.", "error")
    return redirect(url_for("dashboard"))

@app.route("/report.csv")
def export_csv():
    df = read_df("""SELECT e.expense_date, c.category_name, c.category_type, e.amount,
        e.description, e.payment_method FROM expenses e JOIN categories c
        ON c.category_id=e.category_id ORDER BY e.expense_date DESC""")
    return Response(df.to_csv(index=False), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=expense_report.csv"})

@app.route("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return jsonify(status="ok", database=engine.dialect.name)
    except SQLAlchemyError:
        return jsonify(status="error", message="database unavailable"), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
