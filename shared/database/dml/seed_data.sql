-- ============================================================
-- 在线生鲜商城系统 SQLite 数据库初始化数据 (DML)
-- 文件：shared/database/dml/seed_data.sql
-- 说明：本文件向 products 表插入示例商品，向 cart_items 表插入示例购物车记录。
--       商品覆盖蔬菜、水果、肉类、鱼类四个分类，每个分类至少 3 个商品。
--       包含库存低于最低阈值的商品，用于演示低库存预警效果。
-- 注意：加入购物车不会扣减 products.stock，库存数字保持独立。
-- ============================================================

-- ------------------------------------------------------------
-- 清空旧数据（便于重复初始化，保持自增 ID 从 1 开始）
-- ------------------------------------------------------------
DELETE FROM cart_items;
DELETE FROM products;
DELETE FROM sqlite_sequence WHERE name IN ('products', 'cart_items');

-- ============================================================
-- 一、商品数据 products
-- ============================================================
-- 字段顺序：name, category, price, stock, min_stock, image_url, description
-- 低库存商品（stock < min_stock）用于演示预警：
--   - 菠菜（stock=5  < min_stock=10）
--   - 阳光玫瑰葡萄（stock=8  < min_stock=12）
--   - 安格斯牛排（stock=3  < min_stock=8）
--   - 三文鱼刺身（stock=6  < min_stock=10）
-- ============================================================

-- ---------- 蔬菜类（4 个） ----------
INSERT INTO products (name, category, price, stock, min_stock, image_url, description) VALUES
('西红柿', '蔬菜', 6.80, 25, 10, '/static/images/products/tomato.jpg', '本地大棚种植，色泽红润，酸甜适中，适合炒菜与凉拌。'),
('黄瓜',   '蔬菜', 4.50, 30, 10, '/static/images/products/cucumber.jpg', '新鲜采摘，脆嫩多汁，清脆爽口，可生食可烹饪。'),
('菠菜',   '蔬菜', 5.20, 5,  10, '/static/images/products/spinach.jpg', '叶片肥厚翠绿，富含铁元素，低库存商品，需尽快补货。'),
('土豆',   '蔬菜', 3.20, 50, 15, '/static/images/products/potato.jpg', '黄心土豆，淀粉含量高，耐储存，适合炖煮与炒丝。');

-- ---------- 水果类（4 个） ----------
INSERT INTO products (name, category, price, stock, min_stock, image_url, description) VALUES
('红富士苹果',   '水果', 9.90, 40, 10, '/static/images/products/apple.jpg', '陕西洛川红富士，脆甜爽口，果香浓郁，新鲜直达。'),
('香蕉',         '水果', 5.80, 35, 10, '/static/images/products/banana.jpg', '海南热带香蕉，软糯香甜，自然成熟，老少皆宜。'),
('阳光玫瑰葡萄', '水果', 28.80, 8, 12, '/static/images/products/grape.jpg', '无籽脆甜，浓郁玫瑰香，果粒紧实，低库存商品，需尽快补货。'),
('海南金钻菠萝', '水果', 12.50, 20, 10, '/static/images/products/pineapple.jpg', '海南直发金钻菠萝，果肉金黄，甜度高，无需泡盐水。');

-- ---------- 肉类（3 个） ----------
INSERT INTO products (name, category, price, stock, min_stock, image_url, description) VALUES
('黑猪五花肉', '肉类', 39.90, 18, 8, '/static/images/products/pork.jpg', '散养黑猪，肥瘦相间，纹理清晰，适合红烧与回锅。'),
('散养土鸡',   '肉类', 58.00, 12, 8, '/static/images/products/chicken.jpg', '林下散养土鸡，肉质紧实，鲜香浓郁，适合炖汤。'),
('安格斯牛排', '肉类', 88.00, 3,  8, '/static/images/products/steak.jpg', '进口安格斯眼肉牛排，雪花纹理丰富，低库存商品，需尽快补货。');

-- ---------- 鱼类（3 个） ----------
INSERT INTO products (name, category, price, stock, min_stock, image_url, description) VALUES
('活鲫鱼',       '鱼类', 15.00, 22, 10, '/static/images/products/crucian.jpg', '水库活体鲫鱼，鲜活配送，肉质细嫩，适合煲汤。'),
('三文鱼刺身',   '鱼类', 68.00, 6,  10, '/static/images/products/salmon.jpg', '挪威进口三文鱼，冰鲜直供，适合刺身，低库存商品，需尽快补货。'),
('北极甜虾',     '鱼类', 45.00, 28, 10, '/static/images/products/shrimp.jpg', '北极冷水甜虾，肉质紧实甘甜，解冻即食，无需烹煮。');

-- ============================================================
-- 二、购物车示例数据 cart_items
-- ============================================================
-- 仅插入少量示例记录，用于演示购物车展示与总价计算。
-- quantity 不超过对应商品的 stock，满足应用层库存上限校验。
-- 加入购物车不扣减 products.stock。
-- ============================================================
INSERT INTO cart_items (product_id, quantity) VALUES
(1, 2),  -- 西红柿 ×2
(5, 1),  -- 红富士苹果 ×1
(9, 1);  -- 黑猪五花肉 ×1

-- ============================================================
-- 数据统计说明
-- ============================================================
-- 商品总数：14
--   - 蔬菜：4 个（西红柿、黄瓜、菠菜、土豆）
--   - 水果：4 个（红富士苹果、香蕉、阳光玫瑰葡萄、海南金钻菠萝）
--   - 肉类：3 个（黑猪五花肉、散养土鸡、安格斯牛排）
--   - 鱼类：3 个（活鲫鱼、三文鱼刺身、北极甜虾）
-- 低库存商品（stock < min_stock）共 4 个：
--   1. 菠菜         stock=5  < min_stock=10
--   2. 阳光玫瑰葡萄 stock=8  < min_stock=12
--   3. 安格斯牛排   stock=3  < min_stock=8
--   4. 三文鱼刺身   stock=6  < min_stock=10
-- 购物车示例记录：3 条
-- ============================================================
