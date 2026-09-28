from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from twilio.rest import Client

import random
import os

from datetime import datetime, timedelta


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)


# =========================================================
# CONFIGURATION
# =========================================================

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "homeo-development-secret-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///database.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)


# =========================================================
# TWILIO CONFIGURATION
# =========================================================
#
# Set these environment variables before using real OTP:
#
# TWILIO_ACCOUNT_SID
# TWILIO_AUTH_TOKEN
# TWILIO_PHONE_NUMBER
#
# =========================================================

TWILIO_ACCOUNT_SID = os.environ.get(
    "TWILIO_ACCOUNT_SID",
    ""
)

TWILIO_AUTH_TOKEN = os.environ.get(
    "TWILIO_AUTH_TOKEN",
    ""
)

TWILIO_PHONE_NUMBER = os.environ.get(
    "TWILIO_PHONE_NUMBER",
    ""
)


# =========================================================
# CUSTOMER MODEL
# =========================================================

class Customer(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    mobile = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    address = db.Column(
        db.Text,
        nullable=False
    )

    mobile_verified = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# CREATE DATABASE
# =========================================================

with app.app_context():
    db.create_all()


# =========================================================
# OTP GENERATOR
# =========================================================

def generate_otp():

    return str(
        random.randint(100000, 999999)
    )


# =========================================================
# SEND OTP
# =========================================================

def send_otp(mobile, otp):

    # Check Twilio configuration first

    if not TWILIO_ACCOUNT_SID:
        print("TWILIO_ACCOUNT_SID is missing.")
        return False

    if not TWILIO_AUTH_TOKEN:
        print("TWILIO_AUTH_TOKEN is missing.")
        return False

    if not TWILIO_PHONE_NUMBER:
        print("TWILIO_PHONE_NUMBER is missing.")
        return False

    try:

        client = Client(
            TWILIO_ACCOUNT_SID,
            TWILIO_AUTH_TOKEN
        )

        message = client.messages.create(

            body=(
                f"Your Homeo verification OTP is {otp}. "
                f"It is valid for 5 minutes."
            ),

            from_=TWILIO_PHONE_NUMBER,

            to=mobile
        )

        print(
            "OTP sent successfully:",
            message.sid
        )

        return True

    except Exception as e:

        print(
            "Twilio OTP error:",
            e
        )

        return False


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        # Get form data

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        mobile = request.form.get(
            "mobile",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        address = request.form.get(
            "address",
            ""
        ).strip()


        # -----------------------------------------
        # VALIDATION
        # -----------------------------------------

        if not all([
            name,
            email,
            mobile,
            password,
            address
        ]):

            flash(
                "Please fill in all required fields."
            )

            return redirect(
                url_for("register")
            )


        # Password length

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters."
            )

            return redirect(
                url_for("register")
            )


        # -----------------------------------------
        # CHECK EMAIL
        # -----------------------------------------

        existing_email = Customer.query.filter_by(
            email=email
        ).first()

        if existing_email:

            flash(
                "This email address is already registered."
            )

            return redirect(
                url_for("register")
            )


        # -----------------------------------------
        # CHECK MOBILE
        # -----------------------------------------

        existing_mobile = Customer.query.filter_by(
            mobile=mobile
        ).first()

        if existing_mobile:

            flash(
                "This mobile number is already registered."
            )

            return redirect(
                url_for("register")
            )


        # -----------------------------------------
        # GENERATE OTP
        # -----------------------------------------

        otp = generate_otp()

        otp_expiry = (
            datetime.utcnow()
            + timedelta(minutes=5)
        )


        # -----------------------------------------
        # STORE TEMPORARY REGISTRATION
        # -----------------------------------------

        session["registration"] = {

            "name": name,

            "email": email,

            "mobile": mobile,

            "password": generate_password_hash(
                password
            ),

            "address": address,

            "otp": otp,

            "otp_expiry": otp_expiry.isoformat()

        }


        # -----------------------------------------
        # SEND OTP
        # -----------------------------------------

        if send_otp(
            mobile,
            otp
        ):

            flash(
                "A 6-digit OTP has been sent to your mobile number."
            )

            return redirect(
                url_for("verify_otp")
            )

        else:

            session.pop(
                "registration",
                None
            )

            flash(
                "Unable to send OTP. Please check your Twilio configuration."
            )

            return redirect(
                url_for("register")
            )


    return render_template(
        "register.html"
    )


# =========================================================
# VERIFY OTP
# =========================================================

@app.route(
    "/verify-otp",
    methods=["GET", "POST"]
)
def verify_otp():

    registration = session.get(
        "registration"
    )


    # -----------------------------------------
    # CHECK REGISTRATION SESSION
    # -----------------------------------------

    if not registration:

        flash(
            "Your registration session has expired. Please register again."
        )

        return redirect(
            url_for("register")
        )


    # -----------------------------------------
    # VERIFY OTP
    # -----------------------------------------

    if request.method == "POST":

        entered_otp = request.form.get(
            "otp",
            ""
        ).strip()

        stored_otp = registration.get(
            "otp"
        )

        expiry = datetime.fromisoformat(
            registration["otp_expiry"]
        )


        # -----------------------------------------
        # OTP EXPIRATION
        # -----------------------------------------

        if datetime.utcnow() > expiry:

            session.pop(
                "registration",
                None
            )

            flash(
                "OTP has expired. Please register again."
            )

            return redirect(
                url_for("register")
            )


        # -----------------------------------------
        # OTP CHECK
        # -----------------------------------------

        if entered_otp != stored_otp:

            flash(
                "Invalid OTP. Please try again."
            )

            return redirect(
                url_for("verify_otp")
            )


        # -----------------------------------------
        # CREATE CUSTOMER
        # -----------------------------------------

        customer = Customer(

            name=registration["name"],

            email=registration["email"],

            mobile=registration["mobile"],

            password=registration["password"],

            address=registration["address"],

            mobile_verified=True

        )

        db.session.add(customer)

        db.session.commit()


        # -----------------------------------------
        # REMOVE REGISTRATION SESSION
        # -----------------------------------------

        session.pop(
            "registration",
            None
        )


        flash(
            "Registration successful! Please login to continue."
        )

        return redirect(
            url_for("login")
        )


    return render_template(
        "verify_otp.html"
    )


# =========================================================
# RESEND OTP
# =========================================================

@app.route("/resend-otp")
def resend_otp():

    registration = session.get(
        "registration"
    )


    if not registration:

        flash(
            "Your registration session has expired."
        )

        return redirect(
            url_for("register")
        )


    # Generate new OTP

    otp = generate_otp()


    registration["otp"] = otp

    registration["otp_expiry"] = (
        datetime.utcnow()
        + timedelta(minutes=5)
    ).isoformat()


    session["registration"] = registration


    # Send OTP

    if send_otp(
        registration["mobile"],
        otp
    ):

        flash(
            "A new OTP has been sent to your mobile number."
        )

    else:

        flash(
            "Unable to send OTP. Please try again."
        )


    return redirect(
        url_for("verify_otp")
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        mobile = request.form.get(
            "mobile",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        # -----------------------------------------
        # FIND CUSTOMER
        # -----------------------------------------

        customer = Customer.query.filter_by(
            mobile=mobile
        ).first()


        if not customer:

            flash(
                "Mobile number is not registered."
            )

            return redirect(
                url_for("login")
            )


        # -----------------------------------------
        # CHECK MOBILE VERIFICATION
        # -----------------------------------------

        if not customer.mobile_verified:

            flash(
                "Please verify your mobile number first."
            )

            return redirect(
                url_for("login")
            )


        # -----------------------------------------
        # CHECK PASSWORD
        # -----------------------------------------

        if not check_password_hash(
            customer.password,
            password
        ):

            flash(
                "Incorrect password."
            )

            return redirect(
                url_for("login")
            )


        # -----------------------------------------
        # CREATE LOGIN SESSION
        # -----------------------------------------

        session.clear()

        session["customer_id"] = customer.id


        # -----------------------------------------
        # LOGIN SUCCESS
        # -----------------------------------------

        return redirect(
            url_for("dashboard")
        )


    return render_template(
        "login.html"
    )


# =========================================================
# CUSTOMER DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    customer_id = session.get(
        "customer_id"
    )


    # -----------------------------------------
    # CUSTOMER NOT LOGGED IN
    # -----------------------------------------

    if not customer_id:

        flash(
            "Please login to access your account."
        )

        return redirect(
            url_for("login")
        )


    # -----------------------------------------
    # FIND CUSTOMER
    # -----------------------------------------

    customer = db.session.get(
        Customer,
        customer_id
    )


    # -----------------------------------------
    # CUSTOMER NOT FOUND
    # -----------------------------------------

    if not customer:

        session.clear()

        flash(
            "Customer account could not be found."
        )

        return redirect(
            url_for("login")
        )


    # -----------------------------------------
    # SHOW DASHBOARD
    # -----------------------------------------

    return render_template(
        "dashboard.html",
        customer=customer
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out successfully."
    )

    return redirect(
        url_for("login")
    )


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    # If customer is already logged in,
    # send them to dashboard.

    if session.get("customer_id"):

        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )