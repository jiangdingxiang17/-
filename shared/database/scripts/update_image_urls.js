/**
 * 在线生鲜商城 - 更新商品图片路径脚本
 * =====================================
 * 用途：将 seed_data.sql 和数据库中的 picsum.photos URL 替换为本地图片路径
 *
 * 使用方式：
 *   node update_image_urls.js
 *
 * 本地图片路径格式：
 *   /static/images/products/{keyword}.jpg
 *   例如：/static/images/products/tomato.jpg
 */

const fs = require('fs');
const path = require('path');

// ============================================================
// 配置
// ============================================================
const SCRIPT_DIR = __dirname;
const PROJECT_ROOT = path.resolve(SCRIPT_DIR, '..', '..', '..');
const SEED_SQL_PATH = path.resolve(PROJECT_ROOT, 'shared', 'database', 'dml', 'seed_data.sql');
const DB_PATH = path.resolve(PROJECT_ROOT, 'fresh_market.db');
const IMAGE_DIR = path.resolve(PROJECT_ROOT, 'shared', 'backend', 'static', 'images', 'products');

// ============================================================
// 关键词映射（中文商品名 → 本地文件名）
// ============================================================
const KEYWORD_MAP = {
  '西红柿':     'tomato.jpg',
  '黄瓜':       'cucumber.jpg',
  '菠菜':       'spinach.jpg',
  '土豆':       'potato.jpg',
  '大白菜':     'napa-cabbage.jpg',
  '生菜':       'lettuce.jpg',
  '胡萝卜':     'carrot.jpg',
  '西兰花':     'broccoli.jpg',
  '芹菜':       'celery.jpg',
  '青椒':       'green-pepper.jpg',
  '茄子':       'eggplant.jpg',
  '豆角':       'green-beans.jpg',
  '南瓜':       'pumpkin.jpg',
  '甜玉米':     'sweet-corn.jpg',
  '韭菜':       'chinese-chives.jpg',
  '洋葱':       'onion.jpg',
  '冬瓜':       'winter-melon.jpg',
  '莲藕':       'lotus-root.jpg',
 '山药':       'chinese-yam.jpg',
  '苦瓜':       'bitter-gourd.jpg',
  '蒜苗':       'garlic-sprouts.jpg',
  '红薯':       'sweet-potato.jpg',
  '丝瓜':       'luffa-gourd.jpg',
  '秋葵':       'okra.jpg',
  '空心菜':     'water-spinach.jpg',
  '白萝卜':     'daikon-radish.jpg',
  '莴笋':       'celtuce-stem.jpg',
  '花菜':       'cauliflower.jpg',
  '茼蒿':       'crown-daisy.jpg',
  '娃娃菜':     'baby-cabbage.jpg',
  '红富士苹果':   'fuji-apple.jpg',
  '香蕉':         'banana.jpg',
  '阳光玫瑰葡萄': 'shine-muscat-grapes.jpg',
  '海南金钻菠萝': 'golden-pineapple.jpg',
  '丹东草莓':     'strawberry.jpg',
  '海南芒果':     'mango.jpg',
  '麒麟西瓜':     'watermelon.jpg',
  '赣南脐橙':     'navel-orange.jpg',
  '徐香猕猴桃':   'kiwifruit.jpg',
  '智利车厘子':   'cherry.jpg',
  '妃子笑荔枝':   'lychee.jpg',
  '红心火龙果':   'dragon-fruit.jpg',
  '秘鲁蓝莓':     'blueberry.jpg',
  '文旦柚':       'pomelo.jpg',
  '阳山水蜜桃':   'peach.jpg',
  '新疆哈密瓜':   'hami-melon.jpg',
  '龙眼':         'longan.jpg',
  '山竹':         'mangosteen.jpg',
  '阿克苏苹果':   'apple.jpg',
  '突尼斯软籽石榴': 'pomegranate.jpg',
  '海南椰子':     'coconut.jpg',
  '金枕榴莲':     'durian.jpg',
  '樱桃番茄':     'cherry-tomato.jpg',
  '红提':         'red-grapes.jpg',
  '库尔勒香梨':   'pear.jpg',
  '百香果':       'passion-fruit.jpg',
  '砂糖橘':       'mandarin-orange.jpg',
  '释迦果':       'sugar-apple.jpg',
  '杨梅':         'bayberry.jpg',
  '青提':         'green-grapes.jpg',
  '澳洲无籽红提': 'red-seedless-grapes.jpg',
  '柠檬':         'lemon.jpg',
  '黑猪五花肉':   'raw-pork-belly.jpg',
  '散养土鸡':     'whole-raw-chicken.jpg',
  '安格斯牛排':   'raw-beef-steak.jpg',
  '猪里脊肉':     'raw-pork-tenderloin.jpg',
  '澳洲牛腩':     'raw-beef-brisket.jpg',
  '羊腿肉':       'raw-lamb-leg.jpg',
  '鸡胸肉':       'raw-chicken-breast.jpg',
  '半片鸭':       'raw-duck.jpg',
  '猪小排':       'raw-pork-ribs.jpg',
  '金钱腱':       'raw-beef-shank.jpg',
  '鸡翅中':       'raw-chicken-wings.jpg',
  '猪肉馅':       'ground-pork.jpg',
  '金华火腿':     'cured-ham.jpg',
  '牛腱子':       'raw-beef-shank.jpg',
  '猪蹄':         'raw-pork-trotter.jpg',
  '鸡腿':         'raw-chicken-drumstick.jpg',
  '羊排':         'raw-lamb-rack.jpg',
  '牛尾':         'raw-oxtail.jpg',
  '鸭胸肉':       'raw-duck-breast.jpg',
  '猪肉片':       'raw-pork-slice.jpg',
  '鸡爪':         'raw-chicken-feet.jpg',
  '牛百叶':       'beef-omasum-tripe.jpg',
  '猪肝':         'raw-pork-liver.jpg',
  '肥牛卷':       'raw-beef-slice.jpg',
  '乌鸡':         'raw-silkie-chicken.jpg',
  '牛里脊':       'raw-beef-tenderloin.jpg',
  '培根':         'raw-bacon-strips.jpg',
  '猪大肠':       'raw-pork-intestine.jpg',
  '腊肉':         'chinese-cured-pork-belly.jpg',
  '牛肉馅':       'ground-beef.jpg',
  '鸽子':         'raw-pigeon-squab.jpg',
  '鸡胗':         'raw-chicken-gizzard.jpg',
  '活鲫鱼':       'raw-crucian-carp.jpg',
  '三文鱼刺身':   'raw-salmon-fillet.jpg',
  '北极甜虾':     'raw-shrimp.jpg',
  '东海带鱼':     'raw-hairtail-fish.jpg',
  '黄花鱼':       'raw-yellow-croaker.jpg',
  '海鲈鱼':       'raw-sea-bass.jpg',
  '基围虾':       'fresh-shrimp.jpg',
  '乳山生蚝':     'raw-oyster.jpg',
  '扇贝':         'raw-scallop.jpg',
  '鱿鱼':         'raw-squid.jpg',
  '金鲳鱼':       'raw-pomfret-fish.jpg',
  '花蛤':         'raw-clams.jpg',
  '大连海参':     'dried-sea-cucumber.jpg',
  '多宝鱼':       'raw-turbot-fish.jpg',
  '银鳕鱼':       'raw-cod-fillet.jpg',
  '象拔蚌':       'raw-geoduck-clam.jpg',
  '石斑鱼':       'raw-grouper-fish.jpg',
  '皮皮虾':       'raw-mantis-shrimp.jpg',
  '蛏子':         'raw-razor-clams.jpg',
  '鲍鱼':         'raw-abalone.jpg',
  '小龙虾':       'raw-crayfish.jpg',
  '草鱼':         'raw-grass-carp.jpg',
  '墨鱼仔':       'raw-baby-cuttlefish.jpg',
  '海蜇':         'jellyfish-seafood.jpg',
  '甲鱼':         'raw-softshell-turtle.jpg',
  '秋刀鱼':       'raw-saury-fish.jpg',
  '鳕鱼排':       'cod-fillet.jpg',
  '海螺':         'raw-conch-seashell.jpg',
  '鳊鱼':         'raw-bream-fish.jpg',
  '蟹肉棒':       'crab-stick-seafood.jpg',
  '黑鱼':         'raw-snakehead-fish.jpg',
};

// ============================================================
// 1. 更新 seed_data.sql
// ============================================================
function updateSeedSQL(filePath) {
  console.log('[1/3] 更新 seed_data.sql ...');
  if (!fs.existsSync(filePath)) {
    console.log(`  [错误] 文件不存在: ${filePath}`);
    return false;
  }
  let content = fs.readFileSync(filePath, 'utf-8');
  let updatedCount = 0;
  const lines = content.split('\n');
  const newLines = lines.map(line => {
    let newLine = line;
    for (const [name, filename] of Object.entries(KEYWORD_MAP)) {
      if (line.includes(`'${name}'`)) {
        const localUrl = `/static/images/products/${filename}`;
        const urlRegex = /'https?:\/\/[^']*picsum\.photos[^']*'/;
        if (urlRegex.test(newLine)) {
          newLine = newLine.replace(urlRegex, `'${localUrl}'`);
          updatedCount++;
          break;
        }
      }
    }
    return newLine;
  });
  content = newLines.join('\n');
  content = content.replace(
    /图片来源：.*(\r?\n)/,
    (m, nl) => `图片来源：本地图片 (picsum.photos Unsplash 摄影作品)${nl}`
  );
  content = content.replace(
    /URL 格式：.*(\r?\n)/,
    (m, nl) => `URL 格式：/static/images/products/{keyword.jpg}${nl}`
  );
  fs.writeFileSync(filePath, content, 'utf-8');
  console.log(`  ✓ 已更新 ${updatedCount} 个商品的图片路径`);
  return true;
}

// ============================================================
// 2. 更新数据库（生成 SQL 脚本）
// ============================================================
function updateDatabase() {
  console.log('[2/3] 更新数据库 ...');
  if (!fs.existsSync(DB_PATH)) {
    console.log(`  [跳过] 数据库文件不存在: ${DB_PATH}`);
    return true;
  }
  const updateStatements = [];
  for (const [name, filename] of Object.entries(KEYWORD_MAP)) {
    const localUrl = `/static/images/products/${filename}`;
    const escapedName = name.replace(/'/g, "''");
    updateStatements.push(
      `UPDATE products SET image_url = '${localUrl}' WHERE name = '${escapedName}';`
    );
  }
  const sqlScript = updateStatements.join('\n');
  const sqlScriptPath = path.join(SCRIPT_DIR, 'update_image_urls.sql');
  fs.writeFileSync(sqlScriptPath, sqlScript, 'utf-8');
  console.log(`  ✓ SQL 更新脚本已生成: ${sqlScriptPath}`);
  console.log('  [提示] 要更新现有数据库，请运行:');
  console.log('    python -c "import sqlite3; conn=sqlite3.connect(\\'DB_PATH\\');');
  console.log('    [s.split(\'; \') for s in open(\\'update_image_urls.sql\\').read().strip().split(\\';\\')];');
  console.log('    conn.commit(); conn.close()"');
  return true;
}

// ============================================================
// 3. 验证图片文件
// ============================================================
function verifyImages() {
  console.log('[3/3] 验证图片文件 ...');
  if (!fs.existsSync(IMAGE_DIR)) {
    console.log(`  [错误] 图片目录不存在: ${IMAGE_DIR}`);
    return false;
  }
  const files = fs.readdirSync(IMAGE_DIR).filter(f => f.endsWith('.jpg'));
  const expectedFiles = new Set(Object.values(KEYWORD_MAP));
  const presentFiles = new Set(files);
  const missing = [...expectedFiles].filter(f => !presentFiles.has(f));
  let totalSize = 0;
  for (const f of files) {
    try { totalSize += fs.statSync(path.join(IMAGE_DIR, f)).size; } catch(e) {}
  }
  console.log(`  图片总数: ${files.length} 张（${(totalSize/1024/1024).toFixed(1)} MB）`);
  console.log(`  期望商品: ${expectedFiles.size} 个（含1个共享图片）`);
  if (missing.length > 0) {
    console.log(`  [警告] 缺少 ${missing.length} 个文件`);
  } else {
    console.log('  ✓ 所有商品图片均可用');
  }
  return true;
}

// ============================================================
// 主流程
// ============================================================
function main() {
  console.log('='.repeat(65));
  console.log('  在线生鲜商城 - 更新商品图片路径');
  console.log('='.repeat(65));
  updateSeedSQL(SEED_SQL_PATH);
  updateDatabase();
  verifyImages();
  console.log('\n' + '='.repeat(65));
  console.log('  完成！');
  console.log('\n  后续步骤:');
  console.log('  1. 安装 Python 后运行:');
  console.log('     cd D:\\2026暑期实训\\agenticteam');
  console.log('     python import_data.py');
  console.log('\n  2. 或者启动应用:');
  console.log('     cd shared/backend');
  console.log('     python app.py');
  console.log('\n  3. 访问:');
  console.log('     http://localhost:5000');
  console.log('     管理员: admin / admin123');
  console.log('     用户:   user1 / 123456');
  console.log('='.repeat(65));
}
main();
