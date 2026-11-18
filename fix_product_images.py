import urllib.request, os, time, hashlib, sqlite3, re, datetime

DB = "D:\\2026暑期实训\\agenticteam\\fresh_market.db"
IMG_DIR = "D:\\2026暑期实训\\agenticteam\\shared\\backend\\static\\images\\products"
SEED_SQL = "D:\\2026暑期实训\\agenticteam\\shared\\database\\dml\\seed_data.sql"

# Keyword mapping
KW = {
"西红柿":"tomato","黄瓜":"cucumber","菠菜":"spinach","土豆":"potato",
"大白菜":"napa-cabbage","生菜":"lettuce","胡萝卜":"carrot","西兰花":"broccoli",
"芹菜":"celery","青椒":"green-pepper","茄子":"eggplant","豆角":"green-beans",
"南瓜":"pumpkin","甜玉米":"sweet-corn","韭菜":"chinese-chives","洋葱":"onion",
"冬瓜":"winter-melon","莲藕":"lotus-root","山药":"chinese-yam","苦瓜":"bitter-gourd",
"蒜苗":"garlic-sprouts","红薯":"sweet-potato","丝瓜":"luffa-gourd","秋葵":"okra",
"空心菜":"water-spinach","白萝卜":"daikon-radish","莴笋":"celtuce-stem","花菜":"cauliflower",
"茼蒿":"crown-daisy","娃娃菜":"baby-cabbage",
"红富士苹果":"fuji-apple","香蕉":"banana","阳光玫瑰葡萄":"shine-muscat-grapes",
"海南金钻菠萝":"golden-pineapple","丹东草莓":"strawberry","海南芒果":"mango",
"麒麟西瓜":"watermelon","赣南脐橙":"navel-orange","徐香猕猴桃":"kiwifruit",
"智利车厘子":"cherry","妃子笑荔枝":"lychee","红心火龙果":"dragon-fruit",
"秘鲁蓝莓":"blueberry","文旦柚":"pomelo","阳山水蜜桃":"peach",
"新疆哈密瓜":"hami-melon","龙眼":"longan","山竹":"mangosteen",
"阿克苏苹果":"apple","突尼斯软籽石榴":"pomegranate","海南椰子":"coconut",
"金枕榴莲":"durian","樱桃番茄":"cherry-tomato","红提":"red-grapes",
"库尔勒香梨":"pear","百香果":"passion-fruit","砂糖橘":"mandarin-orange",
"释迦果":"sugar-apple","杨梅":"bayberry","青提":"green-grapes",
"澳洲无籽红提":"red-seedless-grapes","柠檬":"lemon",
"黑猪五花肉":"pork-belly","散养土鸡":"whole-chicken","安格斯牛排":"beef-steak",
"猪里脊肉":"pork-tenderloin","澳洲牛腩":"beef-brisket","羊腿肉":"lamb",
"鸡胸肉":"chicken-breast","半片鸭":"duck","猪小排":"pork-ribs",
"金钱腱":"beef-shank","鸡翅中":"chicken-wings","猪肉馅":"ground-pork",
"金华火腿":"cured-ham","牛腱子":"beef-shank-n","猪蹄":"pork-trotter",
"鸡腿":"chicken-drumstick","羊排":"lamb-rack","牛尾":"oxtail",
"鸭胸肉":"duck-breast","猪肉片":"pork-slice","鸡爪":"chicken-feet",
"牛百叶":"beef-tripe","猪肝":"pork-liver","肥牛卷":"beef-roll",
"乌鸡":"silkie-chicken","牛里脊":"beef-tenderloin","培根":"bacon",
"猪大肠":"pork-intestine","腊肉":"cured-pork","牛肉馅":"ground-beef",
"鸽子":"pigeon","鸡胗":"chicken-gizzard",
"活鲫鱼":"crucian-carp","三文鱼刺身":"salmon","北极甜虾":"shrimp-1",
"东海带鱼":"hairtail-fish","黄花鱼":"yellow-croaker","海鲈鱼":"sea-bass",
"基围虾":"jumbo-shrimp","乳山生蚝":"oyster","扇贝":"scallop",
"鱿鱼":"squid","金鲳鱼":"pomfret","花蛤":"clams",
"大连海参":"sea-cucumber","多宝鱼":"turbot","银鳕鱼":"cod",
"象拔蚌":"geoduck","石斑鱼":"grouper","皮皮虾":"mantis-shrimp",
"蛏子":"razor-clams","鲍鱼":"abalone","小龙虾":"crayfish",
"草鱼":"grass-carp","墨鱼仔":"cuttlefish","海蜇":"jellyfish",
"甲鱼":"turtle","秋刀鱼":"saury","鳕鱼排":"cod-fillet",
"海螺":"conch","鳊鱼":"bream","蟹肉棒":"crab-stick",
"黑鱼":"snakehead",
}

os.makedirs(IMG_DIR, exist_ok=True)

print("=" * 60)
print("  生鲜商城 - loremflickr 商品图下载")
print("=" * 60)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, name FROM products ORDER BY id")
products = cur.fetchall()
print(f"\n[1] DB: {len(products)} products")

# Delete old images
for f in os.listdir(IMG_DIR):
    if f.endswith(".jpg"):
        os.remove(os.path.join(IMG_DIR, f))

print("[2] Downloading from loremflickr.com...\n")

downloaded = 0
failed = 0
hashes_seen = set()

for idx, p in enumerate(products, 1):
    pid = p["id"]
    name = p["name"]
    keyword = KW.get(name, "fresh-food")
    
    fname = f"{keyword}-{pid}.jpg"
    path = os.path.join(IMG_DIR, fname)
    
    # Try primary keyword first, fallback to fresh food
    success = False
    for attempt_tag in range(2):
        if attempt_tag == 0:
            url = f"https://loremflickr.com/400/400/{keyword},food?lock={pid}"
        else:
            url = f"https://loremflickr.com/400/400/fresh-food,produce?lock={pid}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=15).read()
            
            if len(data) > 500:
                # Check for uniqueness: if duplicate hash, try different lock
                h = hashlib.md5(data).hexdigest()
                if h in hashes_seen:
                    # Try with a different lock value
                    for retry in range(3):
                        alt_lock = pid * 100 + retry * 7 + 31
                        alt_url = f"https://loremflickr.com/400/400/{keyword},food?lock={alt_lock}"
                        alt_req = urllib.request.Request(alt_url, headers={"User-Agent": "Mozilla/5.0"})
                        alt_data = urllib.request.urlopen(alt_req, timeout=10).read()
                        alt_h = hashlib.md5(alt_data).hexdigest()
                        if alt_h not in hashes_seen and len(alt_data) > 500:
                            data = alt_data
                            h = alt_h
                            break
                        time.sleep(0.3)
                
                with open(path, "wb") as f:
                    f.write(data)
                hashes_seen.add(h)
                tag = "food" if attempt_tag == 0 else "fallback"
                print(f"  [{idx:3d}] {name:10s} -> {tag} {fname} ({len(data)//1024}KB)")
                downloaded += 1
                success = True
                break
        except:
            if attempt_tag == 0:
                time.sleep(1)
    
    if not success:
        # Last resort: save a placeholder reference (NOT null)
        fallback_url = f"https://loremflickr.com/400/400/fresh-food,produce?lock={pid}"
        print(f"  [{idx:3d}] {name:10s} -> [remote] {fallback_url}")
        failed += 1
    
    time.sleep(0.3)  # Rate limiting delay

print(f"\n[3] Downloaded: {downloaded}, Failed: {failed}")

# Verify uniqueness
files = [f for f in os.listdir(IMG_DIR) if f.endswith(".jpg")]
hashes = set()
for f in files:
    h = hashlib.md5(open(os.path.join(IMG_DIR, f), "rb").read()).hexdigest()
    hashes.add(h)
print(f"  Files: {len(files)}, Unique: {len(hashes)}, Dups: {len(files)-len(hashes)}")

# Update database
print("\n[4] Updating database...")
for p in products:
    pid = p["id"]
    name = p["name"]
    keyword = KW.get(name, "fresh-food")
    fname = f"{keyword}-{pid}.jpg"
    path = os.path.join(IMG_DIR, fname)
    
    if os.path.exists(path) and os.path.getsize(path) > 500:
        local_url = f"/static/images/products/{fname}"
    else:
        local_url = f"https://loremflickr.com/400/400/{keyword},food?lock={pid}"
    
    cur.execute(
        "UPDATE products SET image_url = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
        (local_url, pid)
    )
conn.commit()

# Seed SQL sync
print("[5] Syncing seed_data.sql...")
cur.execute("SELECT name, image_url FROM products ORDER BY id")
urls = {r["name"]: r["image_url"] for r in cur.fetchall()}
conn.close()

with open(SEED_SQL, "r", encoding="utf-8") as f:
    content = f.read()

n = 0
lines = content.split("\n")
new_lines = []
for line in lines:
    nl = line
    for name, u in urls.items():
        if "'" + name + "'" in line:
            for p in [r"'https?://[^']*'", r"'/static/images/products/[^']*'"]:
                if re.search(p, nl):
                    nl = re.sub(p, "'" + u + "'", nl)
                    n += 1
                    break
            break
    new_lines.append(nl)

content = "\n".join(new_lines)
today = datetime.date.today().strftime("%Y-%m-%d")
content = re.sub(r"-- 图片来源：.*", f"-- 图片来源：loremflickr.com (Flickr 真实食品摄影) 最后更新：{today}", content)
content = re.sub(r"-- URL 格式：.*", "-- URL 格式：https://loremflickr.com/400/400/{keyword},food?lock={product_id}", content)
with open(SEED_SQL, "w", encoding="utf-8") as f:
    f.write(content)
print(f"  seed_data.sql: {n} products updated")

# Final summary
total_size = sum(os.path.getsize(os.path.join(IMG_DIR, f)) for f in files)
print(f"\n{'='*60}")
print(f"  Done!")
print(f"  Products:   {len(products)}")
print(f"  Files:      {len(files)}")
print(f"  Unique:     {len(hashes)}")
print(f"  Size:       {total_size//1024} KB")
print(f"  Flask:      http://localhost:5000/")
print(f"{'='*60}")