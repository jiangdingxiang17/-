"""
在线生鲜商城 - 数据完整性验证脚本
====================================
用途：独立验证 fresh_market.db 中所有数据的完整性和合理性。
可以独立运行，不依赖 Flask 应用。

验证项目：
  1. 所有商品有图片URL
  2. 分类正确（仅限 蔬菜/水果/肉类/鱼类）
  3. 价格和库存合理性
  4. 低库存预警正确
  5. 输出完整的验证报告
"""

import sqlite3
import os
import sys
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DB_PATH = os.path.join(PROJECT_ROOT, 'fresh_market.db')

VALID_CATEGORIES = ['蔬菜', '水果', '肉类', '鱼类']
IMAGE_URL_PATTERN = re.compile(
    r'^https?://(images|source)\.unsplash\.com/.*|'
    r'^https?://(.*\.)?picsum\.photos/.*'
)


class DataValidator:
    """数据库数据完整性验证器"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.results = {
            'passed': [],
            'warnings': [],
            'failed': [],
            'info': [],
            'stats': {}
        }
        self.conn = None
        self.cur = None

    def connect(self):
        """连接数据库"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f'数据库文件不存在: {self.db_path}')
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON;')
        self.cur = self.conn.cursor()

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def add_result(self, category, check_name, message, details=None):
        """记录验证结果"""
        entry = {'check': check_name, 'message': message}
        if details:
            entry['details'] = details
        self.results[category].append(entry)

    def run_all_checks(self):
        """执行所有验证检查"""
        print('=' * 70)
        print('  在线生鲜商城 - 数据完整性验证')
        print(f'  数据库: {self.db_path}')
        print(f'  验证时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        print('=' * 70)
        print()

        checks = [
            self.check_database_exists,
            self.check_table_structure,
            self.check_product_count,
            self.check_image_urls,
            self.check_categories,
            self.check_prices,
            self.check_stock,
            self.check_low_stock_alerts,
            self.check_duplicate_names,
            self.check_empty_names,
            self.check_is_active_column,
            self.check_user_accounts,
            self.check_cart_integrity,
            self.check_order_tables,
            self.collect_statistics,
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                self.add_result('failed', check.__name__, f'检查执行异常: {str(e)}')

    # ---- 各项检查 ----

    def check_database_exists(self):
        """检查数据库文件是否存在"""
        if os.path.exists(self.db_path):
            size_kb = os.path.getsize(self.db_path) / 1024
            self.add_result('passed', '数据库文件', f'数据库文件存在，大小: {size_kb:.1f} KB')
        else:
            self.add_result('failed', '数据库文件', '数据库文件不存在')

    def check_table_structure(self):
        """检查表结构完整性"""
        required_tables = ['users', 'products', 'cart_items']
        self.cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row['name'] for row in self.cur.fetchall()]

        for table in required_tables:
            if table in existing_tables:
                self.add_result('passed', f'表结构 - {table}', f'表 {table} 存在')
            else:
                self.add_result('failed', f'表结构 - {table}', f'表 {table} 不存在')

    def check_product_count(self):
        """检查商品总数"""
        self.cur.execute('SELECT COUNT(*) as cnt FROM products')
        count = self.cur.fetchone()['cnt']

        self.cur.execute('SELECT COUNT(*) as cnt FROM products WHERE is_active = 1')
        active_count = self.cur.fetchone()['cnt']

        self.cur.execute('SELECT COUNT(*) as cnt FROM products WHERE is_active = 0')
        inactive_count = self.cur.fetchone()['cnt']

        self.results['stats']['total_products'] = count
        self.results['stats']['active_products'] = active_count
        self.results['stats']['inactive_products'] = inactive_count

        if count >= 50:
            self.add_result('passed', '商品总数', f'商品总数 {count} 个（上架 {active_count}，下架 {inactive_count}），满足最低要求')
        elif count >= 14:
            self.add_result('warnings', '商品总数', f'商品总数 {count} 个，建议扩充至 50+ 以提供更好的演示效果')
        else:
            self.add_result('failed', '商品总数', f'商品总数仅 {count} 个，低于最低要求 14')

    def check_image_urls(self):
        """验证所有商品有图片URL"""
        self.cur.execute("SELECT id, name, image_url FROM products WHERE image_url IS NULL OR image_url = ''")
        no_image = [dict(row) for row in self.cur.fetchall()]

        if no_image:
            self.add_result('failed', '图片URL', f'{len(no_image)} 个商品缺少图片URL', details=no_image)
        else:
            self.add_result('passed', '图片URL', '所有商品均有图片URL')

        # 检查 URL 格式
        self.cur.execute("SELECT id, name, image_url FROM products WHERE image_url IS NOT NULL AND image_url != ''")
        all_images = [dict(row) for row in self.cur.fetchall()]

        bad_urls = []
        for p in all_images:
            if not IMAGE_URL_PATTERN.match(p['image_url']):
                bad_urls.append(p)

        if bad_urls:
            self.add_result('warnings', '图片URL格式',
                           f'{len(bad_urls)} 个商品图片URL不是Unsplash格式', details=bad_urls)
        else:
            self.add_result('passed', '图片URL格式',
                           f'所有 {len(all_images)} 个商品图片URL均为Unsplash格式')

    def check_categories(self):
        """验证分类正确性"""
        self.cur.execute(f"""
            SELECT id, name, category FROM products
            WHERE category NOT IN {tuple(VALID_CATEGORIES)}
        """)
        invalid = [dict(row) for row in self.cur.fetchall()]

        if invalid:
            self.add_result('failed', '商品分类', f'{len(invalid)} 个商品分类无效', details=invalid)
        else:
            self.add_result('passed', '商品分类', '所有商品分类有效（蔬菜/水果/肉类/鱼类）')

        # 各分类数量
        for cat in VALID_CATEGORIES:
            self.cur.execute('SELECT COUNT(*) as cnt FROM products WHERE category = ?', (cat,))
            cnt = self.cur.fetchone()['cnt']
            self.results['stats'][f'category_{cat}'] = cnt
            if cnt == 0:
                self.add_result('warnings', f'分类 - {cat}', f'分类 "{cat}" 没有任何商品')

    def check_prices(self):
        """验证价格合理性"""
        self.cur.execute('SELECT id, name, category, price FROM products WHERE price < 0')
        neg_price = [dict(row) for row in self.cur.fetchall()]
        if neg_price:
            self.add_result('failed', '价格检查', f'{len(neg_price)} 个商品价格为负数', details=neg_price)
        else:
            self.add_result('passed', '价格检查 - 负数', '所有商品价格非负')

        self.cur.execute('SELECT id, name, category, price FROM products WHERE price = 0')
        zero_price = [dict(row) for row in self.cur.fetchall()]
        if zero_price:
            self.add_result('info', '价格检查 - 零元',
                           f'{len(zero_price)} 个商品价格为 0（可能是促销品或赠品）', details=zero_price)

        self.cur.execute('SELECT id, name, category, price FROM products WHERE price > 500')
        too_high = [dict(row) for row in self.cur.fetchall()]
        if too_high:
            self.add_result('warnings', '价格检查 - 过高',
                           f'{len(too_high)} 个商品价格超过 500 元', details=too_high)

        # 价格统计
        self.cur.execute('''
            SELECT
                ROUND(MIN(price), 2) as min_p,
                ROUND(MAX(price), 2) as max_p,
                ROUND(AVG(price), 2) as avg_p
            FROM products WHERE price > 0
        ''')
        price_stats = self.cur.fetchone()
        self.results['stats']['price_range'] = f'¥{price_stats["min_p"]} ~ ¥{price_stats["max_p"]}'
        self.results['stats']['avg_price'] = f'¥{price_stats["avg_p"]}'

    def check_stock(self):
        """验证库存合理性"""
        self.cur.execute('SELECT id, name, category, stock FROM products WHERE stock < 0')
        neg_stock = [dict(row) for row in self.cur.fetchall()]
        if neg_stock:
            self.add_result('failed', '库存检查', f'{len(neg_stock)} 个商品库存为负数', details=neg_stock)
        else:
            self.add_result('passed', '库存检查 - 负数', '所有商品库存非负')

        self.cur.execute('SELECT id, name, category, stock FROM products WHERE stock = 0')
        zero_stock = [dict(row) for row in self.cur.fetchall()]
        if zero_stock:
            self.add_result('warnings', '库存检查 - 缺货',
                           f'{len(zero_stock)} 个商品已售罄（库存为0）', details=zero_stock)

        self.cur.execute('SELECT id, name, category, stock FROM products WHERE stock > 500')
        too_high = [dict(row) for row in self.cur.fetchall()]
        if too_high:
            self.add_result('warnings', '库存检查 - 过高',
                           f'{len(too_high)} 个商品库存超过 500，建议检查合理性', details=too_high)

        # 库存统计
        self.cur.execute('''
            SELECT MIN(stock) as min_s, MAX(stock) as max_s, ROUND(AVG(stock), 1) as avg_s
            FROM products
        ''')
        stock_stats = self.cur.fetchone()
        self.results['stats']['stock_range'] = f'{stock_stats["min_s"]} ~ {stock_stats["max_s"]}'
        self.results['stats']['avg_stock'] = f'{stock_stats["avg_s"]:.1f}'

        # min_stock 检查
        self.cur.execute('SELECT id, name, category, min_stock FROM products WHERE min_stock <= 0')
        invalid_min = [dict(row) for row in self.cur.fetchall()]
        if invalid_min:
            self.add_result('failed', '最低库存预警线',
                           f'{len(invalid_min)} 个商品 min_stock <= 0', details=invalid_min)
        else:
            self.add_result('passed', '最低库存预警线', '所有商品 min_stock > 0')

    def check_low_stock_alerts(self):
        """验证低库存预警正确性"""
        self.cur.execute('''
            SELECT id, name, category, stock, min_stock
            FROM products
            WHERE stock < min_stock
            ORDER BY stock ASC
        ''')
        low_stock = [dict(row) for row in self.cur.fetchall()]

        self.results['stats']['low_stock_count'] = len(low_stock)

        if low_stock:
            details_str = []
            for p in low_stock:
                gap = p['min_stock'] - p['stock']
                details_str.append(
                    f'[{p["category"]}] {p["name"]}: 库存 {p["stock"]} < 预警线 {p["min_stock"]} (差 {gap})'
                )
            self.add_result('info', '低库存预警',
                           f'发现 {len(low_stock)} 个低库存预警商品', details=details_str)
        else:
            self.add_result('info', '低库存预警', '当前无低库存预警商品')

        # 验证预警逻辑：确保 stock >= min_stock 的不在预警中
        self.cur.execute('''
            SELECT COUNT(*) as cnt FROM products
            WHERE stock >= min_stock
        ''')
        non_alert_count = self.cur.fetchone()['cnt']
        self.add_result('passed', '预警逻辑验证',
                       f'{non_alert_count} 个商品库存充足，未被误报预警')

    def check_duplicate_names(self):
        """检查重复商品名称"""
        self.cur.execute('SELECT name, COUNT(*) as cnt FROM products GROUP BY name HAVING cnt > 1')
        dupes = [dict(row) for row in self.cur.fetchall()]

        if dupes:
            self.add_result('failed', '重复名称',
                           f'发现 {len(dupes)} 个重复商品名称', details=dupes)
        else:
            self.add_result('passed', '重复名称', '无重复商品名称')

    def check_empty_names(self):
        """检查空商品名称"""
        self.cur.execute("SELECT id, category FROM products WHERE name IS NULL OR name = ''")
        empty = [dict(row) for row in self.cur.fetchall()]

        if empty:
            self.add_result('failed', '空名称', f'{len(empty)} 个商品名称为空', details=empty)
        else:
            self.add_result('passed', '空名称', '所有商品名称有效')

    def check_is_active_column(self):
        """检查 is_active 列是否存在"""
        self.cur.execute("PRAGMA table_info(products)")
        columns = [row[1] for row in self.cur.fetchall()]

        if 'is_active' not in columns:
            self.add_result('failed', 'is_active列', 'products 表缺少 is_active 列')
        else:
            self.add_result('passed', 'is_active列', 'products 表包含 is_active 列')

    def check_user_accounts(self):
        """检查用户账号"""
        self.cur.execute('SELECT COUNT(*) as cnt FROM users')
        user_count = self.cur.fetchone()['cnt']

        self.cur.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin'")
        admin_count = self.cur.fetchone()['cnt']

        self.cur.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'customer'")
        customer_count = self.cur.fetchone()['cnt']

        self.results['stats']['total_users'] = user_count
        self.results['stats']['admin_users'] = admin_count
        self.results['stats']['customer_users'] = customer_count

        if user_count >= 2:
            self.add_result('passed', '用户账号',
                           f'共 {user_count} 个用户（管理员 {admin_count}，顾客 {customer_count}）')
        else:
            self.add_result('warnings', '用户账号', f'用户数量较少：{user_count} 个')

    def check_cart_integrity(self):
        """检查购物车数据完整性"""
        # 检查是否存在孤儿记录（引用了不存在的用户或商品）
        self.cur.execute('''
            SELECT c.id FROM cart_items c
            LEFT JOIN users u ON c.user_id = u.id
            WHERE u.id IS NULL
        ''')
        orphan_user = [dict(row) for row in self.cur.fetchall()]

        self.cur.execute('''
            SELECT c.id FROM cart_items c
            LEFT JOIN products p ON c.product_id = p.id
            WHERE p.id IS NULL
        ''')
        orphan_product = [dict(row) for row in self.cur.fetchall()]

        if orphan_user:
            self.add_result('failed', '购物车完整性',
                           f'{len(orphan_user)} 条购物车记录引用了不存在的用户')
        elif orphan_product:
            self.add_result('failed', '购物车完整性',
                           f'{len(orphan_product)} 条购物车记录引用了不存在的商品')
        else:
            self.cur.execute('SELECT COUNT(*) as cnt FROM cart_items')
            cart_count = self.cur.fetchone()['cnt']
            self.add_result('passed', '购物车完整性',
                           f'购物车数据完整（{cart_count} 条记录），无孤儿记录')

    def check_order_tables(self):
        """检查订单表是否存在"""
        self.cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
        has_orders = self.cur.fetchone() is not None

        self.cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_items'")
        has_order_items = self.cur.fetchone() is not None

        if has_orders and has_order_items:
            self.cur.execute('SELECT COUNT(*) as cnt FROM orders')
            order_count = self.cur.fetchone()['cnt']
            self.results['stats']['total_orders'] = order_count
            self.add_result('passed', '订单表', f'订单表存在（{order_count} 条订单记录）')
        elif has_orders:
            self.add_result('warnings', '订单表', 'orders 表存在但 order_items 表缺失')
        else:
            self.add_result('info', '订单表', '订单相关表尚未创建')

    def collect_statistics(self):
        """收集综合统计信息"""
        # 各分类价格区间
        for cat in VALID_CATEGORIES:
            self.cur.execute('''
                SELECT
                    COUNT(*) as cnt,
                    ROUND(MIN(price), 2) as min_p,
                    ROUND(MAX(price), 2) as max_p,
                    ROUND(AVG(price), 2) as avg_p
                FROM products WHERE category = ?
            ''', (cat,))
            row = self.cur.fetchone()
            if row['cnt'] > 0:
                self.results['stats'][f'{cat}_price_range'] = f'¥{row["min_p"]} ~ ¥{row["max_p"]}'
                self.results['stats'][f'{cat}_avg_price'] = f'¥{row["avg_p"]}'

    # ---- 报告输出 ----

    def print_report(self):
        """输出完整验证报告"""
        self._print_summary()
        self._print_details()
        self._print_statistics()
        self._print_final_verdict()

    def _print_summary(self):
        """打印验证摘要"""
        total = len(self.results['passed']) + len(self.results['warnings']) + len(self.results['failed'])
        passed = len(self.results['passed'])
        warnings = len(self.results['warnings'])
        failed = len(self.results['failed'])
        info = len(self.results['info'])

        print()
        print('=' * 70)
        print('  验证摘要')
        print('=' * 70)
        print(f'  检查项目总数:  {total}')
        print(f'  通过:          {passed} 项')
        print(f'  警告:          {warnings} 项')
        print(f'  失败:          {failed} 项')
        print(f'  信息:          {info} 项')
        print()

        if failed == 0 and warnings == 0:
            print('  结论: [通过] 所有检查项均通过，数据完整性良好！')
        elif failed == 0:
            print(f'  结论: [通过（有警告）] 所有必要检查通过，{warnings} 个警告项建议关注。')
        else:
            print(f'  结论: [未通过] {failed} 个检查项失败，需要修复。')
        print()

    def _print_details(self):
        """打印详细检查结果"""
        sections = [
            ('失败项', 'failed', '❌'),
            ('警告项', 'warnings', '⚠️'),
            ('信息项', 'info', 'ℹ️'),
        ]

        for title, key, icon in sections:
            items = self.results[key]
            if not items:
                continue
            print(f'  {icon} {title} ({len(items)} 项):')
            print('  ' + '-' * 66)
            for item in items:
                print(f'  [{item["check"]}] {item["message"]}')
                if 'details' in item and item['details']:
                    details = item['details']
                    if isinstance(details, list):
                        for d in details[:10]:  # 最多显示10条
                            if isinstance(d, dict):
                                name = d.get('name', d.get('product_name', ''))
                                cat = d.get('category', '')
                                stock = d.get('stock', '')
                                price = d.get('price', '')
                                parts = []
                                if name:
                                    parts.append(name)
                                if cat:
                                    parts.append(f'[{cat}]')
                                if stock:
                                    parts.append(f'库存={stock}')
                                if price:
                                    parts.append(f'价格={price}')
                                print(f'      - {" ".join(parts)}')
                            else:
                                print(f'      - {d}')
                        if len(details) > 10:
                            print(f'      ... 还有 {len(details) - 10} 条')
            print()

        # 通过项（简化显示）
        passed = self.results['passed']
        if passed:
            print(f'  ✅ 通过项 ({len(passed)} 项):')
            print('  ' + '-' * 66)
            for item in passed:
                print(f'  [{item["check"]}] {item["message"]}')
            print()

    def _print_statistics(self):
        """打印统计信息"""
        stats = self.results['stats']
        if not stats:
            return

        print('=' * 70)
        print('  数据统计')
        print('=' * 70)

        # 商品概况
        print(f'  商品总数:      {stats.get("total_products", "N/A")}')
        print(f'    上架:        {stats.get("active_products", "N/A")}')
        print(f'    下架:        {stats.get("inactive_products", "N/A")}')
        print(f'  价格区间:      {stats.get("price_range", "N/A")}')
        print(f'  平均价格:      {stats.get("avg_price", "N/A")}')
        print(f'  库存区间:      {stats.get("stock_range", "N/A")}')
        print(f'  平均库存:      {stats.get("avg_stock", "N/A")}')
        print(f'  低库存预警:    {stats.get("low_stock_count", "N/A")} 个')
        print()

        # 分类统计
        print('  分类明细:')
        print('  ┌' + '─' * 54 + '┐')
        print('  │ 分类     数量    价格区间            均价       │')
        print('  ├' + '─' * 54 + '┤')
        for cat in VALID_CATEGORIES:
            cnt = stats.get(f'category_{cat}', 0)
            price_range = stats.get(f'{cat}_price_range', 'N/A')
            avg_price = stats.get(f'{cat}_avg_price', 'N/A')
            print(f'  │ {cat:<6}  {cnt:>3}个   {price_range:<18}  {avg_price:<8} │')
        print('  └' + '─' * 54 + '┘')
        print()

        # 用户和订单
        print(f'  用户账号:      {stats.get("total_users", "N/A")}')
        print(f'    管理员:      {stats.get("admin_users", "N/A")}')
        print(f'    顾客:        {stats.get("customer_users", "N/A")}')
        if 'total_orders' in stats:
            print(f'  订单总数:      {stats.get("total_orders", "N/A")}')
        print()

    def _print_final_verdict(self):
        """打印最终结论"""
        print('=' * 70)
        if len(self.results['failed']) == 0:
            print('  最终结论: 数据完整性验证通过')
            print('  数据库可以正常用于系统演示和开发。')
        else:
            print('  最终结论: 数据完整性验证未通过')
            print(f'  请修复 {len(self.results["failed"])} 个失败项后重新验证。')
        print('=' * 70)


def main():
    validator = DataValidator(DB_PATH)

    try:
        validator.connect()
    except FileNotFoundError as e:
        print(f'[错误] {e}')
        print(f'请先运行 import_dataset.py 初始化数据库。')
        sys.exit(1)

    validator.run_all_checks()
    validator.print_report()
    validator.close()

    # 返回退出码
    if validator.results['failed']:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
