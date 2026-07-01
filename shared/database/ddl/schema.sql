-- ============================================================
-- 在线生鲜商城系统 SQLite 数据库表结构定义 (DDL)
-- 文件：shared/database/ddl/schema.sql
-- 数据库：SQLite
-- 说明：本文件定义商品表 products 和购物车表 cart_items 的结构。
--       按照需求约束，购物车操作不扣减库存，因此不创建库存扣减触发器。
-- ============================================================

-- 删除已存在的表（便于重复初始化，生产环境慎用）
DROP TABLE IF EXISTS cart_items;
DROP TABLE IF EXISTS products;

-- ------------------------------------------------------------
-- 1. 商品表 products
-- ------------------------------------------------------------
-- 存储生鲜商品基础信息、库存量与低库存阈值。
-- 分类字段取值范围：蔬菜、水果、肉类、鱼类。
-- 低库存预警判断规则：stock < min_stock。
-- ------------------------------------------------------------
CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    category    TEXT    NOT NULL CHECK (category IN ('蔬菜', '水果', '肉类', '鱼类')),
    price       REAL    NOT NULL CHECK (price >= 0),
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    min_stock   INTEGER NOT NULL DEFAULT 10 CHECK (min_stock >= 0),
    image_url   TEXT,
    description TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX idx_products_category ON products(category);

-- ------------------------------------------------------------
-- 2. 购物车表 cart_items
-- ------------------------------------------------------------
-- 记录购物车中商品与加购数量。
-- 由于系统不做登录鉴权，购物车为全局单购物车，不设计 user_id 字段。
-- 同一商品在购物车中只保留一条记录，通过 product_id 唯一约束保证。
-- 业务规则：加入购物车不扣减 products.stock，库存校验由应用层完成。
-- ------------------------------------------------------------
CREATE TABLE cart_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE(product_id),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX idx_cart_items_product_id ON cart_items(product_id);

-- ------------------------------------------------------------
-- 说明
-- ------------------------------------------------------------
-- 1. 本文件只负责建表，不含任何初始化数据，初始化数据见 dml/seed_data.sql。
-- 2. 严格按照需求：加入购物车不扣减库存，故未设计库存扣减触发器。
-- 3. 库存上限校验（quantity <= stock）由应用层在加购/修改时执行，
--    不在数据库层以触发器实现，以便返回友好的业务提示信息。
-- ============================================================
