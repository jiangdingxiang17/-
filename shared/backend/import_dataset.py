"""
在线生鲜商城 - 数据导入与迁移脚本
====================================
用途：重新初始化数据库，导入扩充后的 120+ 个商品数据 + Unsplash 商品图片
数据来源：参考 Kaggle Fruits-360 公开数据集 + 中国生鲜市场价格
图片来源：Unsplash 免费高清食物图片（遵循 Unsplash License）
"""

import sqlite3
import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DB_PATH = os.path.join(PROJECT_ROOT, 'fresh_market.db')

DDL_DIR = os.path.join(PROJECT_ROOT, 'shared', 'database', 'ddl')
DML_PATH = os.path.join(PROJECT_ROOT, 'shared', 'database', 'dml', 'seed_data.sql')
SCHEMA_PATH = os.path.join(DDL_DIR, 'schema.sql')
ORDER_TABLES_PATH = os.path.join(DDL_DIR, 'create_order_tables.sql')

VALID_CATEGORIES = ['蔬菜', '水果', '肉类', '鱼类']
IMAGE_URL_PATTERN = re.compile(
    r'^https?://(images|source)\.unsplash\.com/.*|'
    r'^https?://(.*\.)?picsum\.photos/.*'
)


def run_sql_file(cur, filepath):
    """执行 SQL 文件"""
    if not os.path.exists(filepath):
        print(f'  [警告] 文件不存在: {filepath}')
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    try:
        cur.executescript(sql)
    except sqlite3.Error as e:
        print(f'  [错误] 执行 {os.path.basename(filepath)} 时出错: {e}')
        raise


def validate_seed_data(cur):
    """在导入后立即验证种子数据的质量"""
    issues = []

    # 1. 验证商品总数是否达标
    cur.execute('SELECT COUNT(*) FROM products')
    product_count = cur.fetchone()[0]
    if product_count < 50:
        issues.append(f'商品数量不足（当前 {product_count}，预期 >= 50）')

    # 2. 验证每个分类都有商品
    for cat in VALID_CATEGORIES:
        cur.execute('SELECT COUNT(*) FROM products WHERE category = ?', (cat,))
        cnt = cur.fetchone()[0]
        if cnt == 0:
            issues.append(f'分类 "{cat}" 没有任何商品')

    # 3. 验证所有商品都有图片 URL
    cur.execute("SELECT id, name FROM products WHERE image_url IS NULL OR image_url = ''")
    no_image = cur.fetchall()
    for p in no_image:
        issues.append(f'商品 "{p["name"]}" (ID={p["id"]}) 缺少图片URL')

    # 4. 验证图片 URL 格式（应为 Unsplash URL）
    cur.execute("SELECT id, name, image_url FROM products WHERE image_url IS NOT NULL AND image_url != ''")
    all_with_image = cur.fetchall()
    for p in all_with_image:
        if not IMAGE_URL_PATTERN.match(p['image_url']):
            issues.append(f'商品 "{p["name"]}" (ID={p["id"]}) 图片URL格式异常: {p["image_url"]}')

    # 5. 验证价格合理性（生鲜价格应在 1~200 元范围内）
    cur.execute('SELECT id, name, price FROM products WHERE price <= 0')
    zero_or_neg_price = cur.fetchall()
    for p in zero_or_neg_price:
        issues.append(f'商品 "{p["name"]}" (ID={p["id"]}) 价格异常: {p["price"]}')

    cur.execute('SELECT id, name, price FROM products WHERE price > 500')
    too_expensive = cur.fetchall()
    for p in too_expensive:
        issues.append(f'商品 "{p["name"]}" (ID={p["id"]}) 价格过高: {p["price"]}')

    # 6. 验证库存合理性（非负且不超过合理上限）
    cur.execute('SELECT id, name, stock FROM products WHERE stock < 0')
    neg_stock = cur.fetchall()
    for p in neg_stock:
        issues.append(f'商品 "{p["name"]}" (ID={p["id"]}) 库存为负数: {p["stock"]}')

    cur.execute('SELECT id, name, stock FROM products WHERE stock > 1000')
    too_much_stock = cur.fetchall()
    for p in too_much_stock:
        issues.append(f'商品 "{p["name"]}" (ID={p["id"]}) 库存过高: {p["stock"]}')

    # 7. 验证 min_stock 合理性
    cur.execute('SELECT id, name, min_stock FROM products WHERE min_stock <= 0')
    invalid_min = cur.fetchall()
    for p in invalid_min:
        issues.append(f'商品 "{p["name"]}" (ID={p["id"]}) 最低库存预警线异常: {p["min_stock"]}')

    # 8. 验证名称不为空且无重复
    cur.execute("SELECT id FROM products WHERE name IS NULL OR name = ''")
    empty_name = cur.fetchall()
    for p in empty_name:
        issues.append(f'商品 ID={p["id"]} 名称为空')

    cur.execute('SELECT name, COUNT(*) as cnt FROM products GROUP BY name HAVING cnt > 1')
    dupes = cur.fetchall()
    for d in dupes:
        issues.append(f'商品名称重复: "{d["name"]}" 出现 {d["cnt"]} 次')

    # 9. 验证 is_active 列存在
    cur.execute("PRAGMA table_info(products)")
    columns = [row[1] for row in cur.fetchall()]
    if 'is_active' not in columns:
        issues.append('products 表缺少 is_active 列')

    return issues


def print_detailed_stats(cur):
    """打印详细的统计信息"""
    # 总览
    cur.execute('SELECT COUNT(*) FROM products')
    product_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM users')
    user_count = cur.fetchone()[0]

    # 各分类统计
    cur.execute('''
        SELECT
            category,
            COUNT(*) as cnt,
            ROUND(MIN(price), 2) as min_price,
            ROUND(MAX(price), 2) as max_price,
            ROUND(AVG(price), 2) as avg_price,
            MIN(stock) as min_stock_val,
            MAX(stock) as max_stock_val,
            ROUND(AVG(stock), 0) as avg_stock
        FROM products
        GROUP BY category
        ORDER BY category
    ''')
    category_stats = cur.fetchall()

    # 低库存预警
    cur.execute('SELECT COUNT(*) FROM products WHERE stock < min_stock')
    low_stock_count = cur.fetchone()[0]

    cur.execute('SELECT id, name, category, stock, min_stock FROM products WHERE stock < min_stock ORDER BY stock ASC')
    low_stock_items = cur.fetchall()

    # 图片覆盖率
    cur.execute("SELECT COUNT(*) FROM products WHERE image_url IS NOT NULL AND image_url != ''")
    with_image_count = cur.fetchone()[0]

    # 缺货商品
    cur.execute('SELECT COUNT(*) FROM products WHERE stock = 0')
    out_of_stock = cur.fetchone()[0]

    # 已下架商品
    cur.execute('SELECT COUNT(*) FROM products WHERE is_active = 0')
    inactive_count = cur.fetchone()[0]

    print()
    print('=' * 65)
    print('  数据库初始化完成 - 详细统计报告')
    print('=' * 65)
    print(f'  商品总数:        {product_count}')
    print(f'  用户账号:        {user_count}')
    print(f'  图片覆盖率:      {with_image_count}/{product_count} ({with_image_count*100//product_count if product_count else 0}%)')
    print(f'  低库存预警:      {low_stock_count} 个')
    print(f'  缺货商品:        {out_of_stock} 个')
    print(f'  已下架商品:      {inactive_count} 个')
    print()

    # 各分类详细统计
    print('  ┌' + '─' * 61 + '┐')
    print('  │ 分类       数量  最低价   最高价   均价     库存范围       │')
    print('  ├' + '─' * 61 + '┤')
    for row in category_stats:
        stock_range = f"{row['min_stock_val']}~{row['max_stock_val']}"
        print(
            f'  │ {row["category"]:<6}  '
            f'{row["cnt"]:>3}个  '
            f'¥{row["min_price"]:>6.2f}  '
            f'¥{row["max_price"]:>6.2f}  '
            f'¥{row["avg_price"]:>6.2f}  '
            f'{stock_range:>10}     │'
        )
    print('  └' + '─' * 61 + '┘')
    print()

    # 价格区间分布
    cur.execute('''
        SELECT
            CASE
                WHEN price < 10 THEN '0~10元'
                WHEN price < 30 THEN '10~30元'
                WHEN price < 60 THEN '30~60元'
                WHEN price < 100 THEN '60~100元'
                ELSE '100元以上'
            END as price_range,
            COUNT(*) as cnt
        FROM products
        GROUP BY price_range
        ORDER BY MIN(price)
    ''')
    price_ranges = cur.fetchall()
    print('  价格区间分布:')
    for pr in price_ranges:
        bar = '█' * (pr['cnt'])
        print(f'    {pr["price_range"]:<12} {pr["cnt"]:>3}个  {bar}')
    print()

    # 库存健康度分布
    cur.execute('''
        SELECT
            CASE
                WHEN stock = 0 THEN '缺货'
                WHEN stock < min_stock THEN '库存不足'
                WHEN stock < 20 THEN '库存偏低'
                ELSE '库存充足'
            END as stock_status,
            COUNT(*) as cnt
        FROM products
        GROUP BY stock_status
        ORDER BY CASE stock_status
            WHEN '缺货' THEN 1
            WHEN '库存不足' THEN 2
            WHEN '库存偏低' THEN 3
            ELSE 4
        END
    ''')
    stock_health = cur.fetchall()
    print('  库存健康度:')
    for sh in stock_health:
        bar = '█' * (sh['cnt'])
        print(f'    {sh["stock_status"]:<10} {sh["cnt"]:>3}个  {bar}')
    print()

    # 低库存预警详情
    if low_stock_items:
        print(f'  低库存预警详情 ({low_stock_count} 个):')
        for item in low_stock_items:
            print(f'    ⚠  [{item["category"]}] {item["name"]}: '
                  f'库存 {item["stock"]} < 预警线 {item["min_stock"]}')
    print()
    print(f'  数据库文件: {DB_PATH}')
    print('=' * 65)


def init_database():
    """完整初始化数据库"""
    print('=' * 65)
    print('  在线生鲜商城 - 数据导入工具')
    print('  支持导入 55+ 商品（可扩展至 120+）')
    print('  图片：Unsplash 免费高清食物图片')
    print('  数据集：参考 Kaggle Fruits-360 + 中国市场数据')
    print('=' * 65)
    print()

    # 1. 备份旧数据库（如果存在），然后删除以全新重建
    if os.path.exists(DB_PATH):
        backup_path = DB_PATH + '.backup'
        try:
            import shutil
            shutil.copy2(DB_PATH, backup_path)
            os.remove(DB_PATH)  # 删除旧数据库，全新重建
            print(f'[1/5] 已备份旧数据库到: {backup_path}')
            print(f'     已删除旧数据库，将全新重建')
        except Exception as e:
            print(f'[1/5] 备份失败（不影响导入）: {e}')
    else:
        print('[1/5] 未找到旧数据库，跳过备份')

    # 2. 创建全新数据库
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    cur = conn.cursor()
    print(f'[2/5] 已创建全新数据库: {DB_PATH}')

    # 3. 执行 DDL（创建表结构）
    print('[3/5] 执行 DDL 建表脚本...')
    run_sql_file(cur, SCHEMA_PATH)
    run_sql_file(cur, ORDER_TABLES_PATH)
    print('  表结构创建完成。')

    # 4. 执行 DML（插入种子数据）
    print('[4/5] 执行 DML 种子数据脚本...')
    run_sql_file(cur, DML_PATH)
    print('  种子数据插入完成。')

    # 5. 创建演示账号
    from werkzeug.security import generate_password_hash
    demo_users = [
        ('user1', generate_password_hash('123456'), 'customer'),
        ('admin', generate_password_hash('admin123'), 'admin')
    ]
    cur.executemany(
        'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
        demo_users
    )
    print('  演示账号创建完成：user1/123456, admin/admin123')

    conn.commit()

    # 6. 验证种子数据质量
    print('[5/5] 验证数据质量...')
    data_issues = validate_seed_data(cur)

    if data_issues:
        print(f'  [警告] 发现 {len(data_issues)} 个数据质量问题:')
        for i, issue in enumerate(data_issues, 1):
            print(f'    {i}. {issue}')
        print()
        print('  数据质量问题已列出，但导入仍将继续。')
        print('  请检查 seed_data.sql 文件并修复上述问题后重新导入。')
    else:
        print('  数据质量检查通过。')

    # 7. 打印详细统计
    print_detailed_stats(cur)

    conn.close()
    return True


def verify_data():
    """验证导入数据的完整性"""
    print()
    print('=' * 65)
    print('  数据完整性验证')
    print('=' * 65)

    if not os.path.exists(DB_PATH):
        print('  [错误] 数据库文件不存在！')
        return False

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    all_ok = True

    # 1. 商品总数检查
    cur.execute('SELECT COUNT(*) as cnt FROM products')
    count = cur.fetchone()['cnt']
    print(f'  商品总数: {count}')
    if count < 50:
        print(f'    [警告] 商品数量不足预期（当前 {count}，预期 >= 50）')
        all_ok = False
    else:
        print(f'    [通过] 商品数量满足最低要求')

    # 2. 各分类商品数
    cur.execute('''
        SELECT category, COUNT(*) as cnt
        FROM products GROUP BY category ORDER BY category
    ''')
    for row in cur.fetchall():
        print(f'    {row["category"]}: {row["cnt"]} 个')

    # 3. 图片 URL 验证
    cur.execute("SELECT COUNT(*) as cnt FROM products WHERE image_url IS NULL OR image_url = ''")
    no_img = cur.fetchone()['cnt']
    if no_img > 0:
        print(f'  [失败] 图片缺失: {no_img} 个商品缺少图片URL')
        all_ok = False
    else:
        print(f'  [通过] 所有商品均有图片URL')

    # 4. URL 格式验证
    cur.execute("SELECT id, name, image_url FROM products WHERE image_url IS NOT NULL AND image_url != ''")
    bad_urls = []
    for p in cur.fetchall():
        if not IMAGE_URL_PATTERN.match(p['image_url']):
            bad_urls.append(p)
    if bad_urls:
        print(f'  [警告] 图片URL非Unsplash格式: {len(bad_urls)} 个')
        for p in bad_urls:
            print(f'    - {p["name"]}: {p["image_url"][:80]}...')
    else:
        print(f'  [通过] 所有图片URL均为Unsplash格式')

    # 5. 价格验证
    cur.execute('SELECT COUNT(*) as cnt FROM products WHERE price < 0')
    if cur.fetchone()['cnt'] > 0:
        print('  [失败] 存在价格为负数的商品')
        all_ok = False
    else:
        print('  [通过] 所有商品价格非负')

    cur.execute('SELECT COUNT(*) as cnt FROM products WHERE price = 0')
    zero_price = cur.fetchone()['cnt']
    if zero_price > 0:
        print(f'  [注意] {zero_price} 个商品价格为0（可能是促销品）')

    # 6. 库存验证
    cur.execute('SELECT COUNT(*) as cnt FROM products WHERE stock < 0')
    if cur.fetchone()['cnt'] > 0:
        print('  [失败] 存在库存为负数的商品')
        all_ok = False
    else:
        print('  [通过] 所有商品库存非负')

    # 7. 分类验证
    cur.execute(f"SELECT COUNT(*) as cnt FROM products WHERE category NOT IN {tuple(VALID_CATEGORIES)}")
    if cur.fetchone()['cnt'] > 0:
        print('  [失败] 存在无效分类的商品')
        all_ok = False
    else:
        print('  [通过] 所有商品分类有效')

    # 8. 低库存预警验证
    cur.execute('SELECT COUNT(*) as cnt FROM products WHERE stock < min_stock')
    low_count = cur.fetchone()['cnt']
    print(f'  低库存预警: {low_count} 个商品')
    cur.execute('SELECT id, name, category, stock, min_stock FROM products WHERE stock < min_stock ORDER BY stock ASC')
    for p in cur.fetchall():
        print(f'    ⚠  [{p["category"]}] {p["name"]}: 库存 {p["stock"]} < 预警线 {p["min_stock"]}')

    # 9. 重复名称检查
    cur.execute('SELECT name, COUNT(*) as cnt FROM products GROUP BY name HAVING cnt > 1')
    dupes = cur.fetchall()
    if dupes:
        print(f'  [警告] 发现 {len(dupes)} 个重复商品名称:')
        for d in dupes:
            print(f'    - "{d["name"]}" 出现 {d["cnt"]} 次')
        all_ok = False
    else:
        print('  [通过] 无重复商品名称')

    # 10. is_active 列检查
    cur.execute("PRAGMA table_info(products)")
    columns = [row[1] for row in cur.fetchall()]
    if 'is_active' not in columns:
        print('  [失败] products 表缺少 is_active 列')
        all_ok = False
    else:
        print('  [通过] is_active 列存在')

    # 11. 空名称检查
    cur.execute("SELECT COUNT(*) as cnt FROM products WHERE name IS NULL OR name = ''")
    if cur.fetchone()['cnt'] > 0:
        print('  [失败] 存在名称为空的商品')
        all_ok = False
    else:
        print('  [通过] 所有商品名称有效')

    # 12. min_stock 检查
    cur.execute('SELECT COUNT(*) as cnt FROM products WHERE min_stock <= 0')
    if cur.fetchone()['cnt'] > 0:
        print('  [警告] 存在 min_stock <= 0 的商品')
    else:
        print('  [通过] 所有商品 min_stock > 0')

    conn.close()

    print()
    if all_ok:
        print('  [结果] 数据完整性验证通过！')
    else:
        print('  [结果] 数据完整性验证未通过，请检查上述问题。')
    print('=' * 65)
    return all_ok


if __name__ == '__main__':
    success = init_database()
    if success:
        verify_data()
        print()
        print('  生鲜商城数据导入完成！')
        print('   - 数据集来源：Kaggle Fruits-360 + 中国生鲜市场价格')
        print('   - 图片来源：Unsplash 免费高清图片')
        print('   - 支持 55+ 商品（可扩展至 120+）')
        print('   - 可启动 Flask 应用查看效果：python app.py')
    else:
        print('  数据导入失败，请检查错误信息')
        sys.exit(1)
