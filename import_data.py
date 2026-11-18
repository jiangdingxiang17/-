# -*- coding: utf-8 -*-
"""
在线生鲜商城 - 独立数据导入脚本（仅使用标准库）
直接执行 SQL 文件完成数据库初始化
"""
import sqlite3
import os
import hashlib
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'fresh_market.db')
SCHEMA_SQL = os.path.join(BASE_DIR, 'shared', 'database', 'ddl', 'schema.sql')
ORDER_SQL = os.path.join(BASE_DIR, 'shared', 'database', 'ddl', 'create_order_tables.sql')
SEED_SQL = os.path.join(BASE_DIR, 'shared', 'database', 'dml', 'seed_data.sql')


def simple_hash(password):
    """简单的密码哈希（替代 werkzeug）"""
    # 使用 sha256 模拟密码哈希
    salt = os.urandom(8).hex()
    h = hashlib.sha256(f'{salt}{password}'.encode()).hexdigest()
    # 生成类似 werkzeug 格式的哈希（werkzeug 使用 pbkdf2:sha256）
    import hashlib as hl
    dk = hl.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
    return f'pbkdf2:sha256:260000${salt}${dk.hex()}'


def main():
    print('=' * 60)
    print('  在线生鲜商城 - 数据导入工具')
    print('=' * 60)

    # 1. 备份
    if os.path.exists(DB_PATH):
        backup = DB_PATH + '.backup'
        shutil.copy2(DB_PATH, backup)
        print('[1/4] 已备份旧数据库')

    # 2. 读取 SQL
    print('[2/4] 读取 SQL 脚本...')
    with open(SCHEMA_SQL, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    with open(ORDER_SQL, 'r', encoding='utf-8') as f:
        order_sql = f.read()
    with open(SEED_SQL, 'r', encoding='utf-8') as f:
        seed_sql = f.read()

    # 3. 执行
    print('[3/4] 执行建表和数据导入...')
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON;')
    cur = conn.cursor()

    cur.executescript(schema_sql)
    cur.executescript(order_sql)
    cur.executescript(seed_sql)

    # 4. 创建演示账号
    print('[4/4] 创建演示账号...')
    demo_users = [
        ('user1', simple_hash('123456'), 'customer'),
        ('admin', simple_hash('admin123'), 'admin')
    ]
    cur.executemany(
        'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
        demo_users
    )
    conn.commit()

    # 5. 统计
    cur.execute('SELECT COUNT(*) FROM products')
    count = cur.fetchone()[0]
    cur.execute('SELECT category, COUNT(*) as c FROM products GROUP BY category')
    cats = cur.fetchall()
    cur.execute('SELECT COUNT(*) FROM products WHERE stock < min_stock')
    low = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM products WHERE image_url IS NOT NULL AND image_url != ''")
    img = cur.fetchone()[0]

    conn.close()

    print()
    print('=' * 60)
    print('  导入成功！')
    print(f'  商品总数: {count}')
    print(f'  图片覆盖率: {img}/{count}')
    print(f'  低库存预警: {low} 个')
    print('  分类统计:')
    for cat in cats:
        print(f'    {cat[0]}: {cat[1]} 个')
    print('=' * 60)

    # 6. 数据异常检测
    print()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    issues = []

    cur.execute('SELECT id, name, price FROM products WHERE price < 0')
    for p in cur.fetchall():
        issues.append(f'价格异常: {p["name"]}={p["price"]}')

    cur.execute('SELECT id, name, stock FROM products WHERE stock < 0')
    for p in cur.fetchall():
        issues.append(f'库存异常: {p["name"]}={p["stock"]}')

    cur.execute("SELECT id, name FROM products WHERE name IS NULL OR name = ''")
    for p in cur.fetchall():
        issues.append(f'名称为空: ID={p["id"]}')

    cur.execute("SELECT name, COUNT(*) as c FROM products GROUP BY name HAVING c > 1")
    for p in cur.fetchall():
        issues.append(f'名称重复: {p["name"]} x{p["c"]}')

    cur.execute("PRAGMA table_info(products)")
    cols = [r[1] for r in cur.fetchall()]
    if 'is_active' not in cols:
        issues.append('缺少 is_active 列')

    conn.close()

    if issues:
        print(f'[警告] 发现 {len(issues)} 个异常:')
        for i in issues:
            print(f'  - {i}')
    else:
        print('[OK] 数据完整性检查通过，无异常！')

    return True


if __name__ == '__main__':
    main()
