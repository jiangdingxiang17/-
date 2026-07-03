import os
import sqlite3
import random
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, g, session
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DB_PATH = os.path.join(PROJECT_ROOT, 'fresh_market.db')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

VALID_CATEGORIES = ['蔬菜', '水果', '肉类', '鱼类']
FREE_SHIPPING_THRESHOLD = 50.0
EMPLOYEE_DISCOUNT_RATE = 0.95

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = os.environ.get('SECRET_KEY', 'fresh-market-dev-secret-key')


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


def database_needs_init():
    if not os.path.exists(DB_PATH):
        return True

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    has_users_table = cur.fetchone() is not None
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cart_items'")
    has_cart_table = cur.fetchone() is not None
    cart_has_user_id = False
    if has_cart_table:
        cur.execute('PRAGMA table_info(cart_items)')
        cart_columns = [row[1] for row in cur.fetchall()]
        cart_has_user_id = 'user_id' in cart_columns
    conn.close()
    return not has_users_table or not has_cart_table or not cart_has_user_id


def migrate_db():
    if not os.path.exists(DB_PATH):
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(products)")
    columns = [row[1] for row in cur.fetchall()]

    if 'is_active' not in columns:
        cur.execute('ALTER TABLE products ADD COLUMN is_active INTEGER DEFAULT 1')
        cur.execute(
            "UPDATE products SET is_active = 0 WHERE name LIKE '%（已下架）%'"
        )
        conn.commit()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='favorites'")
    if cur.fetchone() is None:
        cur.execute('''
            CREATE TABLE favorites (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                product_id  INTEGER NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                UNIQUE(user_id, product_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')
        cur.execute('CREATE INDEX idx_favorites_user_id ON favorites(user_id)')
        cur.execute('CREATE INDEX idx_favorites_product_id ON favorites(product_id)')
        conn.commit()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'")
    if cur.fetchone() is None:
        cur.execute('''
            CREATE TABLE reviews (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id     INTEGER NOT NULL,
                product_id   INTEGER NOT NULL,
                user_id      INTEGER NOT NULL,
                rating       INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comment      TEXT,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                UNIQUE(order_id, product_id),
                FOREIGN KEY (order_id)   REFERENCES orders(id)    ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)  ON DELETE CASCADE,
                FOREIGN KEY (user_id)    REFERENCES users(id)     ON DELETE CASCADE
            )
        ''')
        cur.execute('CREATE INDEX idx_reviews_order_id ON reviews(order_id)')
        cur.execute('CREATE INDEX idx_reviews_product_id ON reviews(product_id)')
        conn.commit()

    cur.execute('PRAGMA table_info(orders)')
    order_columns = [row[1] for row in cur.fetchall()]
    if 'original_price' not in order_columns:
        cur.execute('ALTER TABLE orders ADD COLUMN original_price REAL DEFAULT 0')
        cur.execute("UPDATE orders SET original_price = total_price WHERE original_price = 0")
        conn.commit()
    if 'discount_amount' not in order_columns:
        cur.execute('ALTER TABLE orders ADD COLUMN discount_amount REAL DEFAULT 0')
        cur.execute("UPDATE orders SET discount_amount = 0 WHERE discount_amount IS NULL")
        conn.commit()
    if 'shipping_fee' not in order_columns:
        cur.execute('ALTER TABLE orders ADD COLUMN shipping_fee REAL DEFAULT 0')
        cur.execute("UPDATE orders SET shipping_fee = 0 WHERE shipping_fee IS NULL")
        conn.commit()

    conn.close()


def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT id, username, role FROM users WHERE id = ?',
        (user_id,)
    )
    user = cur.fetchone()
    return dict(user) if user else None


@app.context_processor
def inject_current_user():
    current_user = get_current_user()
    cart_count = get_cart_count(current_user['id']) if current_user else 0
    return {
        'current_user': current_user,
        'cart_count': cart_count
    }


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            session.clear()
            flash('请先登录账号后再继续操作', 'warning')
            return redirect(url_for('login', next=request.path))
        return view_func(*args, **kwargs)
    return wrapped_view


def admin_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            session.clear()
            flash('请先登录账号后再继续操作', 'warning')
            return redirect(url_for('login', next=request.path))
        if current_user.get('role') != 'admin':
            flash('无权访问后台管理', 'danger')
            return redirect(url_for('index'))
        return view_func(*args, **kwargs)
    return wrapped_view


def get_safe_next_url(default_endpoint='index'):
    next_url = request.form.get('next') or request.args.get('next') or ''
    if next_url.startswith('/') and not next_url.startswith('//'):
        return next_url
    return url_for(default_endpoint)


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


def get_cart_items(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT c.id AS cart_item_id, '
        '       p.id AS product_id, '
        '       p.name AS product_name, '
        '       p.price AS unit_price, '
        '       c.quantity AS quantity, '
        '       ROUND(p.price * c.quantity, 2) AS subtotal, '
        '       p.stock AS stock, '
        '       p.image_url AS image_url, '
        '       p.category AS category '
        'FROM cart_items c '
        'JOIN products p ON c.product_id = p.id '
        'WHERE c.user_id = ? '
        'ORDER BY c.id',
        (user_id,)
    )
    items = [dict(row) for row in cur.fetchall()]
    return items


def get_cart_total(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT COALESCE(SUM(p.price * c.quantity), 0) AS total '
        'FROM cart_items c '
        'JOIN products p ON c.product_id = p.id '
        'WHERE c.user_id = ?',
        (user_id,)
    )
    total = cur.fetchone()['total']
    return round(total, 2)


def get_cart_count(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT COALESCE(SUM(quantity), 0) AS count FROM cart_items WHERE user_id = ?',
        (user_id,)
    )
    count = cur.fetchone()['count']
    return count


@app.route('/')
def index():
    category = request.args.get('category', None)
    q = request.args.get('q', '').strip()
    conn = get_db_connection()
    cur = conn.cursor()

    if q:
        # 搜索模式：按名称模糊搜索
        cur.execute(
            'SELECT * FROM products WHERE is_active = 1 AND name LIKE ? ORDER BY id',
            (f'%{q}%',)
        )
    elif category and category in VALID_CATEGORIES:
        cur.execute(
            'SELECT * FROM products WHERE category = ? AND is_active = 1 ORDER BY id',
            (category,)
        )
    else:
        category = None
        cur.execute('SELECT * FROM products WHERE is_active = 1 ORDER BY id')

    products = [dict(row) for row in cur.fetchall()]
    current_user = get_current_user()
    cart_items = get_cart_items(current_user['id']) if current_user else []
    cart_total = get_cart_total(current_user['id']) if current_user else 0
    alerts = get_low_stock_alerts()

    # 限时特惠：取价格最低的3个活跃商品（非搜索/非分类时展示）
    flash_deals = []
    if not q and not category:
        cur.execute(
            'SELECT * FROM products WHERE is_active = 1 AND stock > 0 '
            'ORDER BY price ASC LIMIT 3'
        )
        flash_deals = [dict(row) for row in cur.fetchall()]

    # 用户收藏的商品ID（用于显示收藏状态）
    favorite_ids = []
    if current_user:
        cur.execute(
            'SELECT product_id FROM favorites WHERE user_id = ?',
            (current_user['id'],)
        )
        favorite_ids = [row['product_id'] for row in cur.fetchall()]

    return render_template(
        'index.html',
        products=products,
        categories=VALID_CATEGORIES,
        current_category=category,
        search_query=q,
        cart_items=cart_items,
        cart_total=cart_total,
        alerts=alerts,
        flash_deals=flash_deals,
        favorite_ids=favorite_ids
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not username or not password:
            flash('用户名和密码不能为空', 'warning')
            return redirect(url_for('register'))

        if len(username) < 3:
            flash('用户名至少需要 3 个字符', 'warning')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('密码至少需要 6 个字符', 'warning')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('两次输入的密码不一致', 'warning')
            return redirect(url_for('register'))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cur.fetchone():
            flash('用户名已存在，请更换一个用户名', 'warning')
            return redirect(url_for('register'))

        try:
            cur.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), 'customer')
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash('用户名已存在，请更换一个用户名', 'warning')
            return redirect(url_for('register'))
        flash('注册成功，请使用新账号登录', 'success')
        return redirect(url_for('login'))

    alerts = get_low_stock_alerts()
    return render_template('register.html', alerts=alerts)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        next_url = get_safe_next_url()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cur.fetchone()

        if not user or not check_password_hash(user['password_hash'], password):
            flash('用户名或密码错误', 'danger')
            return redirect(url_for('login'))

        session.clear()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        flash(f'欢迎回来，{user["username"]}', 'success')
        return redirect(next_url)

    alerts = get_low_stock_alerts()
    return render_template('login.html', alerts=alerts, next=get_safe_next_url())


@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))


@app.route('/cart')
@login_required
def cart():
    current_user = get_current_user()
    cart_items = get_cart_items(current_user['id'])
    cart_total = get_cart_total(current_user['id'])
    alerts = get_low_stock_alerts()

    amount_to_free = max(0, round(FREE_SHIPPING_THRESHOLD - cart_total, 2))

    # 运费预估：满免运费门槛则免，否则预估6元（实际以结算页随机2-10元为准）
    if cart_total >= FREE_SHIPPING_THRESHOLD:
        estimated_shipping = 0
    else:
        estimated_shipping = 6.00

    estimated_total = round(cart_total + estimated_shipping, 2)

    # 凑单推荐：推荐便宜的、不在购物车里的商品
    filler_recommendations = []
    if cart_items and amount_to_free > 0:
        cart_product_ids = [item['product_id'] for item in cart_items]
        conn = get_db_connection()
        cur = conn.cursor()
        placeholders = ','.join('?' * len(cart_product_ids))
        cur.execute(
            'SELECT * FROM products WHERE is_active = 1 AND stock > 0 '
            f'AND id NOT IN ({placeholders}) '
            'ORDER BY price ASC LIMIT 4',
            cart_product_ids
        )
        filler_recommendations = [dict(row) for row in cur.fetchall()]

    return render_template(
        'cart.html',
        cart_items=cart_items,
        cart_total=cart_total,
        alerts=alerts,
        free_shipping_threshold=FREE_SHIPPING_THRESHOLD,
        amount_to_free_shipping=amount_to_free,
        estimated_shipping=estimated_shipping,
        estimated_total=estimated_total,
        filler_recommendations=filler_recommendations
    )


@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def cart_add(product_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    next_url = request.form.get('next', '').strip()
    if not next_url or not next_url.startswith('/'):
        next_url = url_for('index')

    cur.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cur.fetchone()

    add_qty_str = request.form.get('quantity', '1').strip()
    try:
        add_qty = int(add_qty_str)
    except ValueError:
        add_qty = 1
    if add_qty < 1:
        add_qty = 1

    if not product:
        flash('商品不存在', 'danger')
        return redirect(next_url)

    if product['is_active'] == 0:
        flash('商品已下架，无法购买', 'danger')
        return redirect(next_url)

    if product['stock'] <= 0:
        flash('库存不足，无法加入购物车', 'danger')
        return redirect(next_url)

    cur.execute(
        'SELECT * FROM cart_items WHERE user_id = ? AND product_id = ?',
        (current_user['id'], product_id)
    )
    existing = cur.fetchone()

    if existing:
        new_quantity = existing['quantity'] + add_qty
        if new_quantity > product['stock']:
            flash(f'库存不足，{product["name"]} 当前库存仅 {product["stock"]} 件，购物车中已有 {existing["quantity"]} 件', 'danger')
            return redirect(next_url)
        cur.execute(
            'UPDATE cart_items SET quantity = ?, updated_at = datetime(\'now\', \'localtime\') '
            'WHERE id = ?',
            (new_quantity, existing['id'])
        )
    else:
        if add_qty > product['stock']:
            flash(f'库存不足，{product["name"]} 当前库存仅 {product["stock"]} 件', 'danger')
            return redirect(next_url)
        cur.execute(
            'INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)',
            (current_user['id'], product_id, add_qty)
        )

    conn.commit()
    flash(f'已将 {product["name"]} × {add_qty} 加入购物车', 'success')
    return redirect(next_url)


@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def cart_update(item_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    quantity_str = request.form.get('quantity', '1')
    try:
        quantity = int(quantity_str)
    except ValueError:
        flash('数量无效', 'danger')
        return redirect(url_for('cart'))

    if quantity < 0:
        flash('数量不能为负数', 'danger')
        return redirect(url_for('cart'))

    cur.execute(
        'SELECT c.*, p.stock, p.name '
        'FROM cart_items c JOIN products p ON c.product_id = p.id '
        'WHERE c.id = ? AND c.user_id = ?',
        (item_id, current_user['id'])
    )
    cart_item = cur.fetchone()

    if not cart_item:
        flash('购物车记录不存在', 'danger')
        return redirect(url_for('cart'))

    if quantity == 0:
        cur.execute('DELETE FROM cart_items WHERE id = ? AND user_id = ?', (item_id, current_user['id']))
        conn.commit()
        flash(f'已从购物车移除 {cart_item["name"]}', 'info')
        return redirect(url_for('cart'))

    if quantity > cart_item['stock']:
        flash(f'库存不足，{cart_item["name"]} 当前库存仅 {cart_item["stock"]} 件', 'danger')
        return redirect(url_for('cart'))

    cur.execute(
        'UPDATE cart_items SET quantity = ?, updated_at = datetime(\'now\', \'localtime\') '
        'WHERE id = ? AND user_id = ?',
        (quantity, item_id, current_user['id'])
    )
    conn.commit()
    flash(f'已更新 {cart_item["name"]} 的数量', 'success')
    return redirect(url_for('cart'))


@app.route('/cart/delete/<int:item_id>', methods=['POST'])
@login_required
def cart_delete(item_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        'SELECT c.*, p.name '
        'FROM cart_items c JOIN products p ON c.product_id = p.id '
        'WHERE c.id = ? AND c.user_id = ?',
        (item_id, current_user['id'])
    )
    cart_item = cur.fetchone()

    if not cart_item:
        flash('购物车记录不存在', 'danger')
        return redirect(url_for('cart'))

    cur.execute('DELETE FROM cart_items WHERE id = ? AND user_id = ?', (item_id, current_user['id']))
    conn.commit()
    flash(f'已从购物车移除 {cart_item["name"]}', 'info')
    return redirect(url_for('cart'))


def generate_order_no(order_id):
    return f'ORD{order_id:012d}'


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    current_user = get_current_user()
    conn = get_db_connection()

    if request.method == 'GET':
        cart_items = get_cart_items(current_user['id'])
        if not cart_items:
            flash('购物车为空，请先添加商品', 'warning')
            return redirect(url_for('cart'))

        cart_total = get_cart_total(current_user['id'])
        cart_count = get_cart_count(current_user['id'])
        alerts = get_low_stock_alerts()

        is_employee = current_user.get('role') == 'admin'
        product_total = cart_total
        discount_amount = 0
        discounted_total = product_total
        if is_employee and product_total > 0:
            discounted_total = round(product_total * EMPLOYEE_DISCOUNT_RATE, 2)
            discount_amount = round(product_total - discounted_total, 2)

        # 运费：满免运费门槛免运费，否则随机2-10元
        if discounted_total >= FREE_SHIPPING_THRESHOLD:
            shipping_fee = 0
        else:
            shipping_fee = round(random.uniform(2, 10), 2)

        final_total = round(discounted_total + shipping_fee, 2)

        session['checkout_shipping_fee'] = shipping_fee

        return render_template(
            'checkout.html',
            cart_items=cart_items,
            cart_count=cart_count,
            product_total=product_total,
            cart_total=cart_total,
            is_employee=is_employee,
            discount_amount=discount_amount,
            discounted_total=discounted_total,
            shipping_fee=shipping_fee,
            free_shipping_threshold=FREE_SHIPPING_THRESHOLD,
            final_total=final_total,
            alerts=alerts
        )

    receiver_name = request.form.get('receiver_name', '').strip()
    receiver_phone = request.form.get('receiver_phone', '').strip()
    receiver_address = request.form.get('receiver_address', '').strip()

    if not receiver_name or not receiver_phone or not receiver_address:
        flash('请填写完整的收货信息', 'warning')
        return redirect(url_for('checkout'))

    cart_items = get_cart_items(current_user['id'])
    if not cart_items:
        flash('购物车为空，请先添加商品', 'warning')
        return redirect(url_for('cart'))

    try:
        conn.execute('BEGIN IMMEDIATE')
        cur = conn.cursor()

        for item in cart_items:
            cur.execute(
                'SELECT stock, is_active, name FROM products WHERE id = ?',
                (item['product_id'],)
            )
            product = cur.fetchone()
            if not product:
                conn.rollback()
                flash(f'商品 {item["product_name"]} 不存在', 'danger')
                return redirect(url_for('checkout'))
            if product['is_active'] == 0:
                conn.rollback()
                flash(f'商品 {product["name"]} 已下架，无法支付', 'danger')
                return redirect(url_for('checkout'))
            if product['stock'] < item['quantity']:
                conn.rollback()
                flash(f'库存不足，{item["product_name"]} 当前库存仅 {product["stock"]} 件', 'danger')
                return redirect(url_for('checkout'))

        cart_total = get_cart_total(current_user['id'])

        is_employee = current_user.get('role') == 'admin'
        product_total = cart_total
        discount_amount = 0
        discounted_total = product_total
        if is_employee and product_total > 0:
            discounted_total = round(product_total * EMPLOYEE_DISCOUNT_RATE, 2)
            discount_amount = round(product_total - discounted_total, 2)

        # 使用 session 中保存的运费（和结算页显示一致）
        shipping_fee = session.pop('checkout_shipping_fee', None)
        if shipping_fee is None:
            if discounted_total >= FREE_SHIPPING_THRESHOLD:
                shipping_fee = 0
            else:
                shipping_fee = round(random.uniform(2, 10), 2)

        final_total = round(discounted_total + shipping_fee, 2)

        cur.execute(
            'INSERT INTO orders (user_id, total_price, status, receiver_name, receiver_phone, receiver_address, original_price, discount_amount, shipping_fee) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (current_user['id'], final_total, '已付款待发货', receiver_name, receiver_phone, receiver_address, product_total, discount_amount, shipping_fee)
        )
        order_id = cur.lastrowid

        for item in cart_items:
            cur.execute(
                'INSERT INTO order_items (order_id, product_id, product_name, product_price, quantity) VALUES (?, ?, ?, ?, ?)',
                (order_id, item['product_id'], item['product_name'], item['unit_price'], item['quantity'])
            )

        for item in cart_items:
            cur.execute(
                'UPDATE products SET stock = stock - ?, updated_at = datetime(\'now\', \'localtime\') WHERE id = ?',
                (item['quantity'], item['product_id'])
            )

        cur.execute('DELETE FROM cart_items WHERE user_id = ?', (current_user['id'],))

        conn.commit()
        flash('支付成功，订单已提交', 'success')
        return redirect(url_for('order_success', order_id=order_id))

    except sqlite3.Error as e:
        conn.rollback()
        flash(f'订单创建失败：{str(e)}', 'danger')
        return redirect(url_for('checkout'))


@app.route('/order/success/<int:order_id>')
@login_required
def order_success(order_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM orders WHERE id = ? AND user_id = ?', (order_id, current_user['id']))
    order = cur.fetchone()

    if not order:
        flash('订单不存在或无权访问', 'danger')
        return redirect(url_for('orders'))

    order_dict = dict(order)
    order_dict['order_no'] = generate_order_no(order_id)

    return render_template('order_success.html', order=order_dict)


@app.route('/orders')
@login_required
def orders():
    current_user = get_current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        'SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC',
        (current_user['id'],)
    )
    order_rows = cur.fetchall()

    orders_list = []
    for order_row in order_rows:
        order_dict = dict(order_row)
        order_dict['order_no'] = generate_order_no(order_row['id'])

        cur.execute(
            'SELECT oi.*, p.image_url AS image_url, p.category AS category '
            'FROM order_items oi '
            'JOIN products p ON oi.product_id = p.id '
            'WHERE oi.order_id = ?',
            (order_row['id'],)
        )
        item_rows = cur.fetchall()

        items = []
        item_count = 0
        for item_row in item_rows:
            item_dict = dict(item_row)
            item_dict['unit_price'] = item_row['product_price']
            item_dict['subtotal'] = round(item_row['product_price'] * item_row['quantity'], 2)
            item_count += item_row['quantity']
            items.append(item_dict)

        order_dict['order_items'] = items
        order_dict['item_count'] = item_count

        cur.execute(
            'SELECT COUNT(*) AS cnt FROM reviews WHERE order_id = ?',
            (order_row['id'],)
        )
        reviewed_count = cur.fetchone()['cnt']
        order_dict['reviewed'] = reviewed_count > 0
        order_dict['review_count'] = reviewed_count
        order_dict['total_items_to_review'] = len(items)

        orders_list.append(order_dict)

    alerts = get_low_stock_alerts()
    return render_template('orders.html', orders=orders_list, alerts=alerts)


@app.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    current_user = get_current_user()
    conn = get_db_connection()

    try:
        conn.execute('BEGIN IMMEDIATE')
        cur = conn.cursor()

        cur.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        order = cur.fetchone()

        if not order:
            conn.rollback()
            flash('订单不存在', 'danger')
            return redirect(url_for('orders'))

        if order['user_id'] != current_user['id']:
            conn.rollback()
            flash('无权操作该订单', 'danger')
            return redirect(url_for('orders'))

        if order['status'] not in ('已付款待发货', '已发货'):
            conn.rollback()
            if order['status'] == '已取消':
                flash('该订单已取消，不能重复取消', 'warning')
            else:
                flash('该订单状态不允许取消', 'warning')
            return redirect(url_for('orders'))

        cur.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
        order_items = cur.fetchall()

        for item in order_items:
            cur.execute(
                'UPDATE products SET stock = stock + ?, updated_at = datetime(\'now\', \'localtime\') WHERE id = ?',
                (item['quantity'], item['product_id'])
            )

        cur.execute('UPDATE orders SET status = ? WHERE id = ?', ('已取消', order_id))

        conn.commit()
        flash('订单已取消，库存已恢复', 'success')
        return redirect(url_for('orders'))

    except sqlite3.Error as e:
        conn.rollback()
        flash(f'取消订单失败：{str(e)}', 'danger')
        return redirect(url_for('orders'))


@app.route('/orders/<int:order_id>/confirm', methods=['POST'])
@login_required
def confirm_receipt(order_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = cur.fetchone()

    if not order:
        flash('订单不存在', 'danger')
        return redirect(url_for('orders'))

    if order['user_id'] != current_user['id']:
        flash('无权操作该订单', 'danger')
        return redirect(url_for('orders'))

    if order['status'] != '已发货':
        flash('该订单状态不允许确认收货', 'warning')
        return redirect(url_for('orders'))

    cur.execute('UPDATE orders SET status = ? WHERE id = ?', ('交易完成', order_id))
    conn.commit()
    flash('已确认收货，订单交易完成！欢迎评价商品~', 'success')
    return redirect(url_for('orders'))


@app.route('/review/<int:order_id>', methods=['GET', 'POST'])
@login_required
def review_order(order_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = cur.fetchone()

    if not order:
        flash('订单不存在', 'danger')
        return redirect(url_for('orders'))

    if order['user_id'] != current_user['id']:
        flash('无权操作该订单', 'danger')
        return redirect(url_for('orders'))

    if order['status'] != '交易完成':
        flash('只有已完成的订单才能评价', 'warning')
        return redirect(url_for('orders'))

    cur.execute(
        'SELECT oi.product_id, oi.product_name, oi.product_price, oi.quantity, '
        'p.category, p.image_url, '
        '(SELECT rating FROM reviews WHERE order_id = ? AND product_id = oi.product_id) AS rated, '
        '(SELECT comment FROM reviews WHERE order_id = ? AND product_id = oi.product_id) AS rated_comment '
        'FROM order_items oi '
        'JOIN products p ON oi.product_id = p.id '
        'WHERE oi.order_id = ?',
        (order_id, order_id, order_id)
    )
    items = [dict(row) for row in cur.fetchall()]

    already_reviewed = all(item['rated'] is not None for item in items)

    if request.method == 'POST':
        if already_reviewed:
            flash('该订单所有商品已评价过', 'info')
            return redirect(url_for('orders'))

        submitted = 0
        for item in items:
            if item['rated'] is not None:
                continue
            rating = request.form.get(f'rating_{item["product_id"]}')
            comment = request.form.get(f'comment_{item["product_id"]}', '').strip()

            if not rating:
                continue

            try:
                rating_val = int(rating)
                if rating_val < 1 or rating_val > 5:
                    continue
            except (ValueError, TypeError):
                continue

            try:
                cur.execute(
                    'INSERT INTO reviews (order_id, product_id, user_id, rating, comment) '
                    'VALUES (?, ?, ?, ?, ?)',
                    (order_id, item['product_id'], current_user['id'], rating_val, comment or None)
                )
                submitted += 1
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        if submitted > 0:
            flash(f'评价提交成功，共评价 {submitted} 件商品', 'success')
        else:
            flash('未提交任何评价', 'warning')
        return redirect(url_for('orders'))

    alerts = get_low_stock_alerts()
    return render_template(
        'review.html',
        order=dict(order),
        order_no=generate_order_no(order_id),
        items=items,
        already_reviewed=already_reviewed,
        alerts=alerts
    )


# ============================================================
# 购买偏好分析面板
# ============================================================

@app.route('/preferences')
@login_required
def preferences():
    current_user = get_current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    # 获取用户所有有效订单的明细（排除已取消）
    cur.execute(
        'SELECT o.id AS order_id, o.total_price, o.created_at, '
        'oi.product_id, oi.product_name, oi.product_price, oi.quantity, '
        'p.category, p.image_url '
        'FROM orders o '
        'JOIN order_items oi ON o.id = oi.order_id '
        'JOIN products p ON oi.product_id = p.id '
        'WHERE o.user_id = ? AND o.status != "已取消" '
        'ORDER BY o.created_at DESC',
        (current_user['id'],)
    )
    purchase_rows = [dict(r) for r in cur.fetchall()]

    # 总消费（从订单表直接汇总）
    cur.execute(
        'SELECT COALESCE(SUM(total_price), 0) AS total FROM orders '
        'WHERE user_id = ? AND status != "已取消"',
        (current_user['id'],)
    )
    total_spent = round(cur.fetchone()['total'], 2)

    if not purchase_rows:
        # 无订单用户：推荐热门商品
        cur.execute(
            'SELECT * FROM products WHERE is_active = 1 ORDER BY stock DESC LIMIT 4'
        )
        recommendations = [dict(r) for r in cur.fetchall()]
        return render_template(
            'preferences.html',
            has_orders=False,
            recommendations=recommendations,
            total_orders=0,
            total_spent=0,
            total_items=0,
            category_stats=[],
            top_products=[]
        )

    # 统计订单数和商品数
    order_ids = set(r['order_id'] for r in purchase_rows)
    total_orders = len(order_ids)
    total_items = sum(r['quantity'] for r in purchase_rows)

    # 分类偏好统计
    category_stats = {}
    for r in purchase_rows:
        cat = r['category']
        if cat not in category_stats:
            category_stats[cat] = {'quantity': 0, 'spent': 0.0, 'count': 0}
        category_stats[cat]['quantity'] += r['quantity']
        category_stats[cat]['spent'] += r['product_price'] * r['quantity']
        category_stats[cat]['count'] += 1

    sorted_categories = sorted(
        category_stats.items(),
        key=lambda x: x[1]['quantity'],
        reverse=True
    )

    # 最常购买的商品 Top 5
    product_stats = {}
    for r in purchase_rows:
        pid = r['product_id']
        if pid not in product_stats:
            product_stats[pid] = {
                'id': pid,
                'name': r['product_name'],
                'category': r['category'],
                'image_url': r['image_url'],
                'total_quantity': 0,
                'purchase_count': 0,
                'total_spent': 0.0
            }
        product_stats[pid]['total_quantity'] += r['quantity']
        product_stats[pid]['purchase_count'] += 1
        product_stats[pid]['total_spent'] += r['product_price'] * r['quantity']

    top_products = sorted(
        product_stats.values(),
        key=lambda x: x['total_quantity'],
        reverse=True
    )[:5]

    # 推荐商品：偏好分类中未购买过的商品
    purchased_ids = list(product_stats.keys())
    fav_category = sorted_categories[0][0] if sorted_categories else None

    recommendations = []
    if fav_category:
        if purchased_ids:
            placeholders = ','.join('?' * len(purchased_ids))
            cur.execute(
                'SELECT * FROM products WHERE category = ? AND id NOT IN ({}) '
                'AND is_active = 1 ORDER BY stock DESC LIMIT 4'.format(placeholders),
                (fav_category, *purchased_ids)
            )
        else:
            cur.execute(
                'SELECT * FROM products WHERE category = ? AND is_active = 1 '
                'ORDER BY stock DESC LIMIT 4',
                (fav_category,)
            )
        recommendations = [dict(r) for r in cur.fetchall()]

    # 不足4个时从其他分类补充
    if len(recommendations) < 4:
        exclude_ids = set(r['id'] for r in recommendations) | set(purchased_ids)
        if exclude_ids:
            placeholders = ','.join('?' * len(exclude_ids))
            cur.execute(
                'SELECT * FROM products WHERE id NOT IN ({}) AND is_active = 1 '
                'ORDER BY stock DESC LIMIT ?'.format(placeholders),
                (*exclude_ids, 4 - len(recommendations))
            )
        else:
            cur.execute(
                'SELECT * FROM products WHERE is_active = 1 '
                'ORDER BY stock DESC LIMIT ?',
                (4 - len(recommendations),)
            )
        recommendations.extend([dict(r) for r in cur.fetchall()])

    return render_template(
        'preferences.html',
        has_orders=True,
        total_orders=total_orders,
        total_spent=total_spent,
        total_items=total_items,
        category_stats=sorted_categories,
        top_products=top_products,
        recommendations=recommendations
    )


# ============================================================
# 第 4 天：管理员商品管理后台
# ============================================================

@app.route('/admin/products')
@admin_required
def admin_products():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM products ORDER BY created_at DESC')
    products = [dict(row) for row in cur.fetchall()]
    return render_template('admin_products.html', products=products)


@app.route('/admin/products/new', methods=['GET', 'POST'])
@admin_required
def admin_product_new():
    if request.method == 'GET':
        return render_template('admin_product_form.html', product=None, mode='new')

    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    price = request.form.get('price', '').strip()
    stock = request.form.get('stock', '').strip()
    min_stock = request.form.get('min_stock', '10').strip()
    image_url = request.form.get('image_url', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash('商品名称不能为空', 'danger')
        return redirect(url_for('admin_product_new'))

    if category not in VALID_CATEGORIES:
        flash('请选择有效的商品分类', 'danger')
        return redirect(url_for('admin_product_new'))

    try:
        price_val = float(price)
        if price_val < 0:
            raise ValueError('价格不能为负数')
    except ValueError:
        flash('商品价格必须为非负数', 'danger')
        return redirect(url_for('admin_product_new'))

    try:
        stock_val = int(stock)
        if stock_val < 0:
            raise ValueError('库存不能为负数')
    except ValueError:
        flash('商品库存必须为非负整数', 'danger')
        return redirect(url_for('admin_product_new'))

    try:
        min_stock_val = int(min_stock) if min_stock else 10
        if min_stock_val < 0:
            min_stock_val = 10
    except ValueError:
        min_stock_val = 10

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO products (name, category, price, stock, min_stock, image_url, description) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (name, category, price_val, stock_val, min_stock_val, image_url or None, description or None)
    )
    conn.commit()
    flash('商品新增成功', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_product_edit(product_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cur.fetchone()

    if not product:
        flash('商品不存在', 'danger')
        return redirect(url_for('admin_products'))

    if request.method == 'GET':
        return render_template('admin_product_form.html', product=dict(product), mode='edit')

    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    price = request.form.get('price', '').strip()
    stock = request.form.get('stock', '').strip()
    min_stock = request.form.get('min_stock', '10').strip()
    image_url = request.form.get('image_url', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash('商品名称不能为空', 'danger')
        return redirect(url_for('admin_product_edit', product_id=product_id))

    if category not in VALID_CATEGORIES:
        flash('请选择有效的商品分类', 'danger')
        return redirect(url_for('admin_product_edit', product_id=product_id))

    try:
        price_val = float(price)
        if price_val < 0:
            raise ValueError('价格不能为负数')
    except ValueError:
        flash('商品价格必须为非负数', 'danger')
        return redirect(url_for('admin_product_edit', product_id=product_id))

    try:
        stock_val = int(stock)
        if stock_val < 0:
            raise ValueError('库存不能为负数')
    except ValueError:
        flash('商品库存必须为非负整数', 'danger')
        return redirect(url_for('admin_product_edit', product_id=product_id))

    try:
        min_stock_val = int(min_stock) if min_stock else 10
        if min_stock_val < 0:
            min_stock_val = 10
    except ValueError:
        min_stock_val = 10

    image_url_val = image_url
    if not image_url_val:
        image_url_val = product['image_url'] if product['image_url'] else None

    cur.execute(
        'UPDATE products SET name = ?, category = ?, price = ?, stock = ?, min_stock = ?, '
        'image_url = ?, description = ?, updated_at = datetime(\'now\', \'localtime\') WHERE id = ?',
        (name, category, price_val, stock_val, min_stock_val, image_url_val, description or None, product_id)
    )
    conn.commit()
    flash('商品更新成功', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_product_delete(product_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cur.fetchone()

    if not product:
        flash('商品不存在', 'danger')
        return redirect(url_for('admin_products'))

    cur.execute(
        'UPDATE products SET is_active = 0, updated_at = datetime(\'now\', \'localtime\') WHERE id = ?',
        (product_id,)
    )
    conn.commit()
    flash('商品已下架', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/products/<int:product_id>/activate', methods=['POST'])
@admin_required
def admin_product_activate(product_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cur.fetchone()

    if not product:
        flash('商品不存在', 'danger')
        return redirect(url_for('admin_products'))

    cur.execute(
        'UPDATE products SET is_active = 1, updated_at = datetime(\'now\', \'localtime\') WHERE id = ?',
        (product_id,)
    )
    conn.commit()
    flash('商品已上架', 'success')
    return redirect(url_for('admin_products'))


# ============================================================
# 管理员订单管理后台
# ============================================================

@app.route('/admin/orders')
@admin_required
def admin_orders():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        'SELECT o.*, u.username AS username '
        'FROM orders o '
        'JOIN users u ON o.user_id = u.id '
        'ORDER BY o.created_at DESC'
    )
    order_rows = cur.fetchall()

    orders_list = []
    for order_row in order_rows:
        order_dict = dict(order_row)
        order_dict['order_no'] = generate_order_no(order_row['id'])

        cur.execute(
            'SELECT oi.*, p.image_url AS image_url, p.category AS category '
            'FROM order_items oi '
            'JOIN products p ON oi.product_id = p.id '
            'WHERE oi.order_id = ?',
            (order_row['id'],)
        )
        item_rows = cur.fetchall()

        items = []
        for item_row in item_rows:
            item_dict = dict(item_row)
            items.append(item_dict)

        order_dict['order_items'] = items
        orders_list.append(order_dict)

    return render_template('admin_orders.html', orders=orders_list)


@app.route('/admin/orders/<int:order_id>/ship', methods=['POST'])
@admin_required
def admin_order_ship(order_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = cur.fetchone()

    if not order:
        flash('订单不存在', 'danger')
        return redirect(url_for('admin_orders'))

    if order['status'] != '已付款待发货':
        flash('该订单状态不允许发货', 'warning')
        return redirect(url_for('admin_orders'))

    cur.execute('UPDATE orders SET status = ? WHERE id = ?', ('已发货', order_id))
    conn.commit()
    flash('订单已标记为已发货', 'success')
    return redirect(url_for('admin_orders'))


@app.route('/admin/orders/<int:order_id>/close', methods=['POST'])
@admin_required
def admin_order_close(order_id):
    conn = get_db_connection()

    try:
        conn.execute('BEGIN IMMEDIATE')
        cur = conn.cursor()

        cur.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        order = cur.fetchone()

        if not order:
            conn.rollback()
            flash('订单不存在', 'danger')
            return redirect(url_for('admin_orders'))

        if order['status'] not in ('待付款', '已付款待发货'):
            conn.rollback()
            flash('该订单状态不允许关闭', 'warning')
            return redirect(url_for('admin_orders'))

        cur.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
        order_items = cur.fetchall()

        for item in order_items:
            cur.execute(
                'UPDATE products SET stock = stock + ?, updated_at = datetime(\'now\', \'localtime\') WHERE id = ?',
                (item['quantity'], item['product_id'])
            )

        cur.execute('UPDATE orders SET status = ? WHERE id = ?', ('已取消', order_id))

        conn.commit()
        flash('订单已关闭，库存已恢复', 'success')
        return redirect(url_for('admin_orders'))

    except sqlite3.Error as e:
        conn.rollback()
        flash(f'关闭订单失败：{str(e)}', 'danger')
        return redirect(url_for('admin_orders'))


# ============================================================
# 修改密码
# ============================================================

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    current_user = get_current_user()
    alerts = get_low_stock_alerts()

    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not old_password or not new_password or not confirm_password:
            flash('请填写所有密码字段', 'warning')
            return redirect(url_for('change_password'))

        if len(new_password) < 6:
            flash('新密码至少需要 6 个字符', 'warning')
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'warning')
            return redirect(url_for('change_password'))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE id = ?', (current_user['id'],))
        user = cur.fetchone()

        if not user or not check_password_hash(user['password_hash'], old_password):
            flash('原密码错误', 'danger')
            return redirect(url_for('change_password'))

        cur.execute(
            'UPDATE users SET password_hash = ?, updated_at = datetime(\'now\', \'localtime\') WHERE id = ?',
            (generate_password_hash(new_password), current_user['id'])
        )
        conn.commit()
        flash('密码修改成功', 'success')
        return redirect(url_for('change_password'))

    return render_template('change_password.html', alerts=alerts)


# ============================================================
# 商品收藏夹
# ============================================================

def get_favorite_ids(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT product_id FROM favorites WHERE user_id = ?', (user_id,))
    return [row['product_id'] for row in cur.fetchall()]


@app.route('/favorites')
@login_required
def favorites():
    current_user = get_current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        'SELECT p.* FROM products p '
        'JOIN favorites f ON p.id = f.product_id '
        'WHERE f.user_id = ? AND p.is_active = 1 '
        'ORDER BY f.created_at DESC',
        (current_user['id'],)
    )
    favorite_products = [dict(row) for row in cur.fetchall()]
    alerts = get_low_stock_alerts()

    return render_template(
        'favorites.html',
        products=favorite_products,
        favorite_ids=[p['id'] for p in favorite_products],
        alerts=alerts
    )


@app.route('/favorites/add/<int:product_id>', methods=['POST'])
@login_required
def favorites_add(product_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM products WHERE id = ? AND is_active = 1', (product_id,))
    product = cur.fetchone()
    if not product:
        flash('商品不存在', 'danger')
        return redirect(url_for('index'))

    try:
        cur.execute(
            'INSERT INTO favorites (user_id, product_id) VALUES (?, ?)',
            (current_user['id'], product_id)
        )
        conn.commit()
        flash(f'已收藏 {product["name"]}', 'success')
    except sqlite3.IntegrityError:
        flash('该商品已在收藏夹中', 'info')

    return redirect(request.referrer or url_for('index'))


@app.route('/favorites/remove/<int:product_id>', methods=['POST'])
@login_required
def favorites_remove(product_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT name FROM products WHERE id = ?', (product_id,))
    product = cur.fetchone()

    cur.execute(
        'DELETE FROM favorites WHERE user_id = ? AND product_id = ?',
        (current_user['id'], product_id)
    )
    conn.commit()

    if product:
        flash(f'已取消收藏 {product["name"]}', 'info')

    return redirect(request.referrer or url_for('favorites'))


# ============================================================
# 管理员销售统计面板
# ============================================================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cur = conn.cursor()
    alerts = get_low_stock_alerts()

    cur.execute(
        "SELECT COALESCE(SUM(total_price), 0) AS total FROM orders WHERE status != '已取消'"
    )
    total_sales = round(cur.fetchone()['total'], 2)

    cur.execute("SELECT COUNT(*) AS cnt FROM orders WHERE status != '已取消'")
    total_orders = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'customer'")
    total_users = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) AS cnt FROM products WHERE is_active = 1")
    total_products = cur.fetchone()['cnt']

    # 热销商品 Top 5
    cur.execute(
        'SELECT p.id, p.name, p.category, p.image_url, '
        'COALESCE(SUM(oi.quantity), 0) AS total_qty, '
        'COALESCE(SUM(oi.product_price * oi.quantity), 0) AS total_revenue '
        'FROM products p '
        'LEFT JOIN order_items oi ON p.id = oi.product_id '
        'LEFT JOIN orders o ON oi.order_id = o.id '
        "WHERE p.is_active = 1 AND (o.status IS NULL OR o.status != '已取消') "
        'GROUP BY p.id '
        'ORDER BY total_qty DESC '
        'LIMIT 5'
    )
    top_products = [dict(row) for row in cur.fetchall()]

    # 分类销售占比
    cur.execute(
        'SELECT p.category, '
        'COALESCE(SUM(oi.quantity), 0) AS total_qty, '
        'COALESCE(SUM(oi.product_price * oi.quantity), 0) AS total_revenue '
        'FROM products p '
        'LEFT JOIN order_items oi ON p.id = oi.product_id '
        'LEFT JOIN orders o ON oi.order_id = o.id '
        "WHERE p.is_active = 1 AND (o.status IS NULL OR o.status != '已取消') "
        'GROUP BY p.category '
        'ORDER BY total_revenue DESC'
    )
    category_stats = [dict(row) for row in cur.fetchall()]

    total_category_revenue = sum(c['total_revenue'] for c in category_stats) or 1

    # 订单状态分布
    cur.execute(
        'SELECT status, COUNT(*) AS cnt FROM orders GROUP BY status ORDER BY cnt DESC'
    )
    status_dist = [dict(row) for row in cur.fetchall()]

    return render_template(
        'admin_dashboard.html',
        total_sales=total_sales,
        total_orders=total_orders,
        total_users=total_users,
        total_products=total_products,
        top_products=top_products,
        category_stats=category_stats,
        total_category_revenue=total_category_revenue,
        status_dist=status_dist,
        alerts=alerts
    )


migrate_db()

if database_needs_init():
    from init_db import init_db
    init_db()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
