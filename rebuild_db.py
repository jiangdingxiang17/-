#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生鲜商城 - 数据库重建脚本
功能：
  1. 备份当前数据库
  2. 删除并重建所有表（含 CHECK 约束）
  3. 插入 50 个商品（蔬菜/水果/肉类/鱼类），使用 static/images/products/ 中的正确图片
  4. 创建演示用户 user1/123456 和 admin/admin123
  5. 创建订单相关表
"""

import os
import shutil
import sqlite3
from werkzeug.security import generate_password_hash

PROJECT_ROOT = r'd:\2026暑期实训1\2026暑期实训\agenticteam'
DB_PATH = os.path.join(PROJECT_ROOT, 'fresh_market.db')
BACKUP_PATH = os.path.join(PROJECT_ROOT, 'fresh_market.db.bak')

# ============================================================
# 商品数据：50 个商品，使用 static/images/products/ 中的正确图片
# 分类只使用 VALID_CATEGORIES: 蔬菜、水果、肉类、鱼类
# 包含部分低库存商品用于演示预警
# ============================================================
PRODUCTS = [
    # === 蔬菜 (12) ===
    ('大白菜',       '蔬菜', 2.50, 60, 15, '/static/images/products/napa-cabbage.jpg',      '本地大白菜，清甜爽口，适合炖煮'),
    ('菠菜',         '蔬菜', 5.20,  5, 10, '/static/images/products/spinach.jpg',           '叶片肥厚翠绿菠菜，富含铁元素（低库存）'),
    ('西红柿',       '蔬菜', 6.80, 30, 10, '/static/images/products/tomato.jpg',            '新鲜红润西红柿，酸甜适中，适合家常烹饪'),
    ('黄瓜',         '蔬菜', 4.50, 35, 10, '/static/images/products/cucumber.jpg',          '脆嫩多汁黄瓜，清凉爽口，可生食可凉拌'),
    ('土豆',         '蔬菜', 3.20, 50, 15, '/static/images/products/potato.jpg',            '黄心土豆，淀粉含量高，耐储存'),
    ('西兰花',       '蔬菜', 8.80, 22,  8, '/static/images/products/broccoli.jpg',          '翠绿紧实西兰花，富含膳食纤维'),
    ('生菜',         '蔬菜', 4.80, 30, 10, '/static/images/products/lettuce.jpg',           '新鲜脆嫩生菜，适合沙拉和汉堡'),
    ('茄子',         '蔬菜', 4.60, 25, 10, '/static/images/products/eggplant.jpg',          '紫长茄子，肉质细嫩，适合红烧'),
    ('洋葱',         '蔬菜', 3.00, 55, 10, '/static/images/products/onion.jpg',             '紫皮洋葱，辛辣适中，可生食可炒菜'),
    ('山药',         '蔬菜', 9.80, 18,  8, '/static/images/products/chinese-yam.jpg',       '铁棍山药，粉糯香甜，滋补佳品'),
    ('南瓜',         '蔬菜', 3.80, 30, 10, '/static/images/products/pumpkin.jpg',           '老南瓜，香甜粉糯，适合煲汤煮粥'),
    ('胡萝卜',       '蔬菜', 3.90, 40, 10, '/static/images/products/carrot.jpg',            '新鲜胡萝卜，富含胡萝卜素，营养丰富'),

    # === 水果 (12) ===
    ('红富士苹果',   '水果', 9.90, 40, 10, '/static/images/products/fuji-apple.jpg',        '陕西红富士，脆甜爽口，果香浓郁'),
    ('香蕉',         '水果', 5.80, 35, 10, '/static/images/products/banana.jpg',            '海南香蕉，软糯香甜，老少皆宜'),
    ('丹东草莓',     '水果', 35.00, 6, 10, '/static/images/products/strawberry.jpg',        '丹东99草莓，色泽鲜艳，酸甜可口（低库存）'),
    ('海南芒果',     '水果', 12.80, 25,  8, '/static/images/products/mango.jpg',            '海南贵妃芒，果肉金黄，甜度高'),
    ('麒麟西瓜',     '水果', 4.50, 15,  8, '/static/images/products/watermelon.jpg',        '麒麟西瓜，皮薄瓤红，消暑解渴'),
    ('赣南脐橙',     '水果', 8.90, 30, 10, '/static/images/products/navel-orange.jpg',      '赣南脐橙，汁多味甜，维C丰富'),
    ('阳光玫瑰葡萄', '水果', 28.80, 8, 12, '/static/images/products/shine-muscat-grapes.jpg','无核脆甜，浓郁玫瑰香，果粒紧实（低库存）'),
    ('徐香猕猴桃',   '水果', 6.50, 25, 10, '/static/images/products/kiwifruit.jpg',         '徐香猕猴桃，果肉翠绿，甜酸可口'),
    ('水蜜桃',       '水果', 15.00, 20,  8, '/static/images/products/peach.jpg',            '阳山水蜜桃，皮薄汁多，入口即化'),
    ('智利车厘子',   '水果', 58.00, 5, 10, '/static/images/products/cherry.jpg',            '智利进口车厘子，深红饱满，脆甜多汁（低库存）'),
    ('柠檬',         '水果', 5.50, 30, 10, '/static/images/products/lemon.jpg',             '新鲜柠檬，酸爽清香，泡水烹饪皆宜'),
    ('秘鲁蓝莓',     '水果', 25.00, 15,  8, '/static/images/products/blueberry.jpg',        '秘鲁蓝莓，果粒饱满，花青素丰富'),

    # === 肉类 (14) ===
    ('黑猪五花肉',   '肉类', 39.90, 18,  8, '/static/images/products/pork-belly.jpg',       '散养黑猪五花，肥瘦相间，纹理清晰'),
    ('散养土鸡',     '肉类', 58.00, 12,  8, '/static/images/products/whole-chicken.jpg',    '林下散养土鸡，肉质紧实，鲜香浓郁'),
    ('安格斯牛排',   '肉类', 88.00, 3,  8, '/static/images/products/beef-steak.jpg',       '进口安格斯肉眼牛排，雪花纹理丰富（低库存）'),
    ('猪里脊肉',     '肉类', 22.00, 25, 10, '/static/images/products/pork-tenderloin.jpg',  '猪里脊肉，肉质嫩滑，适合爆炒'),
    ('澳洲牛腩',     '肉类', 48.00, 15,  8, '/static/images/products/beef-brisket.jpg',     '澳洲进口牛腩，肥瘦适中，适合炖煮'),
    ('鸡胸肉',       '肉类', 16.00, 30, 10, '/static/images/products/chicken-breast.jpg',   '新鲜鸡胸肉，低脂高蛋白，健身首选'),
    ('猪小排',       '肉类', 35.00, 20, 10, '/static/images/products/pork-ribs.jpg',        '猪小排，肉质鲜嫩，适合糖醋红烧'),
    ('羊腿肉',       '肉类', 55.00, 12,  8, '/static/images/products/lamb-leg.jpg',         '草原羊腿肉，肉质细嫩，膻味轻'),
    ('鸡翅中',       '肉类', 25.00, 20, 10, '/static/images/products/chicken-wings.jpg',    '鲜嫩鸡翅中，肉质饱满，适合烤制'),
    ('金华火腿',     '肉类', 68.00,  8,  8, '/static/images/products/cured-ham.jpg',        '金华火腿，色泽红润，鲜香味美'),
    ('乌鸡',         '肉类', 42.00, 10,  8, '/static/images/products/silkie-chicken.jpg',   '乌鸡，黑色肉质，滋补养颜'),
    ('牛里脊',       '肉类', 78.00,  8, 10, '/static/images/products/beef-tenderloin.jpg',  '牛里脊，肉质最嫩部位，适合煎炒（低库存）'),
    ('乳鸽',         '肉类', 48.00, 10,  8, '/static/images/products/pigeon.jpg',           '乳鸽，肉质细嫩，适合炖汤红烧'),
    ('肥牛卷',       '肉类', 38.00, 20, 10, '/static/images/products/beef-roll.jpg',        '肥牛卷，红白相间，火锅必备'),

    # === 鱼类 (12) ===
    ('活鲫鱼',       '鱼类', 15.00, 22, 10, '/static/images/products/crucian-carp.jpg',     '水库活体鲫鱼，鲜活配送，适合煲汤'),
    ('三文鱼刺身',   '鱼类', 68.00, 6, 10, '/static/images/products/salmon.jpg',           '挪威进口三文鱼，冰鲜直供（低库存）'),
    ('北极甜虾',     '鱼类', 45.00, 28, 10, '/static/images/products/shrimp.jpg',           '北极冷水甜虾，肉质紧实甘甜'),
    ('东海带鱼',     '鱼类', 22.00, 18, 10, '/static/images/products/hairtail-fish.jpg',    '东海带鱼，银白光亮，肉质细嫩'),
    ('黄花鱼',       '鱼类', 32.00, 15, 10, '/static/images/products/yellow-croaker.jpg',   '大黄花鱼，色泽金黄，蒜瓣肉质'),
    ('海鲈鱼',       '鱼类', 35.00, 18,  8, '/static/images/products/sea-bass.jpg',         '海鲈鱼，肉质洁白紧实，清蒸鲜美'),
    ('基围虾',       '鱼类', 55.00, 20, 10, '/static/images/products/jumbo-shrimp.jpg',     '鲜活基围虾，壳薄肉厚，鲜甜弹牙'),
    ('乳山生蚝',     '鱼类',  8.00, 40, 15, '/static/images/products/oyster.jpg',           '乳山鲜活生蚝，肥美多汁'),
    ('花蛤',         '鱼类',  6.00, 50, 15, '/static/images/products/clams.jpg',            '鲜活花蛤，肉质鲜嫩，辣炒清蒸皆宜'),
    ('鱿鱼',         '鱼类', 18.00, 25, 10, '/static/images/products/squid.jpg',            '新鲜鱿鱼，肉质Q弹，适合烧烤爆炒'),
    ('扇贝',         '鱼类', 28.00, 20, 10, '/static/images/products/scallop.jpg',          '鲜活扇贝，贝柱饱满，蒜蓉粉丝蒸'),
    ('金鲳鱼',       '鱼类', 25.00, 20, 10, '/static/images/products/pomfret.jpg',          '金鲳鱼，肉质肥厚鲜嫩，适合清蒸'),
]


def rebuild_database():
    # 步骤 1: 备份当前数据库
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f'[备份] 已备份当前数据库到 {BACKUP_PATH}')
    else:
        print('[备份] 数据库不存在，无需备份')

    # 步骤 2: 删除旧数据库，从头创建
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print('[清理] 已删除旧数据库')

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON;')
    cur = conn.cursor()

    # 步骤 3: 创建所有表（含 CHECK 约束）
    print('[建表] 创建表结构...')

    # 用户表
    cur.execute('''
        CREATE TABLE users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'admin')),
            created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    cur.execute('CREATE INDEX idx_users_username ON users(username)')

    # 商品表（含分类 CHECK 约束）
    cur.execute('''
        CREATE TABLE products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            category    TEXT    NOT NULL CHECK (category IN ('蔬菜', '水果', '肉类', '鱼类')),
            price       REAL    NOT NULL CHECK (price >= 0),
            stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
            min_stock   INTEGER NOT NULL DEFAULT 10 CHECK (min_stock >= 0),
            image_url   TEXT,
            description TEXT,
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    cur.execute('CREATE INDEX idx_products_category ON products(category)')

    # 购物车表
    cur.execute('''
        CREATE TABLE cart_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1),
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            UNIQUE(user_id, product_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    cur.execute('CREATE INDEX idx_cart_items_user_id ON cart_items(user_id)')
    cur.execute('CREATE INDEX idx_cart_items_product_id ON cart_items(product_id)')

    # 订单表（含收货信息字段 + 中文状态约束）
    cur.execute('''
        CREATE TABLE orders (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            total_price      REAL    NOT NULL CHECK (total_price >= 0),
            status           TEXT    NOT NULL DEFAULT '已付款待发货'
                                     CHECK (status IN ('待付款', '已付款待发货', '已发货', '交易完成', '已取消')),
            receiver_name    TEXT,
            receiver_phone   TEXT,
            receiver_address TEXT,
            created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    cur.execute('CREATE INDEX idx_orders_user_id ON orders(user_id)')
    cur.execute('CREATE INDEX idx_orders_status ON orders(status)')

    # 订单明细表
    cur.execute('''
        CREATE TABLE order_items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id      INTEGER NOT NULL,
            product_id    INTEGER NOT NULL,
            product_name  TEXT    NOT NULL,
            product_price REAL    NOT NULL CHECK (product_price >= 0),
            quantity      INTEGER NOT NULL CHECK (quantity >= 1),
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    cur.execute('CREATE INDEX idx_order_items_order_id ON order_items(order_id)')
    cur.execute('CREATE INDEX idx_order_items_product_id ON order_items(product_id)')

    print('[建表] 所有表创建完成')

    # 步骤 4: 插入商品数据
    print(f'[数据] 插入 {len(PRODUCTS)} 个商品...')
    cur.executemany(
        'INSERT INTO products (name, category, price, stock, min_stock, image_url, description) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        PRODUCTS
    )
    print(f'[数据] 商品插入完成: {cur.rowcount} 条')

    # 步骤 5: 创建演示用户
    print('[数据] 创建演示用户...')
    demo_users = [
        ('user1', generate_password_hash('123456'), 'customer'),
        ('admin', generate_password_hash('admin123'), 'admin'),
    ]
    cur.executemany(
        'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
        demo_users
    )
    print(f'[数据] 用户创建完成: user1/123456 (普通用户), admin/admin123 (管理员)')

    # 商品图片：使用 emoji 占位符（模板内置分类图标），image_url 设为 NULL
    # 如需启用图片，将正确的图片放入 static/images/products/ 目录并更新 image_url 字段
    cur.execute('UPDATE products SET image_url = NULL')
    print(f'[数据] 商品图片设为 emoji 占位符模式')

    conn.commit()
    conn.close()

    # 步骤 6: 验证
    print('\n[验证] 检查重建结果...')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM products')
    print(f'  商品总数: {cur.fetchone()[0]}')

    cur.execute('SELECT category, COUNT(*) FROM products GROUP BY category')
    for row in cur.fetchall():
        print(f'    {row[0]}: {row[1]} 个')

    cur.execute('SELECT COUNT(*) FROM users')
    print(f'  用户总数: {cur.fetchone()[0]}')
    cur.execute('SELECT id, username, role FROM users')
    for row in cur.fetchall():
        print(f'    用户 {row[0]}: {row[1]} ({row[2]})')

    cur.execute('SELECT COUNT(*) FROM products WHERE image_url IS NOT NULL')
    print(f'  有图片的商品: {cur.fetchone()[0]}')

    cur.execute('SELECT COUNT(*) FROM products WHERE stock < min_stock')
    print(f'  低库存商品: {cur.fetchone()[0]}')

    cur.execute('SELECT id, name, stock, min_stock FROM products WHERE stock < min_stock')
    for row in cur.fetchall():
        print(f'    {row[1]}: 库存 {row[2]} < 预警线 {row[3]}')

    # 验证商品图片模式（emoji 占位符模式：image_url 为 NULL）
    cur.execute('SELECT COUNT(*) FROM products WHERE image_url IS NOT NULL')
    has_image = cur.fetchone()[0]
    if has_image == 0:
        print(f'  商品图片: emoji 占位符模式（image_url 全部为 NULL，模板按分类显示图标）')
    else:
        print(f'  商品图片: {has_image} 个商品使用图片 URL')

    conn.close()
    print(f'\n[完成] 数据库重建成功！路径: {DB_PATH}')


if __name__ == '__main__':
    rebuild_database()
