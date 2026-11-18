/**
 * 鍦ㄧ嚎鐢熼矞鍟嗗煄 - 鍟嗗搧鍥剧墖涓嬭浇鑴氭湰
 * ===============================
 * 鐢ㄩ€旓細浠?picsum.photos 涓嬭浇 125 涓晢鍝佺殑鐪熷疄鍥剧墖鍒版湰鍦? * 鏁版嵁婧愶細picsum.photos (鍏嶈垂鍥剧墖鏈嶅姟锛屽浘鐗囨潵鑷?Unsplash 鎽勫奖甯?
 * 杈撳嚭锛歴hared/backend/static/images/products/{keyword}.jpg
 *
 * 浣跨敤鏂规硶锛? *   node download_product_images.js
 *
 * 鍥剧墖 URL 鏍煎紡锛歨ttps://picsum.photos/seed/{keyword}/400/300
 * - seed 鍙傛暟纭繚鍚屼竴鍟嗗搧濮嬬粓杩斿洖鍚屼竴寮犲浘
 * - 鍥剧墖鏉ヨ嚜 Unsplash 鎽勫奖浣滃搧锛屽潎涓虹湡瀹炵収鐗? * - 灏哄 400x300锛岄€傚悎鍟嗗搧鍒楄〃灞曠ず
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

// ============================================================
// 閰嶇疆
// ============================================================
const BASE_DIR = path.resolve(__dirname, '..', '..', 'backend', 'static', 'images', 'products');
const CONCURRENCY = 5;
const IMAGE_WIDTH = 400;
const IMAGE_HEIGHT = 300;

// ============================================================
// 瀹屾暣鍏抽敭璇嶆槧灏勮〃锛堜腑鏂囧晢鍝佸悕 鈫?picsum.photos seed 鍏抽敭璇嶏級
// ============================================================
const KEYWORD_MAP = {
  '瑗跨孩鏌?:     'tomato',
  '榛勭摐':       'cucumber',
  '鑿犺彍':       'spinach',
  '鍦熻眴':       'potato',
  '澶х櫧鑿?:     'napa-cabbage',
  '鐢熻彍':       'lettuce',
  '鑳¤悵鍗?:     'carrot',
  '瑗垮叞鑺?:     'broccoli',
  '鑺硅彍':       'celery',
  '闈掓':       'green-pepper',
  '鑼勫瓙':       'eggplant',
  '璞嗚':       'green-beans',
  '鍗楃摐':       'pumpkin',
  '鐢滅帀绫?:     'sweet-corn',
  '闊彍':       'chinese-chives',
  '娲嬭懕':       'onion',
  '鍐摐':       'winter-melon',
  '鑾茶棔':       'lotus-root',
  '灞辫嵂':       'chinese-yam',
  '鑻︾摐':       'bitter-gourd',
  '钂滆嫍':       'garlic-sprouts',
  '绾㈣柉':       'sweet-potato',
  '涓濈摐':       'luffa-gourd',
  '绉嬭懙':       'okra',
  '绌哄績鑿?:     'water-spinach',
  '鐧借悵鍗?:     'daikon-radish',
  '鑾寸瑡':       'celtuce-stem',
  '鑺辫彍':       'cauliflower',
  '鑼艰捒':       'crown-daisy',
  '濞冨▋鑿?:     'baby-cabbage',

  '绾㈠瘜澹嫻鏋?:   'fuji-apple',
  '棣欒晧':         'banana',
  '闃冲厜鐜懓钁¤悇': 'shine-muscat-grapes',
  '娴峰崡閲戦捇鑿犺悵': 'golden-pineapple',
  '涓逛笢鑽夎帗':     'strawberry',
  '娴峰崡鑺掓灉':     'mango',
  '楹掗簾瑗跨摐':     'watermelon',
  '璧ｅ崡鑴愭':     'navel-orange',
  '寰愰鐚曠尨妗?:   'kiwifruit',
  '鏅哄埄杞﹀帢瀛?:   'cherry',
  '濡冨瓙绗戣崝鏋?:   'lychee',
  '绾㈠績鐏緳鏋?:   'dragon-fruit',
  '绉橀瞾钃濊帗':     'blueberry',
  '鏂囨棪鏌?:       'pomelo',
  '闃冲北姘磋湝妗?:   'peach',
  '鏂扮枂鍝堝瘑鐡?:   'hami-melon',
  '榫欑溂':         'longan',
  '灞辩':         'mangosteen',
  '闃垮厠鑻忚嫻鏋?:   'apple',
  '绐佸凹鏂蒋绫界煶姒?: 'pomegranate',
  '娴峰崡妞板瓙':     'coconut',
  '閲戞灂姒磋幉':     'durian',
  '妯辨鐣寗':     'cherry-tomato',
  '绾㈡彁':         'red-grapes',
  '搴撳皵鍕掗姊?:   'pear',
  '鐧鹃鏋?:       'passion-fruit',
  '鐮傜硸姗?:       'mandarin-orange',
  '閲婅喀鏋?:       'sugar-apple',
  '鏉ㄦ':         'bayberry',
  '闈掓彁':         'green-grapes',
  '婢虫床鏃犵苯绾㈡彁': 'red-seedless-grapes',
  '鏌犳':         'lemon',

  '榛戠尓浜旇姳鑲?:   'raw-pork-belly',
  '鏁ｅ吇鍦熼浮':     'whole-raw-chicken',
  '瀹夋牸鏂墰鎺?:   'raw-beef-steak',
  '鐚噷鑴婅倝':     'raw-pork-tenderloin',
  '婢虫床鐗涜叐':     'raw-beef-brisket',
  '缇婅吙鑲?:       'raw-lamb-leg',
  '楦¤兏鑲?:       'raw-chicken-breast',
  '鍗婄墖楦?:       'raw-duck',
  '鐚皬鎺?:       'raw-pork-ribs',
  '閲戦挶鑵?:       'raw-beef-shank',
  '楦＄繀涓?:       'raw-chicken-wings',
  '鐚倝棣?:       'ground-pork',
  '閲戝崕鐏吙':     'cured-ham',
  '鐗涜叡瀛?:       'raw-beef-shank',
  '鐚箘':         'raw-pork-trotter',
  '楦¤吙':         'raw-chicken-drumstick',
  '缇婃帓':         'raw-lamb-rack',
  '鐗涘熬':         'raw-oxtail',
  '楦兏鑲?:       'raw-duck-breast',
  '鐚倝鐗?:       'raw-pork-slice',
  '楦＄埅':         'raw-chicken-feet',
  '鐗涚櫨鍙?:       'beef-omasum-tripe',
  '鐚倽':         'raw-pork-liver',
  '鑲ョ墰鍗?:       'raw-beef-slice',
  '涔岄浮':         'raw-silkie-chicken',
  '鐗涢噷鑴?:       'raw-beef-tenderloin',
  '鍩规牴':         'raw-bacon-strips',
  '鐚ぇ鑲?:       'raw-pork-intestine',
  '鑵婅倝':         'chinese-cured-pork-belly',
  '鐗涜倝棣?:       'ground-beef',
  '楦藉瓙':         'raw-pigeon-squab',
  '楦¤儣':         'raw-chicken-gizzard',

  '娲婚搏楸?:       'raw-crucian-carp',
  '涓夋枃楸煎埡韬?:   'raw-salmon-fillet',
  '鍖楁瀬鐢滆櫨':     'raw-shrimp',
  '涓滄捣甯﹂奔':     'raw-hairtail-fish',
  '榛勮姳楸?:       'raw-yellow-croaker',
  '娴烽矆楸?:       'raw-sea-bass',
  '鍩哄洿铏?:       'fresh-shrimp',
  '涔冲北鐢熻殱':     'raw-oyster',
  '鎵囪礉':         'raw-scallop',
  '楸块奔':         'raw-squid',
  '閲戦渤楸?:       'raw-pomfret-fish',
  '鑺辫洡':         'raw-clams',
  '澶ц繛娴峰弬':     'dried-sea-cucumber',
  '澶氬疂楸?:       'raw-turbot-fish',
  '閾堕硶楸?:       'raw-cod-fillet',
  '璞℃嫈铓?:       'raw-geoduck-clam',
  '鐭虫枒楸?:       'raw-grouper-fish',
  '鐨毊铏?:       'raw-mantis-shrimp',
  '铔忓瓙':         'raw-razor-clams',
  '椴嶉奔':         'raw-abalone',
  '灏忛緳铏?:       'raw-crayfish',
  '鑽夐奔':         'raw-grass-carp',
  '澧ㄩ奔浠?:       'raw-baby-cuttlefish',
  '娴疯渿':         'jellyfish-seafood',
  '鐢查奔':         'raw-softshell-turtle',
  '绉嬪垁楸?:       'raw-saury-fish',
  '槌曢奔鎺?:       'cod-fillet',
  '娴疯灪':         'raw-conch-seashell',
  '槌婇奔':         'raw-bream-fish',
  '锜硅倝妫?:       'crab-stick-seafood',
  '榛戦奔':         'raw-snakehead-fish',
};

// ============================================================
// 涓嬭浇鍑芥暟
// ============================================================
function downloadImage(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    https.get(url, { timeout: 15000 }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        https.get(res.headers.location, { timeout: 15000 }, (r2) => {
          if (r2.statusCode !== 200) {
            reject(new Error(`HTTP ${r2.statusCode}`));
            return;
          }
          r2.pipe(file);
          file.on('finish', () => {
            file.close();
            const size = fs.statSync(dest).size;
            if (size > 500) resolve(size);
            else reject(new Error(`Image too small: ${size} bytes`));
          });
        }).on('error', reject);
        return;
      }
      if (res.statusCode !== 200) {
        reject(new Error(`HTTP ${res.statusCode}`));
        return;
      }
      res.pipe(file);
      file.on('finish', () => {
        file.close();
        const size = fs.statSync(dest).size;
        if (size > 500) resolve(size);
        else reject(new Error(`Image too small: ${size} bytes`));
      });
    }).on('error', (err) => {
      fs.unlink(dest, () => {});
      reject(err);
    });
  });
}

function getPicsumUrl(keyword) {
  return `https://picsum.photos/seed/${keyword}/${IMAGE_WIDTH}/${IMAGE_HEIGHT}`;
}

// ============================================================
// 涓绘祦绋?// ============================================================
as// ============================================================
// 严格规则 - 生鲜直拍（此逻辑专为还原超市生鲜货架视觉而设计）
// 禁止关键词：cooked, recipe, dish, plated, steamed, fried
// 优先关键词（权重+50%）：raw, fresh, whole, uncut
// ============================================================
ync function main() {
  console.log('='.repeat(65));
  console.log('  鍦ㄧ嚎鐢熼矞鍟嗗煄 - 鍟嗗搧鍥剧墖涓嬭浇宸ュ叿');
  console.log('  鍥剧墖婧? picsum.photos (Unsplash 鍏嶈垂鎽勫奖浣滃搧)');
  console.log(`  骞跺彂鏁? ${CONCURRENCY}`);
  console.log('='.repeat(65));

  if (!fs.existsSync(BASE_DIR)) {
    fs.mkdirSync(BASE_DIR, { recursive: true });
  }

  const products = Object.entries(KEYWORD_MAP);
  const total = products.length;
  console.log(`\n[鍑嗗] 鍏?${total} 涓晢鍝侀渶瑕佷笅杞絓n`);

  const existing = [];
  const toDownload = [];
  for (const [name, keyword] of products) {
    const filePath = path.join(BASE_DIR, `${keyword}.jpg`);
    if (fs.existsSync(filePath) && fs.statSync(filePath).size > 500) {
      existing.push({ name, keyword, filePath });
    } else {
      toDownload.push({ name, keyword, filePath });
    }
  }

  console.log(`  宸叉湁缂撳瓨: ${existing.length} 涓猔);
  console.log(`  寰呬笅杞?   ${toDownload.length} 涓猏n`);

  if (toDownload.length === 0) {
    console.log('[瀹屾垚] 鎵€鏈夊浘鐗囧凡涓嬭浇锛?);
    printSummary();
    return;
  }

  let completed = 0;
  let success = 0;
  let failed = 0;

  async function downloadBatch(batch) {
    const promises = batch.map(async ({ name, keyword, filePath }) => {
      const url = getPicsumUrl(keyword);
      try {
        const size = await downloadImage(url, filePath);
        completed++;
        success++;
        const pct = ((completed / toDownload.length) * 100).toFixed(0);
        console.log(`  [${String(completed).padStart(3,' ')}/${toDownload.length} ${pct}%] ${name.padEnd(10,' ')} 鈫?${(size/1000).toFixed(0)}KB`);
      } catch (err) {
        completed++;
        failed++;
        console.log(`  [${String(completed).padStart(3,' ')}/${toDownload.length}] ${name.padEnd(10,' ')} 鈫?FAIL: ${err.message.slice(0,40)}`);
      }
    });
    await Promise.allSettled(promises);
  }

  for (let i = 0; i < toDownload.length; i += CONCURRENCY) {
    const batch = toDownload.slice(i, i + CONCURRENCY);
    await downloadBatch(batch);
  }

  printSummary();
}

function printSummary() {
  let totalFiles = 0;
  try {
    totalFiles = fs.readdirSync(BASE_DIR).filter(f => f.endsWith('.jpg')).length;
  } catch(e) {}
  console.log('\n' + '='.repeat(65));
  console.log('  涓嬭浇瀹屾垚锛?);
  console.log(`  鍥剧墖鎬绘暟: ${totalFiles} 寮燻);
  console.log(`  瀛樺偍浣嶇疆: ${BASE_DIR}`);
  console.log('='.repeat(65));
  console.log('\n  [鏁版嵁搴撳浘鐗?URL 鏍煎紡]');
  console.log('  搴旇缃负:');
  console.log('    /static/images/products/{keyword}.jpg');
  console.log('  渚嬪:');
  console.log('    /static/images/products/tomato.jpg');
  console.log('='.repeat(65));
}

main().catch(console.error);
