from flask import Flask, render_template, request, redirect, url_for
import os
import re
import requests
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///receipts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Replace with your real OCR.Space API key
OCR_API_KEY = 'helloworld'  # ← Replace this with your key from ocr.space

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
        file = request.files['image']
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # Upload to OCR.Space
            with open(filepath, 'rb') as f:
                response = requests.post(
                    'https://api.ocr.space/parse/image',
                    files={'filename': f},
                    data={
                        'apikey': OCR_API_KEY,
                        'language': 'eng',
                        'isTable': True
                    }
                )
            result = response.json()
            parsed_text = result['ParsedResults'][0]['ParsedText']

            # Process the text
            lines = [line.strip() for line in parsed_text.split('\n') if line.strip()]

            # Shop name
            shop_name = "Not found"
            for line in lines[:5]:
                if len(line.split()) >= 2:
                    shop_name = line
                    break

            # Date
            date_match = re.search(r'(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})', parsed_text)
            date = date_match.group(0) if date_match else "Not found"

            # Item lines
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
            for name, price in items:
                r = Receipt(shop_name=shop_name, date=date, item=name, price=price, quantity=1)
                db.session.add(r)
            db.session.commit()
            return redirect(url_for('index'))

    receipts = Receipt.query.order_by(Receipt.timestamp.desc()).all()
    return render_template('index.html', receipts=receipts)

@app.route('/delete/<int:id>')
def delete(id):
    r = Receipt.query.get_or_404(id)
    db.session.delete(r)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        r = Receipt(
            shop_name=request.form['shop_name'],
            date=request.form['date'],
            item=request.form['item'],
            price=request.form['price'],
            quantity=request.form.get('quantity', 1)
        )
        db.session.add(r)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add.html')
