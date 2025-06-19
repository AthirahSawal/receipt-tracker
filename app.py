from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
import pytesseract
import os
import re

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///receipts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Database model
class ReceiptItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop = db.Column(db.String(100))
    date = db.Column(db.String(20))
    item = db.Column(db.String(100))
    price = db.Column(db.String(20))
    quantity = db.Column(db.Integer, default=1)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['image']
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)
            lines = [line.strip() for line in text.split('\n') if line.strip()]

            # Shop name
            shop_name = "Not found"
            for line in lines[:10]:
                clean_line = re.sub(r'[^A-Za-z0-9\s&]', '', line)
                if len(clean_line.split()) >= 2 and len(clean_line) >= 5:
                    shop_name = clean_line.strip()
                    break

            # Date
            date_match = re.search(r'(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})', text)
            date = date_match.group(0) if date_match else "Not found"

            ignore_keywords = ['cash', 'change', 'total', 'subtotal', 'payment', 'balance', 'tax']
            for line in lines:
                lower_line = line.lower()
                if any(keyword in lower_line for keyword in ignore_keywords):
                    continue

                match = re.match(r'(.+?)\s+(\d+\.\d{2})$', line)
                if match:
                    item_name = match.group(1).strip()
                    price = match.group(2)
                    new_item = ReceiptItem(shop=shop_name, date=date, item=item_name, price=price, quantity=1)
                    db.session.add(new_item)

            db.session.commit()
            return redirect('/')

    all_items = ReceiptItem.query.order_by(ReceiptItem.id.desc()).all()
    return render_template('index.html', items=all_items)

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = ReceiptItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect('/')

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = ReceiptItem.query.get_or_404(item_id)
    if request.method == 'POST':
        item.shop = request.form['shop']
        item.date = request.form['date']
        item.item = request.form['item']
        item.price = request.form['price']
        item.quantity = request.form['quantity']
        db.session.commit()
        return redirect('/')
    return render_template('edit.html', item=item)

@app.route('/add', methods=['GET', 'POST'])
def add_manual():
    if request.method == 'POST':
        shop = request.form['shop']
        date = request.form['date']
        item = request.form['item']
        price = request.form['price']
        quantity = request.form.get('quantity', 1)

        new_item = ReceiptItem(shop=shop, date=date, item=item, price=price, quantity=quantity)
        db.session.add(new_item)
        db.session.commit()
        return redirect('/')
    return render_template('add.html')

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    with app.app_context():
        db.create_all()
    app.run(debug=True)
