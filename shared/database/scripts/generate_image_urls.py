"""
鍦ㄧ嚎鐢熼矞鍟嗗煄 - 鍟嗗搧鍥剧墖 URL 鐢熸垚鑴氭湰
======================================
鐢ㄩ€旓細璇诲彇 seed_data.sql锛屾牴鎹叧閿瘝鏄犲皠琛ㄤ负姣忎釜鍟嗗搧鐢熸垚鏂扮殑 Picsum 鍥剧墖 URL銆?
      source.unsplash.com 宸蹭簬 2024骞?鏈堝叧闂紝杩佺Щ鑷?Picsum (picsum.photos)銆?

URL 鐢熸垚瑙勫垯锛?
  - 鎵€鏈夊晢鍝侊細https://picsum.photos/seed/{first-keyword}/400/300
  - Picsum seed 纭繚鍚屼竴鍟嗗搧濮嬬粓杩斿洖鍚屼竴寮犲浘鐗?
  - Picsum 鍥炬簮鏉ヨ嚜 Unsplash 鎽勫奖甯堜綔鍝侀泦锛岃川閲忓彲闈?
"""

import re
import os

# ============================================================
KEYWORD_MAP = {
    # === 钄彍锛?0涓級===
    '瑗跨孩鏌?:     'tomato,fresh-vegetable',
    '榛勭摐':       'cucumber,fresh-vegetable',
    '鑿犺彍':       'spinach,fresh-leaves',
    '鍦熻眴':       'potato,raw',
    '澶х櫧鑿?:     'napa-cabbage,fresh',
    '鐢熻彍':       'lettuce,fresh-leaves',
    '鑳¤悵鍗?:     'carrot,fresh-vegetable',
    '瑗垮叞鑺?:     'broccoli,fresh',
    '鑺硅彍':       'celery,fresh-vegetable',
    '闈掓':       'green-pepper,fresh-vegetable',
    '鑼勫瓙':       'eggplant,fresh-vegetable',
    '璞嗚':       'green-beans,fresh-vegetable',
    '鍗楃摐':       'pumpkin,raw',
    '鐢滅帀绫?:     'sweet-corn,fresh-vegetable',
    '闊彍':       'chinese-chives,fresh-herb',
    '娲嬭懕':       'onion,raw-vegetable',
    '鍐摐':       'winter-melon,fresh',
    '鑾茶棔':       'lotus-root,fresh-vegetable',
    '灞辫嵂':       'chinese-yam,raw-vegetable',
    '鑻︾摐':       'bitter-gourd,fresh-vegetable',
    '钂滆嫍':       'garlic-sprouts,fresh',
    '绾㈣柉':       'sweet-potato,raw',
    '涓濈摐':       'luffa-gourd,fresh-vegetable',
    '绉嬭懙':       'okra,fresh-vegetable',
    '绌哄績鑿?:     'water-spinach,fresh-leaves',
    '鐧借悵鍗?:     'daikon-radish,fresh-vegetable',
    '鑾寸瑡':       'celtuce-stem,fresh-vegetable',
    '鑺辫彍':       'cauliflower,fresh-vegetable',
    '鑼艰捒':       'crown-daisy,fresh-leaves',
    '濞冨▋鑿?:     'baby-cabbage,fresh-vegetable',

    # === 姘存灉锛?2涓級===
    '绾㈠瘜澹嫻鏋?:   'fuji-apple,fresh-fruit',
    '棣欒晧':         'banana,fresh-fruit',
    '闃冲厜鐜懓钁¤悇': 'shine-muscat-grapes,fresh-fruit',
    '娴峰崡閲戦捇鑿犺悵': 'golden-pineapple,fresh-fruit',
    '涓逛笢鑽夎帗':     'strawberry,fresh-fruit',
    '娴峰崡鑺掓灉':     'mango,fresh-fruit',
    '楹掗簾瑗跨摐':     'watermelon,fresh-fruit',
    '璧ｅ崡鑴愭':     'navel-orange,fresh-fruit',
    '寰愰鐚曠尨妗?:   'kiwifruit,fresh-fruit',
    '鏅哄埄杞﹀帢瀛?:   'cherry,fresh-fruit',
    '濡冨瓙绗戣崝鏋?:   'lychee,fresh-fruit',
    '绾㈠績鐏緳鏋?:   'dragon-fruit,fresh-fruit',
    '绉橀瞾钃濊帗':     'blueberry,fresh-fruit',
    '鏂囨棪鏌?:       'pomelo,fresh-fruit',
    '闃冲北姘磋湝妗?:   'peach,fresh-fruit',
    '鏂扮枂鍝堝瘑鐡?:   'hami-melon,fresh-fruit',
    '榫欑溂':         'longan,fresh-fruit',
    '灞辩':         'mangosteen,fresh-fruit',
    '闃垮厠鑻忚嫻鏋?:   'apple,fresh-fruit',
    '绐佸凹鏂蒋绫界煶姒?: 'pomegranate,fresh-fruit',
    '娴峰崡妞板瓙':     'coconut,fresh-fruit',
    '閲戞灂姒磋幉':     'durian,fresh-fruit',
    '妯辨鐣寗':     'cherry-tomato,fresh-fruit',
    '绾㈡彁':         'red-grapes,fresh-fruit',
    '搴撳皵鍕掗姊?:   'pear,fresh-fruit',
    '鐧鹃鏋?:       'passion-fruit,fresh-fruit',
    '鐮傜硸姗?:       'mandarin-orange,fresh-fruit',
    '閲婅喀鏋?:       'sugar-apple,fresh-fruit',
    '鏉ㄦ':         'bayberry,fresh-fruit',
    '闈掓彁':         'green-grapes,fresh-fruit',
    '婢虫床鏃犵苯绾㈡彁': 'red-seedless-grapes,fresh-fruit',
    '鏌犳':         'lemon,fresh-fruit',

    # === 鑲夌被锛?2涓級===  -- raw,uncooked 闃叉杩斿洖鑿滃搧鍥?
    '榛戠尓浜旇姳鑲?:   'raw-pork-belly,uncooked-meat',
    '鏁ｅ吇鍦熼浮':     'whole-raw-chicken,uncooked',
    '瀹夋牸鏂墰鎺?:   'raw-beef-steak,uncooked-meat',
    '鐚噷鑴婅倝':     'raw-pork-tenderloin,uncooked',
    '婢虫床鐗涜叐':     'raw-beef-brisket,uncooked-meat',
    '缇婅吙鑲?:       'raw-lamb-leg,uncooked-meat',
    '楦¤兏鑲?:       'raw-chicken-breast,uncooked',
    '鍗婄墖楦?:       'raw-duck,uncooked-meat',
    '鐚皬鎺?:       'raw-pork-ribs,uncooked',
    '閲戦挶鑵?:       'raw-beef-shank,uncooked-meat',
    '楦＄繀涓?:       'raw-chicken-wings,uncooked',
    '鐚倝棣?:       'ground-pork,raw-meat',
    '閲戝崕鐏吙':     'cured-ham,preserved-meat',
    '鐗涜叡瀛?:       'raw-beef-shank,uncooked-meat',
    '鐚箘':         'raw-pork-trotter,uncooked',
    '楦¤吙':         'raw-chicken-drumstick,uncooked',
    '缇婃帓':         'raw-lamb-rack,uncooked-meat',
    '鐗涘熬':         'raw-oxtail,uncooked-meat',
    '楦兏鑲?:       'raw-duck-breast,uncooked-meat',
    '鐚倝鐗?:       'raw-pork-slice,uncooked',
    '楦＄埅':         'raw-chicken-feet,uncooked',
    '鐗涚櫨鍙?:       'beef-omasum-tripe,raw',
    '鐚倽':         'raw-pork-liver,uncooked',
    '鑲ョ墰鍗?:       'raw-beef-slice,uncooked-meat',
    '涔岄浮':         'raw-silkie-chicken,uncooked',
    '鐗涢噷鑴?:       'raw-beef-tenderloin,uncooked',
    '鍩规牴':         'raw-bacon-strips',
    '鐚ぇ鑲?:       'raw-pork-intestine,uncooked',
    '鑵婅倝':         'chinese-cured-pork-belly',
    '鐗涜倝棣?:       'ground-beef,raw-meat',
    '楦藉瓙':         'raw-pigeon-squab,uncooked',
    '楦¤儣':         'raw-chicken-gizzard,uncooked',

    # === 楸肩被/娴烽矞锛?1涓級===  -- raw,uncooked,fresh-seafood
    '娲婚搏楸?:       'raw-crucian-carp,fresh-fish',
    '涓夋枃楸煎埡韬?:   'raw-salmon-fillet,fresh-seafood',
    '鍖楁瀬鐢滆櫨':     'raw-shrimp,uncooked-seafood',
    '涓滄捣甯﹂奔':     'raw-hairtail-fish,fresh-seafood',
    '榛勮姳楸?:       'raw-yellow-croaker,fresh-fish',
    '娴烽矆楸?:       'raw-sea-bass,fresh-fish',
    '鍩哄洿铏?:       'raw-shrimp,uncooked-seafood,fresh',
    '涔冲北鐢熻殱':     'raw-oyster,fresh-seafood',
    '鎵囪礉':         'raw-scallop,fresh-seafood',
    '楸块奔':         'raw-squid,uncooked-seafood',
    '閲戦渤楸?:       'raw-pomfret-fish,fresh-seafood',
    '鑺辫洡':         'raw-clams,fresh-seafood',
    '澶ц繛娴峰弬':     'dried-sea-cucumber,seafood',
    '澶氬疂楸?:       'raw-turbot-fish,fresh-seafood',
    '閾堕硶楸?:       'raw-cod-fillet,fresh-seafood',
    '璞℃嫈铓?:       'raw-geoduck-clam,fresh-seafood',
    '鐭虫枒楸?:       'raw-grouper-fish,fresh-seafood',
    '鐨毊铏?:       'raw-mantis-shrimp,uncooked-seafood',
    '铔忓瓙':         'raw-razor-clams,fresh-seafood',
    '椴嶉奔':         'raw-abalone,fresh-seafood',
    '灏忛緳铏?:       'raw-crayfish,uncooked-seafood',
    '鑽夐奔':         'raw-grass-carp,fresh-fish',
    '澧ㄩ奔浠?:       'raw-baby-cuttlefish,seafood',
    '娴疯渿':         'jellyfish-seafood,raw',
    '鐢查奔':         'raw-softshell-turtle,fresh',
    '绉嬪垁楸?:       'raw-saury-fish,fresh-seafood',
    '槌曢奔鎺?:       'raw-cod-fillet,fresh-seafood',
    '娴疯灪':         'raw-conch-seashell,fresh-seafood',
    '槌婇奔':         'raw-bream-fish,fresh',
    '锜硅倝妫?:       'crab-stick-seafood',
    '榛戦奔':         'raw-snakehead-fish,fresh',
}

# 鍒嗙被鍚庣紑瑙勫垯
VEGETABLE_FRUIT_CATEGORIES = {'钄彍', '姘存灉'}
MEAT_SEAFOOD_CATEGORIES = {'鑲夌被', '楸肩被'}


def generate_url(name, category):
    """
    鏍规嵁鍟嗗搧鍚嶅拰鍒嗙被鐢熸垚鏂扮殑 image_url銆?
    浣跨敤 Picsum seeded URL锛屽悓涓€ seed 濮嬬粓杩斿洖鍚屼竴寮犲浘鐗囷細
      https://picsum.photos/seed/{first-keyword}/400/300
    """
    kw = KEYWORD_MAP.get(name)
    if not kw:
        print(f'  [璀﹀憡] 鏈壘鍒板叧閿瘝鏄犲皠: {name}锛屼娇鐢ㄥ晢鍝佸悕浣滀负鍏抽敭璇?)
        seed = name
    else:
        # 鍙栫涓€涓嫳鏂囧叧閿瘝浣滀负 seed
        seed = kw.split(',')[0]

    url = f"https://picsum.photos/seed/{seed}/400/300"
    return url


def parse_seed_data(filepath):
    """
    瑙ｆ瀽 seed_data.sql锛屾彁鍙栨墍鏈夊晢鍝佷俊鎭€?
    杩斿洖锛?header_lines, insert_blocks)
      header_lines: INSERT 璇彞涔嬪墠鐨勬墍鏈夎锛堝惈绌鸿鍜屾敞閲婏級
      insert_blocks: 鍒楄〃锛屾瘡涓厓绱犱负 {'category': str, 'products': list}
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    # 浜у搧琛屾鍒欙細鍖归厤 ('鍟嗗搧鍚?, '鍒嗙被', price, stock, min_stock, 'image_url', 'description'),
    product_pattern = re.compile(
        r"^\s*\('([^']+)',\s*'([^']+)',\s*([\d.]+),\s*(\d+),\s*(\d+),\s*'[^']*',\s*'([^']*)'\)[,;]?\s*$"
    )

    products = []  # list of dicts

    # 褰撳墠姝ｅ湪澶勭悊鐨勫垎绫?
    current_category = None

    for line in lines:
        m = product_pattern.match(line)
        if m:
            name = m.group(1).strip()
            category = m.group(2).strip()
            price = m.group(3)
            stock = m.group(4)
            min_stock = m.group(5)
            description = m.group(6)

            products.append({
                'name': name,
                'category': category,
                'price': price,
                'stock': stock,
                'min_stock': min_stock,
                'description': description,
            })
            current_category = category

    return products


def generate_new_seed_data(input_path, output_path):
    """
    璇诲彇鍘熷 seed_data.sql锛屾浛鎹㈡墍鏈?image_url锛岃緭鍑烘柊鏂囦欢銆?
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 姝ｅ垯鍖归厤姣忔潯浜у搧璁板綍涓殑 image_url 閮ㄥ垎
    # 鏍煎紡锛?.. ('鍟嗗搧鍚?, '鍒嗙被', price, stock, min_stock, '鍘烾RL', '鎻忚堪') ...
    # 鏇挎崲绛栫暐锛氬尮閰嶆瘡鏉′骇鍝佽锛屾彁鍙栧晢鍝佸悕锛屾煡鏄犲皠琛紝鐢熸垚鏂癠RL锛屾浛鎹㈡暣琛?

    lines = content.split('\n')
    new_lines = []

    # 鍖归厤浜у搧琛岀殑姝ｅ垯锛堟崟鑾锋暣琛屼腑鐨?image_url锛?
    product_line_re = re.compile(
        r"^(\s*\('([^']+)',\s*'([^']+)',\s*[\d.]+\s*,\s*\d+\s*,\s*\d+\s*,\s*)'[^']*'(\s*,\s*'[^']*'\)[,;]?\s*)$"
    )

    for line in lines:
        m = product_line_re.match(line)
        if m:
            before_url = m.group(1)  # 浠庤棣栧埌 image_url 涔嬪墠
            name = m.group(2)
            category = m.group(3)
            after_url = m.group(4)   # 浠?image_url 涔嬪悗鍒拌灏?

            new_url = generate_url(name, category)
            new_line = f"{before_url}'{new_url}'{after_url}"
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    new_content = '\n'.join(new_lines)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return new_content


def verify_mapping_coverage(products):
    """楠岃瘉鎵€鏈夊晢鍝佸湪鏄犲皠琛ㄤ腑閮芥湁瀵瑰簲鍏抽敭璇?""
    missing = []
    for p in products:
        if p['name'] not in KEYWORD_MAP:
            missing.append(p['name'])
    return missing


def main():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # shared/database/scripts/ 鍚戜笂涓ょ骇鍒伴」鐩牴
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR)))
    DML_DIR = os.path.join(PROJECT_ROOT, 'shared', 'database', 'dml')
    INPUT_PATH = os.path.join(DML_DIR, 'seed_data.sql')
    OUTPUT_PATH = os.path.join(DML_DIR, 'seed_data.sql')

    print('=' * 65)
    print('  鐢熼矞鍟嗗煄 - 鍟嗗搧鍥剧墖 URL 鐢熸垚宸ュ叿')
    print('  鍥剧墖婧? Picsum (picsum.photos)')
    print('=' * 65)
    print()

    # 1. 瑙ｆ瀽鍘熷鏁版嵁
    print('[1/4] 瑙ｆ瀽 seed_data.sql ...')
    products = parse_seed_data(INPUT_PATH)
    print(f'  鍏辫В鏋愬埌 {len(products)} 涓晢鍝?)

    # 2. 楠岃瘉鏄犲皠瑕嗙洊
    print('[2/4] 楠岃瘉鍏抽敭璇嶆槧灏勮鐩栫巼 ...')
    missing = verify_mapping_coverage(products)
    if missing:
        print(f'  [璀﹀憡] {len(missing)} 涓晢鍝佺己灏戝叧閿瘝鏄犲皠:')
        for name in missing:
            print(f'    - {name}')
    else:
        print(f'  鎵€鏈?{len(products)} 涓晢鍝佸潎鏈夊叧閿瘝鏄犲皠 鉁?)

    # 3. 缁熻鍒嗙被鍒嗗竷
    print('[3/4] 缁熻鍒嗙被鍒嗗竷 ...')
    cat_count = {}
    for p in products:
        cat = p['category']
        cat_count[cat] = cat_count.get(cat, 0) + 1
    for cat, cnt in sorted(cat_count.items()):
        print(f'  {cat}: {cnt} 涓?)

    # 4. 鐢熸垚鏂?URL 骞惰緭鍑?
    print('[4/4] 鐢熸垚鏂?image_url 骞跺啓鍏?seed_data.sql ...')
    generate_new_seed_data(INPUT_PATH, OUTPUT_PATH)

    # 鎵撳嵃 URL 绀轰緥
    print()
    print('  URL 鐢熸垚绀轰緥锛堟瘡涓垎绫诲彇鍓?3 涓級:')
    print('  ' + '-' * 62)
    for cat in ['钄彍', '姘存灉', '鑲夌被', '楸肩被']:
        print(f'  [{cat}]')
        cat_products = [p for p in products if p['category'] == cat]
        for p in cat_products[:3]:
            url = generate_url(p['name'], p['category'])
            print(f'    {p["name"]}')
            print(f'    鈫?{url}')
        if len(cat_products) > 3:
            print(f'    ... 杩樻湁 {len(cat_products) - 3} 涓?)
        print()

    print(f'  杈撳嚭鏂囦欢: {OUTPUT_PATH}')
    print('=' * 65)
    print('  鍥剧墖 URL 鐢熸垚瀹屾垚锛?)
    print('  鎵€鏈?URL 宸茶縼绉昏嚦 Picsum (picsum.photos/seed/...)')
    print('  Picsum seeded URL 纭繚鍚屼竴鍟嗗搧濮嬬粓灞曠ず鍚屼竴寮犲浘鐗?)
    print('=' * 65)


if __name__ == '__main__':
    main()
