import sqlite3
import os

DB_PATH = r'D:\2026暑期实训\agenticteam\fresh_market.db'


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn


def create_order_tables():
    print('正在创建订单表结构...')
    conn = get_db_connection()
    cur = conn.cursor()

    create_orders_sql = '''
    CREATE TABLE IF NOT EXISTS orders (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        total_price REAL    NOT NULL CHECK (total_price >= 0),
        status      TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'cancelled')),
        created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    '''

    create_order_items_sql = '''
    CREATE TABLE IF NOT EXISTS order_items (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id      INTEGER NOT NULL,
        product_id    INTEGER NOT NULL,
        product_name  TEXT    NOT NULL,
        product_price REAL    NOT NULL CHECK (product_price >= 0),
        quantity      INTEGER NOT NULL CHECK (quantity >= 1),
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );
    '''

    cur.execute(create_orders_sql)
    print('orders 表创建完成。')

    cur.execute(create_order_items_sql)
    print('order_items 表创建完成。')

    conn.commit()
    conn.close()
    print(f'订单表结构创建完成，数据库文件路径：{DB_PATH}')


def verify_tables():
    print('\n验证表结构：')
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('orders', 'order_items')")
    tables = cur.fetchall()
    table_names = [t[0] for t in tables]

    if 'orders' in table_names:
        print('✓ orders 表已存在')
        cur.execute("PRAGMA table_info(orders)")
        columns = cur.fetchall()
        print('  字段列表：')
        for col in columns:
            print(f'    - {col[1]} ({col[2]})')
    else:
        print('✗ orders 表不存在')

    if 'order_items' in table_names:
        print('✓ order_items 表已存在')
        cur.execute("PRAGMA table_info(order_items)")
        columns = cur.fetchall()
        print('  字段列表：')
        for col in columns:
            print(f'    - {col[1]} ({col[2]})')
    else:
        print('✗ order_items 表不存在')

    conn.close()


if __name__ == '__main__':
    create_order_tables()
    verify_tables()