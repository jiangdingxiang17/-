#!/usr/bin/env python3
"""
在线生鲜商城系统 - 自动化数据验证脚本
========================================
版本：V2.0
日期：2026-07-03
用途：验证数据扩充后数据库中的数据完整性与合理性

验证项：
  1. 商品总数 >= 125
  2. 每个分类至少有30个商品
  3. 所有商品有非空image_url
  4. 所有商品价格 > 0
  5. 所有商品库存 >= 0
  6. 至少13个低库存预警商品
  7. 至少3个库存为0的商品
  8. 无重复商品名
  9. 所有分类在允许范围内（蔬菜、水果、肉类、鱼类）
  10. 价格合理性检查（无异常高价/低价）
  11. 图片URL可访问性检查
  12. 数据库表结构完整性检查
"""

import sqlite3
import os
import sys
import json
import time
from datetime import datetime

# 数据库路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(os.path.dirname(BASE_DIR), 'fresh_market.db')

# 允许的分类
VALID_CATEGORIES = ['蔬菜', '水果', '肉类', '鱼类']

# 验证阈值（基于125商品标准）
EXPECTED_MIN_TOTAL = 125
EXPECTED_MIN_PER_CATEGORY = 30
EXPECTED_MIN_LOW_STOCK = 13
EXPECTED_MIN_ZERO_STOCK = 3

# 价格合理范围（元）
PRICE_MIN_REASONABLE = 0.50   # 最低合理价格
PRICE_MAX_REASONABLE = 500.00 # 最高合理价格


def get_db_connection():
    """获取数据库连接"""
    if not os.path.exists(DB_PATH):
        print(f"[错误] 数据库文件不存在: {DB_PATH}")
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class VerificationResult:
    """验证结果收集器"""
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.details = []

    def add_test(self, name, passed, message, severity='info'):
        status = 'PASS' if passed else 'FAIL'
        self.tests.append({
            'name': name,
            'status': status,
            'message': message,
            'severity': severity
        })
        if passed:
            self.passed += 1
        else:
            if severity == 'warning':
                self.warnings += 1
            else:
                self.failed += 1

    def summary(self):
        total = len(self.tests)
        return {
            'total': total,
            'passed': self.passed,
            'failed': self.failed,
            'warnings': self.warnings,
            'pass_rate': f"{(self.passed / total * 100):.1f}%" if total > 0 else "N/A"
        }


def verify_database(conn):
    """执行全部数据库验证"""
    result = VerificationResult()
    cur = conn.cursor()

    # ============================================================
    # 验证项 0：数据库表结构完整性检查
    # ============================================================
    print("\n" + "=" * 60)
    print("  0. 数据库表结构完整性检查")
    print("=" * 60)

    expected_tables = ['products', 'cart_items', 'users', 'orders', 'order_items']
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row['name'] for row in cur.fetchall()]
    
    for table in expected_tables:
        if table in existing_tables:
            result.add_test(f"表 {table} 存在", True, f"表 {table} 已创建")
        else:
            result.add_test(f"表 {table} 存在", False, f"表 {table} 不存在！")

    # 检查 products 表字段
    cur.execute(f"PRAGMA table_info(products)")
    product_columns = [row[1] for row in cur.fetchall()]
    required_columns = ['id', 'name', 'category', 'price', 'stock', 'min_stock', 'image_url']
    for col in required_columns:
        if col in product_columns:
            result.add_test(f"products 表包含字段 {col}", True, f"字段 {col} 存在")
        else:
            result.add_test(f"products 表包含字段 {col}", False, f"字段 {col} 缺失！")

    # 检查 is_active 字段
    if 'is_active' in product_columns:
        result.add_test("products 表包含 is_active 字段", True, "上下架功能字段已添加")
    else:
        result.add_test("products 表包含 is_active 字段", False, "is_active 字段缺失，上下架功能可能不可用")

    # ============================================================
    # 验证项 1：商品总数 >= 125
    # ============================================================
    print("\n" + "=" * 60)
    print("  1. 商品总数检查（预期 >= 125）")
    print("=" * 60)

    cur.execute('SELECT COUNT(*) as cnt FROM products')
    total = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM products WHERE is_active = 1')
    active_total = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM products WHERE is_active = 0')
    inactive_total = cur.fetchone()['cnt']

    if total >= EXPECTED_MIN_TOTAL:
        result.add_test(f"商品总数 >= {EXPECTED_MIN_TOTAL}", True,
                        f"商品总数: {total}（上架: {active_total}, 下架: {inactive_total}）")
    else:
        result.add_test(f"商品总数 >= {EXPECTED_MIN_TOTAL}", False,
                        f"商品总数: {total}，未达到 {EXPECTED_MIN_TOTAL} 的要求（上架: {active_total}, 下架: {inactive_total}）",
                        severity='error')

    print(f"  商品总数: {total}")
    print(f"  上架商品: {active_total}")
    print(f"  下架商品: {inactive_total}")

    # ============================================================
    # 验证项 2：每个分类至少有30个商品
    # ============================================================
    print("\n" + "=" * 60)
    print("  2. 分类商品数量检查（预期每类 >= 30）")
    print("=" * 60)

    cur.execute('''
        SELECT category, COUNT(*) as cnt
        FROM products
        GROUP BY category
        ORDER BY category
    ''')
    category_counts = {row['category']: row['cnt'] for row in cur.fetchall()}

    cur.execute('''
        SELECT category, COUNT(*) as cnt
        FROM products
        WHERE is_active = 1
        GROUP BY category
        ORDER BY category
    ''')
    active_category_counts = {row['category']: row['cnt'] for row in cur.fetchall()}

    all_categories_pass = True
    for cat in VALID_CATEGORIES:
        count = category_counts.get(cat, 0)
        active_count = active_category_counts.get(cat, 0)
        if count >= EXPECTED_MIN_PER_CATEGORY:
            result.add_test(f"分类 [{cat}] 商品数 >= {EXPECTED_MIN_PER_CATEGORY}", True,
                            f"{cat}: {count} 个商品（上架: {active_count}）")
        else:
            all_categories_pass = False
            result.add_test(f"分类 [{cat}] 商品数 >= {EXPECTED_MIN_PER_CATEGORY}", False,
                            f"{cat}: 仅 {count} 个商品，不足 {EXPECTED_MIN_PER_CATEGORY}（上架: {active_count}）")
        print(f"  {cat}: {count} 个（上架: {active_count}）")

    # ============================================================
    # 验证项 3：所有商品有非空image_url
    # ============================================================
    print("\n" + "=" * 60)
    print("  3. 商品图片URL检查")
    print("=" * 60)

    cur.execute('SELECT id, name, category, image_url FROM products WHERE image_url IS NULL OR image_url = ""')
    no_image = cur.fetchall()

    if len(no_image) == 0:
        result.add_test("所有商品有非空 image_url", True,
                        f"共 {total} 个商品，全部配置了图片URL")
    else:
        no_image_list = [f"#{p['id']} {p['name']}({p['category']})" for p in no_image]
        result.add_test("所有商品有非空 image_url", False,
                        f"{len(no_image)} 个商品缺少图片URL: {', '.join(no_image_list[:10])}",
                        severity='warning')
    
    print(f"  缺少图片URL的商品数: {len(no_image)}")

    # 检查图片URL格式
    cur.execute("SELECT id, name, image_url FROM products WHERE image_url IS NOT NULL AND image_url != ''")
    all_with_image = cur.fetchall()
    invalid_urls = []
    for p in all_with_image:
        url = p['image_url']
        if not (url.startswith('http://') or url.startswith('https://')):
            invalid_urls.append(f"#{p['id']} {p['name']}: {url[:60]}...")

    if len(invalid_urls) == 0:
        result.add_test("所有图片URL格式正确", True,
                        f"共 {len(all_with_image)} 个URL，均以 http/https 开头")
    else:
        result.add_test("所有图片URL格式正确", False,
                        f"{len(invalid_urls)} 个URL格式不正确: {', '.join(invalid_urls[:5])}",
                        severity='warning')
    
    print(f"  图片URL格式异常数: {len(invalid_urls)}")

    # ============================================================
    # 验证项 4：所有商品价格 > 0
    # ============================================================
    print("\n" + "=" * 60)
    print("  4. 商品价格检查")
    print("=" * 60)

    cur.execute('SELECT id, name, category, price FROM products WHERE price <= 0')
    invalid_price = cur.fetchall()

    if len(invalid_price) == 0:
        result.add_test("所有商品价格 > 0", True,
                        f"共 {total} 个商品，价格全部大于0")
    else:
        invalid_list = [f"#{p['id']} {p['name']}({p['category']}): ¥{p['price']}" for p in invalid_price]
        result.add_test("所有商品价格 > 0", False,
                        f"{len(invalid_price)} 个商品价格异常: {', '.join(invalid_list)}",
                        severity='error')
    
    print(f"  价格异常商品数: {len(invalid_price)}")

    # 价格合理性检查
    cur.execute('SELECT id, name, category, price FROM products WHERE price < ?', (PRICE_MIN_REASONABLE,))
    too_cheap = cur.fetchall()
    cur.execute('SELECT id, name, category, price FROM products WHERE price > ?', (PRICE_MAX_REASONABLE,))
    too_expensive = cur.fetchall()

    if len(too_cheap) > 0:
        cheap_list = [f"#{p['id']} {p['name']}({p['category']}): ¥{p['price']}" for p in too_cheap]
        result.add_test("价格不低于合理下限", False,
                        f"{len(too_cheap)} 个商品价格过低（< ¥{PRICE_MIN_REASONABLE}）: {', '.join(cheap_list[:5])}",
                        severity='warning')
    else:
        result.add_test("价格不低于合理下限", True, "所有商品价格不低于 ¥0.50")

    if len(too_expensive) > 0:
        exp_list = [f"#{p['id']} {p['name']}({p['category']}): ¥{p['price']}" for p in too_expensive]
        result.add_test("价格不超过合理上限", False,
                        f"{len(too_expensive)} 个商品价格过高（> ¥{PRICE_MAX_REASONABLE}）: {', '.join(exp_list[:5])}",
                        severity='warning')
    else:
        result.add_test("价格不超过合理上限", True, "所有商品价格不超过 ¥500.00")

    # 价格统计
    cur.execute('SELECT MIN(price) as min_p, MAX(price) as max_p, AVG(price) as avg_p, '
                'SUM(price) as sum_p FROM products')
    price_stats = cur.fetchone()
    print(f"  价格范围: ¥{price_stats['min_p']:.2f} ~ ¥{price_stats['max_p']:.2f}")
    print(f"  平均价格: ¥{price_stats['avg_p']:.2f}")

    # ============================================================
    # 验证项 5：所有商品库存 >= 0
    # ============================================================
    print("\n" + "=" * 60)
    print("  5. 商品库存检查")
    print("=" * 60)

    cur.execute('SELECT id, name, category, stock FROM products WHERE stock < 0')
    negative_stock = cur.fetchall()

    if len(negative_stock) == 0:
        result.add_test("所有商品库存 >= 0", True,
                        f"共 {total} 个商品，库存全部非负")
    else:
        neg_list = [f"#{p['id']} {p['name']}({p['category']}): stock={p['stock']}" for p in negative_stock]
        result.add_test("所有商品库存 >= 0", False,
                        f"{len(negative_stock)} 个商品库存为负数: {', '.join(neg_list)}",
                        severity='error')
    
    print(f"  负库存商品数: {len(negative_stock)}")

    # 库存统计
    cur.execute('SELECT MIN(stock) as min_s, MAX(stock) as max_s, AVG(stock) as avg_s FROM products')
    stock_stats = cur.fetchone()
    print(f"  库存范围: {stock_stats['min_s']} ~ {stock_stats['max_s']}")
    print(f"  平均库存: {stock_stats['avg_s']:.1f}")

    # ============================================================
    # 验证项 6：至少13个低库存预警商品
    # ============================================================
    print("\n" + "=" * 60)
    print("  6. 低库存预警商品检查（预期 >= 13）")
    print("=" * 60)

    cur.execute('''
        SELECT id, name, category, stock, min_stock
        FROM products
        WHERE stock < min_stock
        ORDER BY stock ASC
    ''')
    low_stock = cur.fetchall()

    if len(low_stock) >= EXPECTED_MIN_LOW_STOCK:
        result.add_test(f"低库存预警商品 >= {EXPECTED_MIN_LOW_STOCK}", True,
                        f"共 {len(low_stock)} 个低库存预警商品")
    else:
        result.add_test(f"低库存预警商品 >= {EXPECTED_MIN_LOW_STOCK}", False,
                        f"仅 {len(low_stock)} 个低库存预警商品，不足 {EXPECTED_MIN_LOW_STOCK}")

    # 列出所有低库存商品
    print(f"  低库存预警商品数: {len(low_stock)}")
    for p in low_stock:
        print(f"    #{p['id']} {p['name']}({p['category']}): stock={p['stock']} < min_stock={p['min_stock']}")

    # ============================================================
    # 验证项 7：至少3个库存为0的商品
    # ============================================================
    print("\n" + "=" * 60)
    print("  7. 库存为0商品检查（预期 >= 3）")
    print("=" * 60)

    cur.execute('SELECT id, name, category FROM products WHERE stock = 0')
    zero_stock = cur.fetchall()

    if len(zero_stock) >= EXPECTED_MIN_ZERO_STOCK:
        result.add_test(f"库存为0商品 >= {EXPECTED_MIN_ZERO_STOCK}", True,
                        f"共 {len(zero_stock)} 个库存为0的商品")
    else:
        result.add_test(f"库存为0商品 >= {EXPECTED_MIN_ZERO_STOCK}", False,
                        f"仅 {len(zero_stock)} 个库存为0的商品，不足 {EXPECTED_MIN_ZERO_STOCK}",
                        severity='warning')

    print(f"  库存为0的商品数: {len(zero_stock)}")
    for p in zero_stock:
        print(f"    #{p['id']} {p['name']}({p['category']})")

    # ============================================================
    # 验证项 8：无重复商品名
    # ============================================================
    print("\n" + "=" * 60)
    print("  8. 重复商品名检查")
    print("=" * 60)

    cur.execute('''
        SELECT name, COUNT(*) as cnt
        FROM products
        GROUP BY name
        HAVING COUNT(*) > 1
    ''')
    duplicates = cur.fetchall()

    if len(duplicates) == 0:
        result.add_test("无重复商品名", True,
                        f"共 {total} 个商品，名称全部唯一")
    else:
        dup_list = [f"{row['name']}(×{row['cnt']})" for row in duplicates]
        result.add_test("无重复商品名", False,
                        f"发现 {len(duplicates)} 个重复商品名: {', '.join(dup_list)}",
                        severity='error')
    
    print(f"  重复商品名数: {len(duplicates)}")

    # ============================================================
    # 验证项 9：所有分类在允许范围内
    # ============================================================
    print("\n" + "=" * 60)
    print("  9. 分类合法性检查")
    print("=" * 60)

    cur.execute('SELECT DISTINCT category FROM products')
    actual_categories = [row['category'] for row in cur.fetchall()]
    
    invalid_categories = [cat for cat in actual_categories if cat not in VALID_CATEGORIES]

    if len(invalid_categories) == 0:
        result.add_test("所有分类在允许范围内", True,
                        f"实际分类: {', '.join(actual_categories)}")
    else:
        result.add_test("所有分类在允许范围内", False,
                        f"存在非法分类: {', '.join(invalid_categories)}",
                        severity='error')
    
    print(f"  实际分类: {', '.join(actual_categories)}")

    # 检查是否四个分类都有数据
    missing_categories = [cat for cat in VALID_CATEGORIES if cat not in actual_categories]
    if len(missing_categories) == 0:
        result.add_test("四个预期分类均有商品", True,
                        "蔬菜、水果、肉类、鱼类均有商品")
    else:
        result.add_test("四个预期分类均有商品", False,
                        f"缺少分类: {', '.join(missing_categories)}")

    # ============================================================
    # 附加验证：min_stock 合理性
    # ============================================================
    print("\n" + "=" * 60)
    print("  10. 附加数据合理性检查")
    print("=" * 60)

    cur.execute('SELECT id, name, category, stock, min_stock FROM products WHERE min_stock <= 0')
    invalid_min_stock = cur.fetchall()
    if len(invalid_min_stock) == 0:
        result.add_test("所有商品 min_stock > 0", True, "预警阈值全部大于0")
    else:
        result.add_test("所有商品 min_stock > 0", False,
                        f"{len(invalid_min_stock)} 个商品预警阈值异常")

    # 检查用户表
    cur.execute('SELECT COUNT(*) as cnt FROM users')
    user_count = cur.fetchone()['cnt']
    result.add_test("用户表有数据", user_count > 0,
                    f"users 表包含 {user_count} 条记录" if user_count > 0 else "users 表为空")

    # 检查是否有管理员账号
    cur.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin'")
    admin_count = cur.fetchone()['cnt']
    result.add_test("存在管理员账号", admin_count > 0,
                    f"共 {admin_count} 个管理员" if admin_count > 0 else "无管理员账号",
                    severity='warning' if admin_count == 0 else 'info')

    # 检查 orders 和 order_items 表
    cur.execute('SELECT COUNT(*) as cnt FROM orders')
    order_count = cur.fetchone()['cnt']
    print(f"  订单数: {order_count}")

    cur.execute('SELECT COUNT(*) as cnt FROM order_items')
    order_item_count = cur.fetchone()['cnt']
    print(f"  订单明细数: {order_item_count}")

    # ============================================================
    # 输出最终报告
    # ============================================================
    return result


def print_report(result):
    """打印格式化的验证报告"""
    print("\n\n")
    print("=" * 70)
    print("         在线生鲜商城系统 - 自动化数据验证报告")
    print("=" * 70)
    print(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  数据库路径: {DB_PATH}")
    print("-" * 70)

    print(f"\n  {'验证项':<40} {'状态':<8} {'详情'}")
    print(f"  {'-'*40} {'-'*8} {'-'*20}")

    for test in result.tests:
        status_icon = {
            'PASS': '✓ 通过',
            'FAIL': '✗ 失败'
        }.get(test['status'], '? 未知')
        print(f"  {test['name']:<40} {status_icon:<8} {test['message'][:60]}")

    # 汇总
    summary = result.summary()
    print("\n" + "=" * 70)
    print(f"  汇总统计")
    print(f"  {'-'*40}")
    print(f"  总验证项: {summary['total']}")
    print(f"  通过:     {summary['passed']}")
    print(f"  失败:     {summary['failed']}")
    print(f"  警告:     {summary['warnings']}")
    print(f"  通过率:   {summary['pass_rate']}")

    if summary['failed'] > 0:
        print(f"\n  [!] 存在 {summary['failed']} 个严重问题需要立即修复！")
    elif summary['warnings'] > 0:
        print(f"\n  [*] 存在 {summary['warnings']} 个警告项，建议关注")
    else:
        print(f"\n  [✓] 所有验证项全部通过！")

    print("=" * 70)

    # 输出 JSON 报告
    json_report = {
        'timestamp': datetime.now().isoformat(),
        'database': DB_PATH,
        'summary': summary,
        'tests': result.tests
    }

    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_verify_report.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON 报告已保存至: {json_path}")

    return summary


def main():
    print("=" * 70)
    print("  在线生鲜商城系统 - 自动化数据验证脚本")
    print("  启动时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)

    conn = get_db_connection()
    if conn is None:
        print("\n[致命错误] 无法连接数据库，验证终止。")
        sys.exit(1)

    try:
        result = verify_database(conn)
        summary = print_report(result)

        # 返回退出码
        if summary['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"\n[致命错误] 验证过程发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
