from flask import Flask, render_template, request, jsonify
import requests
import os
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

app = Flask(__name__)

# Paystack API keys (replace with your own keys)
PAYSTACK_SECRET_KEY = "sk_test_your_secret_key"  # Replace with your Paystack secret key
PAYSTACK_PUBLIC_KEY = "pk_test_your_public_key"  # Replace with your Paystack public key

# Email configuration (replace with your email credentials)
EMAIL_ADDRESS = "your_email@gmail.com"  # Replace with your Gmail address
EMAIL_PASSWORD = "your_app_password"  # Replace with your Gmail App Password (not your regular password)
ORG_EMAIL = "elchayautismorg@gmail.com"  # Organization email to receive notifications

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
    name = request.form.get('name')  # Get the donator's name
    email = request.form.get('email')
    amount = request.form.get('amount')  # Amount in kobo (e.g., 5000 NGN = 500000 kobo)

    # Paystack API to initialize transaction
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "email": email,
        "amount": int(amount) * 100,  # Convert to kobo
        "currency": "NGN"
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"status": "error", "message": "Payment initialization failed"}), 400

@app.route('/verify/<reference>', methods=['GET'])
def verify(reference):
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        verify_data = response.json()
        if verify_data['status'] and verify_data['data']['status'] == 'success':
            # Extract donation details from the request context or session
            # For simplicity, we'll assume the name, email, and amount are passed via query params
            # In a real app, you might use a session or database to store this temporarily
            name = request.args.get('name', 'Unknown')
            email = request.args.get('email', 'Unknown')
            amount = request.args.get('amount', '0')

            # Store the donation details in the CSV file
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(DONATION_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, name, email, amount, reference, "Success"])

            # Send email notification to the organization
            send_email(name, email, amount, reference)

            return jsonify({"status": "success", "message": "Payment verified successfully"})
        else:
            return jsonify({"status": "error", "message": "Payment verification failed"}), 400
    else:
        return jsonify({"status": "error", "message": "Payment verification failed"}), 400

def send_email(name, email, amount, reference):
    # Create the email message
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

    # Send the email
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, ORG_EMAIL, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == '__main__':
    app.run(debug=True)