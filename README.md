# Brightloop Subscription Management System

A beginner-friendly hackathon MVP built with Python, Flask, SQLite, HTML and CSS.

## Features
- Admin, staff and customer accounts
- Signup/login with unique email and password validation
- Product and plan management
- Subscription creation and status tracking
- Invoice generation with tax calculation
- Fixed/percentage discounts
- Payment recording
- Dashboard with revenue and outstanding totals
- Customer portal (customers only see their own subscriptions and invoices)

## Run locally (Windows / VS Code)

1. Install Python 3.10 or newer.
2. Extract this ZIP.
3. Open the `subscription_management_system` folder in VS Code.
4. Open Terminal > New Terminal.
5. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```

6. Install dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

7. Start the app:

   ```powershell
   py app.py
   ```

8. Open http://127.0.0.1:5000 in your browser.

## First login
- Email: `admin@brightloop.local`
- Password: `Admin@12345`

Change this demo password before using real data. The app creates the demo admin and sample data on first run.

## Team notes
- This is an MVP for the hackathon, not a production billing platform.
- Password reset is shown as a demo flow; real email delivery needs an email provider.
- Payments are recorded manually; no real card/bank payment gateway is connected.
- For GitHub, commit only source files. Do not upload `.venv`, database files, secrets or real customer data.
