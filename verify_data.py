#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===========================================================
  生鲜商城 - 数据验证脚本
===========================================================
功能：检查数据库记录与图片文件的完整性
===========================================================
"""

import os, sys, sqlite3, random

# 配置
PROJECT_ROOT = r"D:\2026暑期实训\agenticteam"
DB_PATH = os.path.join(PROJECT_ROOT, "fresh_market.db")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "shared", "backend", "uploads", "products")
STATIC_IMG_DIR = os.path.join(PROJECT_ROOT, "shared", "backend", "static", "images", "products")
BASE_URL = "http://127.0.0.1:5000"

print("=" * 60)
print("  生鲜商城 - 数据验证报告")
print("=" * 60)

# --- 1. 数据库 vs 图片文件 ---
print("\n[1] 数据库记录数 vs 图片文件数")
print("-" * 40)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM products")
db_count = cur.fetchone()[0]
print(f"  数据库 products 表记录数: {db_count}")

# Upload dir
if os.path.exists(UPLOAD_DIR):
    upload_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".jpg")]
    print(f"  /uploads/products/ 图片文件数: {len(upload_files)}")
else:
    upload_files = []
    print(f"  /uploads/products/ 目录不存在!")

# Static dir
if os.path.exists(STATIC_IMG_DIR):
    static_files = [f for f in os.listdir(STATIC_IMG_DIR) if f.endswith(".jpg")]
    print(f"  /static/images/products/ 图片文件数: {len(static_files)}")
else:
    static_files = []
    print(f"  /static/images/products/ 目录不存在!")

# Check match
if db_count == len(upload_files):
    print(f"  [OK] 数据库记录数与上传图片数一致: {db_count}")
else:
    print(f"  [WARN] 不一致! 数据库={db_count}, 图片={len(upload_files)}")

# --- 2. 随机抽查3个商品的完整路径 ---
print("\n[2] 随机抽查商品路径可访问性")
print("-" * 40)

cur.execute("SELECT id, name, category, image_url FROM products ORDER BY id")
all_products = cur.fetchall()
conn.close()

if len(all_products) >= 3:
    samples = random.sample(list(all_products), 3)
else:
    samples = list(all_products)

for prod in samples:
    pid = prod["id"]
    name = prod["name"]
    category = prod["category"]
    img_url = prod["image_url"]
    
    # Extract filename from image_url
    fname = os.path.basename(img_url)
    local_path = os.path.join(UPLOAD_DIR, fname)
    
    exists = os.path.exists(local_path)
    size = os.path.getsize(local_path) if exists else 0
    
    print(f"  [{pid:2d}] {name:10s} ({category})")
    print(f"        DB路径: {img_url}")
    print(f"        本地文件: {local_path}")
    print(f"        文件存在: {'YES' if exists else 'NO'}")
    if exists:
        print(f"        文件大小: {size // 1024} KB")
    print(f"        完整URL: {BASE_URL}{img_url}")
    print()

# --- 3. 商品分类分布 ---
print("\n[3] 商品分类分布")
print("-" * 40)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT category, COUNT(*) as cnt FROM products GROUP BY category ORDER BY category")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} 个")

# Low stock items
cur.execute("SELECT name, category, stock, min_stock FROM products WHERE stock < min_stock")
low = cur.fetchall()
print(f"\n[4] 低库存预警 (共 {len(low)} 个)")
for r in low:
    print(f"  {r[0]} ({r[1]}) - stock {r[2]} < min {r[3]}")

# Backup table
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bak_product_images'")
if cur.fetchone():
    cur.execute("SELECT COUNT(*) FROM bak_product_images")
    bak_count = cur.fetchone()[0]
    print(f"\n[5] 备份表 bak_product_images: {bak_count} 条记录")
else:
    print("\n[5] 备份表 bak_product_images: 不存在")

conn.close()

# --- 4. 当前前端实际使用的图片URL ---
print("\n[6] 前端实际图片URL示例")
print("-" * 40)
print(f"  DB中存储格式: /uploads/products/product_{{id}}.jpg")
print(f"  实际请求URL: {BASE_URL}/uploads/products/product_1.jpg")
print(f"  Flask路由: @app.route('/uploads/<path:filename>')")
print(f"  静态文件夹: shared/backend/uploads/")
print(f"  说明: Flask 的 static_folder 仍指向 shared/backend/static/")
print(f"        /uploads/ 由独立路由处理, 不影响已有 /static/ 路径")

print("\n" + "=" * 60)
print("  验证完毕")
print("=" * 60)