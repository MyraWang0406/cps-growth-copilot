-- CPS Growth Copilot Database Schema

-- Merchants (商家)
CREATE TABLE IF NOT EXISTS merchants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Taokes (淘客)
CREATE TABLE IF NOT EXISTS taokes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products (商品)
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER REFERENCES merchants(id),
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock INTEGER DEFAULT 0,
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Campaigns (活动)
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER REFERENCES merchants(id),
    name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Commission Rules (佣金规则)
CREATE TABLE IF NOT EXISTS commission_rules (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER REFERENCES merchants(id),
    product_id INTEGER REFERENCES products(id),
    taoke_id INTEGER REFERENCES taokes(id),
    commission_rate DECIMAL(5, 4) NOT NULL, -- 0.0000 to 1.0000
    commission_type VARCHAR(50) DEFAULT 'percentage', -- percentage or fixed
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contents (内容/素材)
CREATE TABLE IF NOT EXISTS contents (
    id SERIAL PRIMARY KEY,
    taoke_id INTEGER REFERENCES taokes(id),
    merchant_id INTEGER REFERENCES merchants(id),
    title VARCHAR(500),
    content_type VARCHAR(50), -- article, video, image, etc.
    url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Content Product Map (内容-商品关联)
CREATE TABLE IF NOT EXISTS content_product_map (
    id SERIAL PRIMARY KEY,
    content_id INTEGER REFERENCES contents(id),
    product_id INTEGER REFERENCES products(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clicks (点击)
CREATE TABLE IF NOT EXISTS clicks (
    id SERIAL PRIMARY KEY,
    taoke_id INTEGER REFERENCES taokes(id),
    content_id INTEGER REFERENCES contents(id),
    product_id INTEGER REFERENCES products(id),
    merchant_id INTEGER REFERENCES merchants(id),
    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(50),
    user_agent TEXT
);

-- Orders (订单)
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    taoke_id INTEGER REFERENCES taokes(id),
    merchant_id INTEGER REFERENCES merchants(id),
    product_id INTEGER REFERENCES products(id),
    click_id INTEGER REFERENCES clicks(id),
    order_amount DECIMAL(10, 2) NOT NULL,
    commission_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, paid, refunded, cancelled
    ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP,
    refunded_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_clicks_taoke_date ON clicks(taoke_id, clicked_at);
CREATE INDEX IF NOT EXISTS idx_clicks_product ON clicks(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_taoke_date ON orders(taoke_id, ordered_at);
CREATE INDEX IF NOT EXISTS idx_orders_merchant_date ON orders(merchant_id, ordered_at);
CREATE INDEX IF NOT EXISTS idx_orders_product ON orders(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_commission_rules_merchant ON commission_rules(merchant_id);
CREATE INDEX IF NOT EXISTS idx_commission_rules_product ON commission_rules(product_id);
CREATE INDEX IF NOT EXISTS idx_commission_rules_taoke ON commission_rules(taoke_id);

-- Daily Product Metrics View
CREATE OR REPLACE VIEW daily_product_metrics AS
SELECT 
    DATE(o.ordered_at) as metric_date,
    o.product_id,
    o.merchant_id,
    o.taoke_id,
    COUNT(DISTINCT c.id) as impressions,
    COUNT(DISTINCT cl.id) as clicks,
    COUNT(DISTINCT o.id) as orders,
    COUNT(DISTINCT CASE WHEN o.status = 'refunded' THEN o.id END) as refunds,
    SUM(CASE WHEN o.status IN ('paid', 'pending') THEN o.order_amount ELSE 0 END) as gmv,
    SUM(CASE WHEN o.status IN ('paid', 'pending') THEN o.commission_amount ELSE 0 END) as commission_paid,
    CASE 
        WHEN COUNT(DISTINCT cl.id) > 0 THEN 
            COUNT(DISTINCT o.id)::DECIMAL / COUNT(DISTINCT cl.id)::DECIMAL 
        ELSE 0 
    END as cvr,
    CASE 
        WHEN COUNT(DISTINCT cl.id) > 0 THEN 
            SUM(CASE WHEN o.status IN ('paid', 'pending') THEN o.order_amount ELSE 0 END) / COUNT(DISTINCT cl.id)::DECIMAL
        ELSE 0 
    END as epc
FROM orders o
LEFT JOIN clicks cl ON o.click_id = cl.id
LEFT JOIN contents c ON cl.content_id = c.id
GROUP BY DATE(o.ordered_at), o.product_id, o.merchant_id, o.taoke_id;

