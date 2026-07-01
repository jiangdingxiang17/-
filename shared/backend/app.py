import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DB_PATH = os.path.join(PROJECT_ROOT, 'fresh_market.db')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

VALID_CATEGORIES = ['蔬菜', '水果', '肉类', '鱼类']

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = 'fresh-market-secret-key'


def get_db_connection():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON;')
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def get_low_stock_alerts():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT id, name, category, stock, min_stock '
        'FROM products '
        'WHERE stock < min_stock '
        'ORDER BY stock ASC'
    )
    alerts = [dict(row) for row in cur.fetchall()]
    return alerts


def get_cart_items():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT c.id AS cart_item_id, '
        '       p.id AS product_id, '
        '       p.name AS product_name, '
        '       p.price AS unit_price, '
        '       c.quantity AS quantity, '
        '       (p.price * c.quantity) AS subtotal, '
        '       p.stock AS stock, '
        '       p.image_url AS image_url, '
        '       p.category AS category '
        'FROM cart_items c '
        'JOIN products p ON c.product_id = p.id '
        'ORDER BY c.id'
    )
    items = [dict(row) for row in cur.fetchall()]
    return items


def get_cart_total():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT COALESCE(SUM(p.price * c.quantity), 0) AS total '
        'FROM cart_items c '
        'JOIN products p ON c.product_id = p.id'
    )
    total = cur.fetchone()['total']
    return round(total, 2)


def get_cart_count():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COALESCE(SUM(quantity), 0) AS count FROM cart_items')
    count = cur.fetchone()['count']
    return count


@app.route('/')
def index():
    category = request.args.get('category', None)
    conn = get_db_connection()
    cur = conn.cursor()

    if category and category in VALID_CATEGORIES:
        cur.execute(
            'SELECT * FROM products WHERE category = ? ORDER BY id',
            (category,)
        )
    else:
        category = None
        cur.execute('SELECT * FROM products ORDER BY id')

    products = [dict(row) for row in cur.fetchall()]
    cart_items = get_cart_items()
    cart_total = get_cart_total()
    cart_count = get_cart_count()
    alerts = get_low_stock_alerts()

    return render_template(
        'index.html',
        products=products,
        categories=VALID_CATEGORIES,
        current_category=category,
        cart_items=cart_items,
        cart_total=cart_total,
        cart_count=cart_count,
        alerts=alerts
    )


@app.route('/cart')
def cart():
    cart_items = get_cart_items()
    cart_total = get_cart_total()
    cart_count = get_cart_count()
    alerts = get_low_stock_alerts()

    return render_template(
        'cart.html',
        cart_items=cart_items,
        cart_total=cart_total,
        cart_count=cart_count,
        alerts=alerts
    )


@app.route('/cart/add/<int:product_id>', methods=['POST'])
def cart_add(product_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cur.fetchone()

    if not product:
        flash('商品不存在', 'error')
        return redirect(url_for('index'))

    if product['stock'] <= 0:
        flash('库存不足，无法加入购物车', 'error')
        return redirect(url_for('index'))

    cur.execute('SELECT * FROM cart_items WHERE product_id = ?', (product_id,))
    existing = cur.fetchone()

    if existing:
        new_quantity = existing['quantity'] + 1
        if new_quantity > product['stock']:
            flash('库存不足，无法继续加购', 'error')
            return redirect(url_for('index'))
        cur.execute(
            'UPDATE cart_items SET quantity = ?, updated_at = datetime(\'now\', \'localtime\') '
            'WHERE id = ?',
            (new_quantity, existing['id'])
        )
    else:
        cur.execute(
            'INSERT INTO cart_items (product_id, quantity) VALUES (?, 1)',
            (product_id,)
        )

    conn.commit()
    flash(f'已将 {product["name"]} 加入购物车', 'success')
    return redirect(url_for('index'))


@app.route('/cart/update/<int:item_id>', methods=['POST'])
def cart_update(item_id):
    conn = get_db_connection()
    cur = conn.cursor()

    quantity_str = request.form.get('quantity', '1')
    try:
        quantity = int(quantity_str)
    except ValueError:
        flash('数量无效', 'error')
        return redirect(url_for('cart'))

    if quantity < 0:
        flash('数量不能为负数', 'error')
        return redirect(url_for('cart'))

    cur.execute(
        'SELECT c.*, p.stock, p.name '
        'FROM cart_items c JOIN products p ON c.product_id = p.id '
        'WHERE c.id = ?',
        (item_id,)
    )
    cart_item = cur.fetchone()

    if not cart_item:
        flash('购物车记录不存在', 'error')
        return redirect(url_for('cart'))

    if quantity == 0:
        cur.execute('DELETE FROM cart_items WHERE id = ?', (item_id,))
        conn.commit()
        flash(f'已从购物车移除 {cart_item["name"]}', 'info')
        return redirect(url_for('cart'))

    if quantity > cart_item['stock']:
        flash(f'库存不足，{cart_item["name"]} 当前库存仅 {cart_item["stock"]} 件', 'error')
        return redirect(url_for('cart'))

    cur.execute(
        'UPDATE cart_items SET quantity = ?, updated_at = datetime(\'now\', \'localtime\') '
        'WHERE id = ?',
        (quantity, item_id)
    )
    conn.commit()
    flash(f'已更新 {cart_item["name"]} 的数量', 'success')
    return redirect(url_for('cart'))


@app.route('/cart/delete/<int:item_id>', methods=['POST'])
def cart_delete(item_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        'SELECT c.*, p.name '
        'FROM cart_items c JOIN products p ON c.product_id = p.id '
        'WHERE c.id = ?',
        (item_id,)
    )
    cart_item = cur.fetchone()

    if not cart_item:
        flash('购物车记录不存在', 'error')
        return redirect(url_for('cart'))

    cur.execute('DELETE FROM cart_items WHERE id = ?', (item_id,))
    conn.commit()
    flash(f'已从购物车移除 {cart_item["name"]}', 'info')
    return redirect(url_for('cart'))


if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        from init_db import init_db
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
