import sqlite3
import os

backup_path = r'D:\2026暑期实训\agenticteam\fresh_market.db.backup'

if os.path.exists(backup_path):
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        
        # 获取表列表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f'备份文件有效!')
        print(f'表数量: {len(tables)}')
        print(f'表名: {[t[0] for t in tables]}')
        
        # 检查用户和商品数量
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f'{table_name}: {count} 条记录')
        
        conn.close()
    except Exception as e:
        print(f'错误: {e}')
else:
    print('备份文件不存在!')