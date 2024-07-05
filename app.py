# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)

# データベース設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# モデル定義
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(8), nullable=False, unique=True)
    stock = db.Column(db.Integer, default=0)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(8), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)


# データベース作成
with app.app_context():
    db.create_all()


# バリデーション関数
def is_valid_product_name(name):
    return name.isalpha() and len(name) <= 8


def is_valid_amount(amount):
    return isinstance(amount, int) and amount > 0


def is_valid_price(price):
    try:
        return float(price) >= 0
    except ValueError:
        return False


@app.route('/v1/stocks', methods=['POST'])
def update_stock():
    data = request.get_json()
    product_name = data.get('name')
    amount = data.get('amount', 1)

    if not product_name or not is_valid_product_name(product_name) or not is_valid_amount(amount):
        return jsonify({"message": "ERROR"}), 400

    product = Product.query.filter_by(name=product_name).first()
    if product:
        product.stock += amount
    else:
        product = Product(name=product_name, stock=amount)
        db.session.add(product)
    db.session.commit()

    response = jsonify({"name": product_name, "amount": amount})
    response.headers['Location'] = url_for(
        'check_stock', name=product_name, _external=True)
    return response, 200


@app.route('/v1/stocks', methods=['GET'])
@app.route('/v1/stocks/<string:name>', methods=['GET'])
def check_stock(name=None):
    if name:
        if not is_valid_product_name(name):
            return jsonify({"message": "ERROR"}), 400
        product = Product.query.filter_by(name=name).first()
        amount = product.stock if product else 0
        return jsonify({name: amount}), 200
    else:
        products = Product.query.filter(
            Product.stock > 0).order_by(Product.name).all()
        response = {product.name: product.stock for product in products}
        return jsonify(response), 200


@app.route('/v1/sales', methods=['POST'])
def sell_product():
    data = request.get_json()
    product_name = data.get('name')
    amount = data.get('amount', 1)
    price = data.get('price', 0)

    if not product_name or not is_valid_product_name(product_name) or not is_valid_amount(amount) or not is_valid_price(price):
        return jsonify({"message": "ERROR"}), 400

    product = Product.query.filter_by(name=product_name).first()
    if product is None or product.stock < amount:
        return jsonify({"message": "ERROR"}), 400

    product.stock -= amount
    if price != 0:
        db.session.add(Sale(product_name=product_name,
                       amount=amount, price=price))
    db.session.commit()

    if price == 0:
        response = jsonify({"name": product_name, "amount": amount})
    else:
        response = jsonify(
            {"name": product_name, "amount": amount, "price": price})
    response.headers['Location'] = url_for(
        'sell_product', name=product_name, _external=True)
    return response, 200


@app.route('/v1/sales', methods=['GET'])
def check_sales():
    sales = Sale.query.all()
    total_sales = sum(sale.amount * sale.price for sale in sales)
    return jsonify({"sales": round(total_sales, 2)}), 200


@app.route('/v1/stocks', methods=['DELETE'])
def reset_all():
    db.drop_all()
    db.create_all()
    return jsonify({"message": "All data reset"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
