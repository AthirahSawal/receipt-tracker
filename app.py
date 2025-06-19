import os
import re
import requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Create uploads folder if not exists
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Use writable path for SQLite DB on Render
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/receipts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Read OCR API key from environment variable
OCR_API_KEY = os.getenv('OCR_API_KEY')
if not OCR_API_KEY:
    raise ValueError("OCR_API_KEY environment variable not set")

# Receipt model
class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(100))
    date = db.Column(db.String(20))
    item = db.Column(db.String(200))
    price = db.Column(db.String(20))
    quantity = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('image')
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            try:
                with open(filepath, 'rb') as f:
                    response = requests.post(
                        'https://api.ocr.space/parse/image',
                        files={'file': f},  # fixed key here
                        data={'apikey': OCR_API_KEY, 'language': 'eng', 'isTable': True}
                    )
                result = response.json()
                parsed_text = result['ParsedResults'][0]['ParsedText']
            except Exception as e:
                print("OCR API Error:", e)
                return "OCR failed. Check logs.", 500

            lines = [line.strip() for line in parsed_text.split('\n') if line.strip()]

            # Shop name detection
            shop_name = "Not found"
            for line in lines[:5]:
                if len(line.split()) >= 2:
                    shop_name = line
                    break

            # Date detection
            date_match = re.search(r'(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})', parsed_text)
            date = date_match.group(0) if date_match else "Not found"

            # Extract items ignoring totals, cash etc.
            ignore_keywords = ['total', 'change', 'cash', 'balance', 'payment']
            items = []
            for line in lines:
                if re.search(r'\d+\.\d{2}', line):
                    if not any(k in line.lower() for k in ignore_keywords):
                        match = re.search(r'(.+?)\s+(\d+\.\d{2})$', line)
                        if match:
                            item_name = match.group(1).strip()
                            price = match.group(2)
                            items.append((item_name, price))

            # Save to DB
            for item_name, price in items:
                r = Receipt(shop_name=shop_name, date=date, item=item_name, price=price, quantity=1)
                db.session.add(r)
            db.session.commit()

            return redirect(url_for('index'))

    receipts = Receipt.query.order_by(Receipt.timestamp.desc()).all()
    return render_template('index.html', receipts=receipts)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        r = Receipt(
            shop_name=request.form['shop_name'],
            date=request.form['date'],
            item=request.form['item'],
            price=request.form['price'],
            quantity=int(request.form['quantity'])
        )
        db.session.add(r)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/delete/<int:id>')
def delete(id):
    r = Receipt.query.get_or_404(id)
    db.session.delete(r)
    db.session.commit()
    return redirect(url_for('index'))
