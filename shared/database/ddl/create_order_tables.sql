-- ============================================================
-- 创建订单相关表结构
-- 数据库：fresh_market.db
-- ============================================================

-- ------------------------------------------------------------
-- 订单表 orders
-- ------------------------------------------------------------
-- 存储订单主信息，包含用户ID、订单总价、订单状态等。
-- status 取值：pending-待支付，paid-已支付，cancelled-已取消。
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    total_price REAL    NOT NULL CHECK (total_price >= 0),
    status      TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'cancelled')),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);

-- ------------------------------------------------------------
-- 订单明细表 order_items
-- ------------------------------------------------------------
-- 记录订单中每个商品的明细信息。
-- 包含商品快照信息（product_name、product_price），确保订单历史数据完整性。
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER NOT NULL,
    product_id    INTEGER NOT NULL,
    product_name  TEXT    NOT NULL,
    product_price REAL    NOT NULL CHECK (product_price >= 0),
    quantity      INTEGER NOT NULL CHECK (quantity >= 1),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);