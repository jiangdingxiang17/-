-- ============================================================
-- 在线生鲜商城系统 SQLite 数据库表结构定义 (DDL)
-- 文件：shared/database/ddl/schema.sql
-- 数据库：SQLite
-- 说明：本文件定义用户表 users、商品表 products 和购物车表 cart_items 的结构。
--       第 1 天迭代目标：支持登录用户，并让购物车按用户隔离。
-- ============================================================

-- 删除已存在的表（便于重复初始化，生产环境慎用）
DROP TABLE IF EXISTS cart_items;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

-- ------------------------------------------------------------
-- 1. 用户表 users
-- ------------------------------------------------------------
-- 存储消费者和管理员账号。密码使用哈希值保存，不保存明文密码。
-- role 取值：customer 表示普通消费者，admin 表示管理员。
-- ------------------------------------------------------------
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'admin')),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX idx_users_username ON users(username);

-- ------------------------------------------------------------
-- 2. 商品表 products
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
-- 3. 购物车表 cart_items
-- ------------------------------------------------------------
-- 记录购物车中商品与加购数量。
-- 购物车按用户隔离，同一用户的同一商品只保留一条记录。
-- 业务规则：加入购物车不扣减 products.stock，库存校验由应用层完成。
-- ------------------------------------------------------------
CREATE TABLE cart_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    product_id  INTEGER NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE(user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX idx_cart_items_user_id ON cart_items(user_id);
CREATE INDEX idx_cart_items_product_id ON cart_items(product_id);

-- ------------------------------------------------------------
-- 说明
-- ------------------------------------------------------------
-- 1. 本文件只负责建表，不含任何初始化数据，初始化数据见 dml/seed_data.sql。
-- 2. 第 1 天迭代先实现登录与用户购物车隔离，支付、订单与库存扣减在后续迭代实现。
-- 3. 库存上限校验（quantity <= stock）由应用层在加购/修改时执行，
--    不在数据库层以触发器实现，以便返回友好的业务提示信息。
-- ============================================================
