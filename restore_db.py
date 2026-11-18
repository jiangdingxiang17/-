import shutil
import os

source = r'D:\2026暑期实训\agenticteam\fresh_market.db.backup'
destination = r'D:\2026暑期实训\agenticteam\fresh_market.db'

try:
    shutil.copy2(source, destination)
    print(f'成功复制文件: {source} -> {destination}')
    print(f'文件大小: {os.path.getsize(destination)} 字节')
except Exception as e:
    print(f'错误: {e}')