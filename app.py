from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from paystackapi.paystack import Paystack

app = Flask(__name__)

# Paystack configuration (use environment variables for security)
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_your_secret_key")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "pk_test_your_public_key")
paystack = Paystack(secret_key=PAYSTACK_SECRET_KEY)

# Email configuration (use environment variables for security)
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "your_email@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your_app_password")
ORG_EMAIL = "elchayautismorg@gmail.com"

# Path to store donation records
DONATION_FILE = "donations.csv"

# Initialize the CSV file with headers if it doesn't exist
if not os.path.exists(DONATION_FILE):
    with open(DONATION_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Name", "Email", "Amount", "Reference", "Status"])

@app.route('/')
def index():
    return render_template('index.html', paystack_key=PAYSTACK_PUBLIC_KEY)

@app.route('/pay', methods=['POST'])
def pay():
    name = request.form.get('name')
    email = request.form.get('email')
    amount = request.form.get('amount')

    # Validate amount
    try:
        amount = int(amount)
        if amount < 100:
            return jsonify({"status": "error", "message": "Amount must be at least 100 NGN"}), 400
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid amount"}), 400

    try:
        # Initialize Paystack transaction using paystackapi
        response = paystack.transaction.initialize(
            amount=amount * 100,  # Convert to kobo
            email=email,
            currency="NGN",
            reference=f"elchay_donation_{int(os.urandom(8).hex(), 16)}",
            callback_url="https://donate-elchay-autism.onrender.com/verify-payment"
        )

        if response['status']:
            return jsonify({'status': 'success', 'data': response['data']})
        else:
            print(f"Paystack API error: {response['message']}")
            return jsonify({"status": "error", "message": f"Payment initialization failed: {response['message']}"}), 400

    except Exception as e:
        print(f"Paystack API exception: {str(e)}")
        return jsonify({"status": "error", "message": f"Payment initialization failed: {str(e)}"}), 500

@app.route('/verify/<reference>', methods=['GET'])
def verify(reference):
    try:
        response = paystack.transaction.verify(reference=reference)
        if response['status'] and response['data']['status'] == 'success':
            name = request.args.get('name', 'Unknown')
            email = request.args.get('email', 'Unknown')
            amount = request.args.get('amount', '0')

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(DONATION_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, name, email, amount, reference, "Success"])

            send_email(name, email, amount, reference)

            return jsonify({"status": "success", "message": "Payment verified successfully"})
        else:
            print(f"Paystack verification failed: {response['message']}")
            return jsonify({"status": "error", "message": "Payment verification failed"}), 400
    except Exception as e:
        error_message = f"Payment verification failed: {str(e)}"
        print(f"Paystack verification exception: {error_message}")
        return jsonify({"status": "error", "message": error_message}), 500

@app.route('/verify-payment')
def verify_payment():
    reference = request.args.get('reference')
    if not reference:
        return redirect(url_for('index', _anchor='cancel'))

    try:
        response = paystack.transaction.verify(reference=reference)
        if response['status'] and response['data']['status'] == 'success':
            return redirect(url_for('index', _anchor='success'))
        else:
            return redirect(url_for('index', _anchor='cancel'))
    except Exception as e:
        print(f"Paystack verification exception: {str(e)}")
        return redirect(url_for('index', _anchor='cancel'))

def send_email(name, email, amount, reference):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = ORG_EMAIL
    msg['Subject'] = f"New Donation Received - {name}"

    body = f"""
    A new donation has been received!

    Donator Name: {name}
    Donator Email: {email}
    Amount: NGN {amount}
    Reference: {reference}
    Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    Thank you for supporting Elchay Autism Initiative!
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, ORG_EMAIL, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)