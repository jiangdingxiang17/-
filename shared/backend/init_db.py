import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DB_PATH = os.path.join(PROJECT_ROOT, 'fresh_market.db')
DDL_PATH = os.path.join(PROJECT_ROOT, 'shared', 'database', 'ddl', 'schema.sql')
DML_PATH = os.path.join(PROJECT_ROOT, 'shared', 'database', 'dml', 'seed_data.sql')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn


def init_db():
    print('正在初始化数据库...')
    conn = get_db_connection()
    cur = conn.cursor()

    with open(DDL_PATH, 'r', encoding='utf-8') as f:
        cur.executescript(f.read())
    print('表结构创建完成。')

    cur.execute('SELECT COUNT(*) FROM products')
    product_count = cur.fetchone()[0]

    if product_count == 0:
        with open(DML_PATH, 'r', encoding='utf-8') as f:
            cur.executescript(f.read())
        print('示例数据插入完成。')
    else:
        print(f'商品表已有 {product_count} 条数据，跳过初始化数据。')

    conn.commit()
    conn.close()
    print(f'数据库初始化完成，数据库文件路径：{DB_PATH}')


if __name__ == '__main__':
    init_db()
