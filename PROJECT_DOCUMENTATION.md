# Brightloop Subscription Management System

## Project Documentation

**Project:** Subscription Management System\
**Project context:** Odoo Make-A-Ton 9.0 Hackathon\
**Application type:** Web-based subscription and billing management MVP

------------------------------------------------------------------------

## 1. Introduction

The Brightloop Subscription Management System is a web application
designed to help an organization manage customers, products,
subscription plans, subscriptions, invoices, discounts, and payment
records from one place.

The application provides different account roles for administrators,
staff members, and customers. Administrative and staff users can manage
subscription-related business records, while customers can access their
own subscription and invoice information through a customer portal.

This project is a hackathon minimum viable product (MVP) intended to
demonstrate the main workflow of subscription management.

## 2. Objectives

-   Organize customer, product, and subscription information in one
    application.
-   Support subscription creation and status tracking.
-   Generate invoices with tax and discount calculations.
-   Record payments against invoices.
-   Provide dashboard totals for revenue and outstanding amounts.
-   Give customers access to their own subscription and invoice details.
-   Separate access according to user roles.

## 3. Technology Stack

  -----------------------------------------------------------------------
  Technology                          Purpose
  ----------------------------------- -----------------------------------
  Python                              Main application programming
                                      language

  Flask                               Web framework and request routing

  SQLite                              Relational database for application
                                      records

  HTML                                Structure of the web pages

  CSS                                 Styling and page layout

  Werkzeug security utilities         Password hashing and password
                                      verification
  -----------------------------------------------------------------------

The repository also includes a `requirements.txt` file for Python
dependencies.

## 4. Main Features

### 4.1 User accounts and role-based access

The application supports three account roles:

-   **Admin:** Administrative access for managing the subscription
    system.
-   **Staff:** Staff access for operational subscription-related work.
-   **Customer:** Access to the customer portal and the customer's own
    records.

The signup and login flow validates user details. Email addresses are
required to be unique, and passwords are stored as password hashes
rather than plain text.

### 4.2 Product management

Products can be maintained with information such as product name,
product type, sales price, cost price, notes, and active status.

### 4.3 Subscription plan management

Plans define subscription options. Plan information includes the plan
name, billing cycle, price, minimum quantity, and whether pausing or
early closure is allowed.

### 4.4 Subscription management

A subscription connects a customer with a product and a plan. The record
can include a subscription number, quantity, start date, expiry date,
payment terms, status, unit price, and an optional discount.

### 4.5 Invoice generation

Invoices are associated with subscriptions and customers. Invoice
records include issue and due dates, subtotal, tax rate, tax amount,
discount amount, total, and invoice status.

### 4.6 Discounts

The system supports fixed-value and percentage-based discounts. Discount
records can include date validity, minimum quantity, usage limit, usage
count, and active status.

### 4.7 Payment recording

Payment records can be added against invoices. The application stores
details such as payment method, amount, payment date, and an optional
note.

**Note:** The current project records payments manually. It does not
connect to a live card or bank payment gateway.

### 4.8 Dashboard

The dashboard presents summary information, including revenue and
outstanding totals, to help users understand the current billing
position.

### 4.9 Customer portal

Customers can view their own subscriptions and invoices. The customer
portal is intended to keep one customer's records separate from those of
other customers.

## 5. Application Workflow

A typical workflow is:

1.  An administrator or authorized staff member signs in.
2.  Products and subscription plans are created or maintained.
3.  A customer account is registered or selected.
4.  A subscription is created by selecting the customer, product, plan,
    quantity, and relevant dates.
5.  Applicable discounts and tax are considered when an invoice is
    generated.
6.  The invoice is made available for tracking.
7.  A payment can be recorded against the invoice.
8.  Dashboard totals provide a summary of revenue and outstanding
    amounts.
9.  The customer signs in to view their own subscription and invoice
    information.

The exact actions available to each role depend on the access controls
implemented in the application.

## 6. Project Structure

The repository contains the following main items:

``` text
subscription-management-system/
│
├── app.py
├── requirements.txt
├── README.md
├── static/
├── templates/
└── .gitignore
```

-   **`app.py`** -- Flask application entry point. It contains
    application setup, database initialization, data handling, and web
    application routes.
-   **`requirements.txt`** -- Lists the Python packages required by the
    project.
-   **`templates/`** -- Contains HTML templates rendered by Flask.
-   **`static/`** -- Contains static assets such as CSS, JavaScript, and
    images, as applicable.
-   **`README.md`** -- Provides the repository overview and quick-start
    instructions.
-   **`.gitignore`** -- Specifies files and folders that Git should
    ignore.

The application database is configured at `instance/brightloop.db` and
is created/initialized by the application.

## 7. Database Overview

The SQLite database contains tables for the main application entities:

  Table             Purpose
  ----------------- -----------------------------------------------------
  `users`           User details, unique email, password hash, and role
  `products`        Product details and pricing
  `plans`           Subscription plan and billing-cycle details
  `discounts`       Discount rules and usage information
  `subscriptions`   Customer subscriptions and their status
  `invoices`        Invoice dates, amounts, tax, discounts, and status
  `payments`        Payment records linked to invoices
  `reset_tokens`    Password-reset token records

The database uses primary keys and relationships between records. For
example, subscriptions refer to customers, products, and plans; invoices
refer to subscriptions and customers; and payments refer to invoices.

## 8. Installation and Setup (Windows)

### Prerequisites

-   Windows 10 or later
-   Python 3.10 or newer
-   Git
-   Visual Studio Code or another code editor
-   A web browser

### Steps

1.  Clone the repository:

    ``` bash
    git clone https://github.com/felmifelix-source/subscription-management-system.git
    ```

2.  Open the project folder:

    ``` bash
    cd subscription-management-system
    ```

3.  Create a virtual environment:

    ``` bash
    py -m venv .venv
    ```

4.  Activate the virtual environment:

    ``` bash
    .venv\Scripts\activate
    ```

5.  Install the required packages:

    ``` bash
    py -m pip install -r requirements.txt
    ```

6.  Start the application:

    ``` bash
    py app.py
    ```

7.  Open the application in a browser:

    ``` text
    http://127.0.0.1:5000
    ```

The application initializes its local database when it starts.

## 9. Demo Login

The repository README documents the following demo administrator
account:

-   **Email:** `admin@brightloop.local`
-   **Password:** `Admin@12345`

This is a demo credential only. Change the demo password and development
secret before using the application with real information. Do not use
demo credentials for a production deployment.

## 10. Security and Data Handling Notes

-   Passwords are hashed using Werkzeug security utilities.
-   User email addresses are unique.
-   Database foreign-key enforcement is enabled.
-   The application uses a Flask secret key. Configure a strong secret
    through the `SECRET_KEY` environment variable for any deployment
    beyond local development.
-   Do not commit virtual environments, database files containing
    personal data, secrets, or real customer information to Git.
-   The password-reset flow is documented by the project as a demo flow;
    real email delivery requires an email provider.
-   The current payment feature records payments and is not a live
    payment gateway.

## 11. Current Scope and Limitations

This project is an MVP for a hackathon and is not a production billing
platform. The current documented limitations include:

-   Payments are recorded manually; no real card or bank payment gateway
    is connected.
-   Password reset is a demonstration flow; real email delivery requires
    an email provider.
-   Production use would require additional deployment, security,
    testing, backup, and operational work.

## 12. Possible Future Enhancements

The following are suggestions for future development, not claims about
existing functionality:

-   Integrate a secure payment gateway.
-   Add automated invoice and subscription-renewal notifications.
-   Connect a real email service for password reset and account
    notifications.
-   Add more detailed reports and export options.
-   Add automated tests for authentication, subscriptions, invoices,
    discounts, and payments.
-   Improve deployment configuration, logging, backups, and production
    security.

## 13. Conclusion

The Brightloop Subscription Management System brings key subscription
operations into one web application. By combining role-based accounts,
product and plan management, subscription tracking, invoice generation,
discount handling, payment recording, and a customer portal, the project
demonstrates an end-to-end subscription management workflow suitable for
an MVP.

------------------------------------------------------------------------

*Documentation prepared from the repository's published README and
application structure. Feature descriptions should be checked against
the latest code whenever the project changes.*
