# PennyWise — Personal Expense Tracking and Analysis System

A beginner-friendly Flask data analytics project based on Project 2 in the supplied Python Flask Data Analytics Projects document.

## Features
- Add, list, edit and delete income/expense transactions.
- Category, date-range and month filters.
- Monthly income, expense and net savings cards.
- Highest-spending category.
- Live category pie chart, monthly expense bar chart, and income-vs-expense line chart.
- CSV report export.
- Positive amount and required-field validation.
- SQLAlchemy parameterized database queries and `/health` endpoint.
- MySQL support via `DATABASE_URL`; SQLite is used automatically for local quick-start only.

## Technology
Python, Flask, MySQL, Pandas, NumPy, Matplotlib, SQLAlchemy, HTML/CSS.

## Run locally (Windows PowerShell)
1. Install Python 3.11 or later and verify `py --version`.
2. Extract this folder, open PowerShell in it.
3. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Install packages:
   ```powershell
   python -m pip install -r requirements.txt
   ```
5. Start the application:
   ```powershell
   python app.py
   ```
6. Open `http://127.0.0.1:5000`.

If the Windows `python` command opens the Microsoft Store, install Python from python.org and enable **Add Python to PATH**, or try `py` instead.

## Use MySQL (recommended for the project submission)
1. Run `schema.sql` in MySQL Workbench or MySQL command line.
2. Set `DATABASE_URL` to your MySQL connection URL. Example PowerShell (replace credentials/database):
   ```powershell
   $env:DATABASE_URL="mysql+pymysql://USERNAME:PASSWORD@HOST:3306/personal_expense_tracker"
   $env:SECRET_KEY="replace-with-a-long-random-secret"
   python app.py
   ```
   URL-encode special characters in the username/password. Keep credentials private and out of source control.
3. For hosted MySQL, use the provider's external connection URL and ensure the host allows connections from your app host.

## Deploy to Render (public URL)
1. Sign in to Render and create a **New Web Service** connected to a Git repository containing these files.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app`
4. Add environment variable `SECRET_KEY` with a long random value.
5. Add `DATABASE_URL` pointing to a hosted MySQL database if you want durable MySQL storage. The app falls back to a local SQLite file if this variable is omitted, but many hosts have ephemeral filesystems, so SQLite may reset after redeploy/restart.
6. Deploy. Render will provide a URL similar to `https://your-service-name.onrender.com`; the actual URL exists only after you deploy it.

**Important:** I cannot publish it to your account or create a real public URL without access to your hosting account/repository. Do not share passwords here. Follow the steps above and send me the deployment log or URL if you hit an error.

## Database design
- `categories(category_id PK, category_name, category_type)`
- `expenses(expense_id PK, expense_date, category_id FK, amount, description, payment_method)`

Relationship: one category can be linked to many expense/transaction records.

## Analysis methodology
- Monthly totals: sum amounts grouped by transaction month and type.
- Net savings: monthly income minus monthly expenses.
- Category breakdown: sum expense amounts by category; pie slices show each category's share of recorded expenses.
- Highest-spending category: category with the greatest total expense amount in the saved dataset.
- Monthly trend: expense totals grouped by calendar month.
- NumPy validates that the amount is a finite positive number; Pandas performs filtering, grouping and reporting; Matplotlib generates charts from saved transactions.

## API / routes
- `GET /` — dashboard and filters
- `POST /add` — create transaction
- `POST /edit/<id>` — update transaction
- `POST /delete/<id>` — delete transaction
- `GET /report.csv` — download CSV
- `GET /health` — basic health/database check

## Test checklist
- Valid income and expense can be added.
- Zero, negative, non-numeric and missing amounts are rejected.
- Month, date-range and category filters can be applied.
- Edit and delete update stored records.
- Empty database displays a friendly message.
- Charts are displayed after records are saved.
- CSV export contains saved transaction data.

## Scope and limitation
Single-user educational application with manually entered data. It does not connect to banks, payment gateways, or provide financial advice. Add authentication before allowing multiple users or sensitive data.
