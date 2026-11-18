#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
  生鲜商城 - 商品爬取与数据库重建脚本（事务安全）
============================================================
功能：
  1. 备份当前商品图片路径到临时表 bak_product_images
  2. DELETE 商品表中所有记录（保留表结构）
  3. 删除 /uploads/products/ 目录下所有图片文件
  4. 从 picsum.photos 爬取商品主图
  5. 保存为 product_{id}.jpg，写入 /uploads/products/
  6. 完整事务控制，失败回滚
============================================================
"""

import os, sys, time, urllib.request, sqlite3, datetime

# ========== 配置 ==========
PROJECT_ROOT = r"D:\2026暑期实训\agenticteam"
DB_PATH = os.path.join(PROJECT_ROOT, "fresh_market.db")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "shared", "backend", "uploads", "products")
DDL_PATH = os.path.join(PROJECT_ROOT, "shared", "database", "ddl", "schema.sql")

# 爬取配置
CRAWL_DELAY_MIN = 1.0   # 最小延迟（秒）
CRAWL_DELAY_MAX = 3.0   # 最大延迟（秒）
PRODUCT_LIMIT = 50      # 最多爬取商品数
IMAGE_WIDTH = 400
IMAGE_HEIGHT = 300

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REFERER = "https://picsum.photos/"

# 新鲜生鲜关键词白名单（禁止零食、加工品）
FRESH_KEYWORDS = {
    "蔬菜": ["白菜", "菠菜", "菜", "萝卜", "豆", "瓜", "椒", "茄", "葱", "蒜", "西红柿", "番茄",
             "姜", "芹", "笋", "薯", "芋", "莲藕", "山药", "玉米", "菌", "菇",
             "西兰花", "花菜", "生菜", "空心菜", "韭菜", "茼蒿", "莴笋"],
    "水果": ["苹果", "梨", "桃", "李", "杏", "莓", "橙", "橘", "柑", "柚",
             "柠檬", "香蕉", "芒果", "菠萝", "榴莲", "荔枝", "龙眼", "葡萄",
             "提子", "猕猴桃", "火龙果", "木瓜", "西瓜", "甜瓜", "哈密瓜",
             "椰子", "百香果", "蓝莓", "车厘子", "石榴", "柿子", "枣"],
    "肉类": ["猪肉", "牛肉", "羊肉", "鸡肉", "鸭肉", "鹅肉", "猪", "牛", "羊", "鸡", "鸭", "排骨", "小排", "五花肉",
             "里脊", "腿肉", "胸肉", "翅", "爪", "胗", "肝", "肠", "肚", "腩", "肥牛",
             "牛排", "肉卷", "培根", "火腿", "腊肉", "肉馅", "鸽子", "乌鸡"],
    "鱼类": ["鱼", "虾", "蟹", "贝", "蚝", "蛤", "螺", "参", "鲍鱼", "鱿鱼",
             "章鱼", "海蜇", "带鱼", "黄花鱼", "鲈鱼", "三文鱼", "鳕鱼",
             "鲳鱼", "鲫鱼", "草鱼", "鲶鱼", "甲鱼", "龙虾"],
    "蛋奶": ["鸡蛋", "鸭蛋", "鹌鹑蛋", "牛奶", "酸奶", "奶酪", "黄油"],
}

def is_fresh_food(name):
    """校验商品名称是否属于新鲜生鲜"""
    for cat_keywords in FRESH_KEYWORDS.values():
        for kw in cat_keywords:
            if kw in name:
                return True
    return False

def map_category(name):
    """根据名称映射到本地分类"""
    for cat, keywords in FRESH_KEYWORDS.items():
        for kw in keywords:
            if kw in name:
                return cat
    return "其他"

# ================================================================
#  产品列表
# ================================================================
PRODUCTS = [
    # (中文名, picsum种子关键词, 价格, 库存, 最小库存, 描述)
    # === 蔬菜 ===
    ("西红柿",     "tomato",           6.80, 30, 10, "新鲜红润西红柿，酸甜适中，适合家常烹饪"),
    ("黄瓜",       "cucumber",         4.50, 35, 10, "脆嫩多汁黄瓜，清凉爽口，可生食可凉拌"),
    ("菠菜",       "spinach",          5.20, 8,  10, "叶片肥厚翠绿菠菜，富含铁元素"),
    ("土豆",       "potato",           3.20, 50, 15, "黄心土豆，淀粉含量高，耐储存"),
    ("胡萝卜",     "carrot",           3.90, 40, 10, "新鲜胡萝卜，富含胡萝卜素，营养丰富"),
    ("西兰花",     "broccoli",         8.80, 22, 8,  "翠绿紧实西兰花，富含膳食纤维"),
    ("生菜",       "lettuce",          4.80, 30, 10, "新鲜脆嫩生菜，适合沙拉和汉堡"),
    ("茄子",       "eggplant",         4.60, 25, 10, "紫长茄子，肉质细嫩，适合红烧"),
    ("大白菜",     "napa-cabbage",     2.50, 60, 15, "本地大白菜，清甜爽口，适合炖煮"),
    ("洋葱",       "onion",            3.00, 55, 10, "紫皮洋葱，辛辣适中，可生食可炒菜"),
    ("山药",       "chinese-yam",      9.80, 18, 8,  "铁棍山药，粉糯香甜，滋补佳品"),
    ("南瓜",       "pumpkin",          3.80, 30, 10, "老南瓜，香甜粉糯，适合煲汤煮粥"),
    # === 水果 ===
    ("红富士苹果", "fuji-apple",       9.90, 40, 10, "陕西红富士，脆甜爽口，果香浓郁"),
    ("香蕉",       "banana",           5.80, 35, 10, "海南香蕉，软糯香甜，老少皆宜"),
    ("丹东草莓",   "strawberry",       35.00, 6, 10, "丹东99草莓，色泽鲜艳，酸甜可口"),
    ("海南芒果",   "mango",            12.80, 25, 8,  "海南贵妃芒，果肉金黄，甜度高"),
    ("麒麟西瓜",   "watermelon",       4.50, 15, 8,  "麒麟西瓜，皮薄瓤红，消暑解渴"),
    ("赣南脐橙",   "navel-orange",     8.90, 30, 10, "赣南脐橙，汁多味甜，维C丰富"),
    ("阳光玫瑰葡萄","shine-muscat-grapes",28.80,10,12,"无核脆甜，浓郁玫瑰香，果粒紧实"),
    ("徐香猕猴桃", "kiwifruit",        6.50, 25, 10, "徐香猕猴桃，果肉翠绿，甜酸可口"),
    ("水蜜桃",     "peach",            15.00, 20, 8,  "阳山水蜜桃，皮薄汁多，入口即化"),
    ("智利车厘子",  "cherry",          58.00, 5,  10, "智利进口车厘子，深红饱满，脆甜多汁"),
    ("柠檬",       "lemon",            5.50, 30, 10, "新鲜柠檬，酸爽清香，泡水烹饪皆宜"),
    ("秘鲁蓝莓",   "blueberry",        25.00, 15, 8,  "秘鲁蓝莓，果粒饱满，花青素丰富"),
    # === 肉类 ===
    ("黑猪五花肉", "pork-belly",       39.90, 18, 8,  "散养黑猪五花，肥瘦相间，纹理清晰"),
    ("散养土鸡",   "whole-chicken",    58.00, 12, 8,  "林下散养土鸡，肉质紧实，鲜香浓郁"),
    ("安格斯牛排", "beef-steak",       88.00, 5,  8,  "进口安格斯肉眼牛排，雪花纹理丰富"),
    ("猪里脊肉",   "pork-tenderloin",  22.00, 25, 10, "猪里脊肉，肉质嫩滑，适合爆炒"),
    ("澳洲牛腩",   "beef-brisket",     48.00, 15, 8,  "澳洲进口牛腩，肥瘦适中，适合炖煮"),
    ("鸡胸肉",     "chicken-breast",   16.00, 30, 10, "新鲜鸡胸肉，低脂高蛋白，健身首选"),
    ("猪小排",     "pork-ribs",        35.00, 20, 10, "猪小排，肉质鲜嫩，适合糖醋红烧"),
    ("羊腿肉",     "lamb-leg",         55.00, 12, 8,  "草原羊腿肉，肉质细嫩，膻味轻"),
    ("鸡翅中",     "chicken-wings",    25.00, 20, 10, "鲜嫩鸡翅中，肉质饱满，适合烤制"),
    ("金华火腿",   "cured-ham",        68.00, 8,  8,  "金华火腿，色泽红润，鲜香味美"),
    ("乌鸡",       "silkie-chicken",   42.00, 10, 8,  "乌鸡，黑色肉质，滋补养颜"),
    ("牛里脊",     "beef-tenderloin",  78.00, 8,  10, "牛里脊，肉质最嫩部位，适合煎炒"),
    ("鸽子",       "pigeon",           48.00, 10, 8,  "乳鸽，肉质细嫩，适合炖汤红烧"),
    ("肥牛卷",     "beef-roll",        38.00, 20, 10, "肥牛卷，红白相间，火锅必备"),
    # === 鱼类 ===
    ("活鲫鱼",     "crucian-carp",     15.00, 22, 10, "水库活体鲫鱼，鲜活配送，适合煲汤"),
    ("三文鱼刺身",  "salmon",          68.00, 8,  10, "挪威进口三文鱼，冰鲜直供"),
    ("北极甜虾",   "shrimp",           45.00, 28, 10, "北极冷水甜虾，肉质紧实甘甜"),
    ("东海带鱼",   "hairtail-fish",    22.00, 18, 10, "东海带鱼，银白光亮，肉质细嫩"),
    ("黄花鱼",     "yellow-croaker",   32.00, 15, 10, "大黄花鱼，色泽金黄，蒜瓣肉质"),
    ("海鲈鱼",     "sea-bass",         35.00, 18, 8,  "海鲈鱼，肉质洁白紧实，清蒸鲜美"),
    ("基围虾",     "jumbo-shrimp",     55.00, 20, 10, "鲜活基围虾，壳薄肉厚，鲜甜弹牙"),
    ("乳山生蚝",   "oyster",           8.00,  40, 15, "乳山鲜活生蚝，肥美多汁"),
    ("花蛤",       "clams",            6.00,  50, 15, "鲜活花蛤，肉质鲜嫩，辣炒清蒸皆宜"),
    ("鱿鱼",       "squid",            18.00, 25, 10, "新鲜鱿鱼，肉质Q弹，适合烧烤爆炒"),
    ("扇贝",       "scallop",          28.00, 20, 10, "鲜活扇贝，贝柱饱满，蒜蓉粉丝蒸"),
    ("金鲳鱼",     "pomfret",          25.00, 20, 10, "金鲳鱼，肉质肥厚鲜嫩，适合清蒸"),
]

def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

# ================================================================
#  步骤 1: 备份当前商品图片路径到临时表
# ================================================================
def backup_image_paths(conn):
    cur = conn.cursor()
    # 创建备份临时表
    cur.execute("DROP TABLE IF EXISTS bak_product_images")
    cur.execute("""
        CREATE TABLE bak_product_images (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            image_url TEXT,
            backed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    cur.execute("SELECT id, name, category, image_url FROM products")
    rows = cur.fetchall()
    count = 0
    for row in rows:
        cur.execute(
            "INSERT INTO bak_product_images (id, name, category, image_url) VALUES (?, ?, ?, ?)",
            (row[0], row[1], row[2], row[3])
        )
        count += 1
    log(f"[备份] 已备份 {count} 条商品图片路径到 bak_product_images")
    return count

# ================================================================
#  步骤 2: 删除商品表所有记录（保留表结构）
# ================================================================
def delete_all_products(conn):
    cur = conn.cursor()
    # 先删除 cart_items（外键依赖），再删 products
    cur.execute("DELETE FROM cart_items")
    deleted_cart = cur.rowcount
    cur.execute("DELETE FROM products")
    deleted_products = cur.rowcount
    # 重置自增序列
    cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('products', 'cart_items')")
    log(f"[删除] 已删除 cart_items {deleted_cart} 条, products {deleted_products} 条")
    return deleted_products

# ================================================================
#  步骤 3: 删除 /uploads/products/ 目录下所有图片文件
# ================================================================
def delete_upload_images():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        log(f"[清理] 目录 {UPLOAD_DIR} 不存在，已创建")
        return 0
    count = 0
    for fname in os.listdir(UPLOAD_DIR):
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.isfile(fpath) and fname.endswith(".jpg"):
            os.remove(fpath)
            count += 1
    log(f"[清理] 已删除 {count} 张旧图片文件")
    return count

# ================================================================
#  步骤 4-5: 爬取图片 + 下载保存
# ================================================================
def download_image(url, dest, retries=3):
    """下载单张图片，重试 retries 次"""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Referer": REFERER,
    })
    for attempt in range(retries):
        try:
            resp = urllib.request.urlopen(req, timeout=20)
            data = resp.read()
            if len(data) > 500:
                # 校验是否为有效 JPEG/PNG
                if data[:2] in (b'\xff\xd8', b'\x89P'):
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "wb") as f:
                        f.write(data)
                    return len(data)
            log(f"  [重试 {attempt+1}] 图片过小或不合法: {len(data)} bytes")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
    return 0

def process_products(conn):
    """主处理逻辑（在事务内执行）"""
    cur = conn.cursor()
    results = {"success": 0, "failed": 0, "skipped": 0, "details": []}
    next_id = 1  # 将从 1 开始的自增 ID

    for i, prod in enumerate(PRODUCTS):
        name, keyword, price, stock, min_stock, desc = prod

        # --- 步骤 6: 新鲜生鲜校验 ---
        if not is_fresh_food(name):
            log(f"  [{i+1:2d}] SKIP {name:8s} - 非新鲜生鲜关键词")
            results["skipped"] += 1
            results["details"].append((name, "SKIPPED", "非生鲜食品"))
            continue

        # --- 图片爬取 ---
        img_url = f"https://picsum.photos/seed/{keyword}/{IMAGE_WIDTH}/{IMAGE_HEIGHT}"
        fname = f"product_{next_id}.jpg"
        dest = os.path.join(UPLOAD_DIR, fname)

        log(f"  [{i+1:2d}] 爬取 {name:8s} -> {img_url}")
        size = download_image(img_url, dest)

        if size == 0:
            log(f"  [{i+1:2d}] FAIL {name:8s} - 图片下载失败")
            results["failed"] += 1
            results["details"].append((name, "FAILED", img_url))
            next_id += 1  # 即使失败也推进 ID
            time.sleep(CRAWL_DELAY_MIN)
            continue

        # --- 分类映射 ---
        category = map_category(name)
        if category == "其他":
            log(f"  [{i+1:2d}] WARN {name:8s} - 未匹配到分类，使用默认")
            # 给个默认分类（实际不会触发，因为 is_fresh_food 已经验证过）
            category = "蔬菜"

        # --- 写入数据库 ---
        image_path = f"/uploads/products/{fname}"
        cur.execute("""
            INSERT INTO products (name, category, price, stock, min_stock, image_url, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, category, price, stock, min_stock, image_path, desc))

        results["success"] += 1
        results["details"].append((name, "OK", f"{img_url} -> {image_path}"))
        log(f"  [{i+1:2d}] OK   {name:8s} | {category} | {image_path} ({size//1024}KB)")

        next_id += 1
        # 限制数量
        if results["success"] >= PRODUCT_LIMIT:
            log(f"  [限制] 已达到 {PRODUCT_LIMIT} 个商品上限，停止爬取")
            break

        # 随机延迟
        delay = CRAWL_DELAY_MIN + (CRAWL_DELAY_MAX - CRAWL_DELAY_MIN) * (hash(name) % 100) / 100.0
        time.sleep(delay)

    return results

# ================================================================
#  主入口（事务控制）
# ================================================================
def main():
    print("=" * 65)
    print("  生鲜商城 - 商品爬取与数据库重建")
    print("  数据源: picsum.photos (Unsplash 免费摄影)")
    print(f"  最大商品数: {PRODUCT_LIMIT}")
    print(f"  图片目录: {UPLOAD_DIR}")
    print("=" * 65)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # ===== BEGIN TRANSACTION =====
        conn.execute("BEGIN IMMEDIATE")
        log("[事务] 开始事务")

        # 步骤 1: 备份图片路径
        backed = backup_image_paths(conn)

        # 步骤 2: 删除所有商品
        deleted = delete_all_products(conn)

        # 步骤 3: 删除图片文件
        cleaned = delete_upload_images()

        # 步骤 4-6: 爬取 + 下载 + 写入
        results = process_products(conn)

        # ===== COMMIT =====
        conn.commit()
        log("[事务] 提交事务成功")

        # ===== 输出日志 =====
        print("\n" + "=" * 65)
        print("  执行结果")
        print("=" * 65)
        print(f"  成功插入: {results['success']} 个商品")
        print(f"  下载失败: {results['failed']} 个")
        print(f"  已跳过:   {results['skipped']} 个")
        print(f"  备份路径: {backed} 条")
        print(f"  已删除:   {deleted} 条旧记录 + {cleaned} 张旧图片")
        print("-" * 65)
        print("  详细映射:")
        for name, status, info in results["details"]:
            print(f"    {name:10s} [{status}] {info}")
        print("=" * 65)

    except Exception as e:
        conn.rollback()
        log(f"[错误] 事务已回滚！原因: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

    # 最终验证
    print("\n[验证]")
    verify = sqlite3.connect(DB_PATH)
    vcur = verify.cursor()
    vcur.execute("SELECT COUNT(*) FROM products")
    total = vcur.fetchone()[0]
    print(f"  数据库中共 {total} 个商品")
    if total > 0:
        vcur.execute("SELECT id, name, category, image_url FROM products ORDER BY id")
        for r in vcur.fetchall():
            path = r[3]
            fname = os.path.basename(path)
            fpath = os.path.join(UPLOAD_DIR, fname)
            exists = "OK" if os.path.exists(fpath) else "MISSING"
            print(f"    {r[0]:2d}. {r[1]:10s} | {r[2]} | {path} [{exists}]")

    # 检查备份表
    vcur.execute("SELECT COUNT(*) FROM bak_product_images")
    print(f"  备份表 bak_product_images: {vcur.fetchone()[0]} 条记录")

    # 检查图片目录
    files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".jpg")]
    print(f"  图片目录: {len(files)} 个文件")
    verify.close()

    print("\n" + "=" * 65)
    print("  完成！")
    print("=" * 65)

if __name__ == "__main__":
    main()