-- ===========================================
-- Shoe store schema + seed data for Oracle 26ai Autonomous DB
-- Run as ADMIN via Database Actions SQL Worksheet or SQLcl
-- ===========================================

-- 1) Create app user
CREATE USER shoestore IDENTIFIED BY "<StrongPassword123>";
GRANT CONNECT TO shoestore;
GRANT RESOURCE TO shoestore;
GRANT DWROLE TO shoestore;
GRANT CONSOLE_DEVELOPER TO shoestore;
GRANT UNLIMITED TABLESPACE TO shoestore;

-- Select AI privileges
GRANT EXECUTE ON DBMS_CLOUD TO shoestore;
GRANT EXECUTE ON DBMS_CLOUD_AI TO shoestore;

-- Network ACL for Anthropic endpoint
BEGIN
  DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
    host => 'api.anthropic.com',
    ace  => xs$ace_type(
      privilege_list => xs$name_list('http'),
      principal_name => 'SHOESTORE',
      principal_type => xs_acl.ptype_db
    )
  );
END;
/

-- ===========================================
-- Run the rest as SHOESTORE
-- ===========================================

DROP TABLE transactions CASCADE CONSTRAINTS;
DROP TABLE customers CASCADE CONSTRAINTS;
DROP TABLE products CASCADE CONSTRAINTS;

CREATE TABLE products (
  product_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  brand        VARCHAR2(100) NOT NULL,
  model        VARCHAR2(200) NOT NULL,
  category     VARCHAR2(50) NOT NULL,
  color        VARCHAR2(50),
  size_range   VARCHAR2(30),
  price        NUMBER(8,2) NOT NULL,
  stock_qty    NUMBER DEFAULT 0,
  released     DATE,
  description  VARCHAR2(500)
);

CREATE TABLE customers (
  customer_id  NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  first_name   VARCHAR2(100) NOT NULL,
  last_name    VARCHAR2(100) NOT NULL,
  email        VARCHAR2(200) UNIQUE NOT NULL,
  city         VARCHAR2(100),
  state        VARCHAR2(2),
  joined_date  DATE DEFAULT SYSDATE
);

CREATE TABLE transactions (
  txn_id        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_id   NUMBER NOT NULL,
  product_id    NUMBER NOT NULL,
  quantity      NUMBER DEFAULT 1,
  total_amount  NUMBER(8,2) NOT NULL,
  txn_date      DATE DEFAULT SYSDATE,
  status        VARCHAR2(20) DEFAULT 'completed',
  CONSTRAINT fk_txn_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
  CONSTRAINT fk_txn_product  FOREIGN KEY (product_id)  REFERENCES products (product_id)
);

-- Table and column comments (critical for Select AI schema understanding)
COMMENT ON TABLE products IS 'Shoe products in the store catalog with brand, model, pricing, and inventory';
COMMENT ON COLUMN products.category IS 'Shoe category: running, casual, hiking, basketball, or skateboarding';
COMMENT ON COLUMN products.size_range IS 'Available US shoe sizes as a range, e.g. 7-13';
COMMENT ON COLUMN products.stock_qty IS 'Current number of units in stock';
COMMENT ON COLUMN products.released IS 'Date the shoe model was released or added to catalog';

COMMENT ON TABLE customers IS 'Registered customers of the shoe store';
COMMENT ON COLUMN customers.state IS 'US state abbreviation, e.g. OR, CA, TX';
COMMENT ON COLUMN customers.joined_date IS 'Date the customer created their account';

COMMENT ON TABLE transactions IS 'Purchase transactions linking customers to products';
COMMENT ON COLUMN transactions.total_amount IS 'Total price paid (price x quantity)';
COMMENT ON COLUMN transactions.status IS 'Transaction status: completed, returned, or pending';
COMMENT ON COLUMN transactions.txn_date IS 'Date the transaction occurred';

-- Products (20) — all five categories
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Nike', 'Air Zoom Pegasus 41', 'running', 'Black/White', '7-13', 139.99, 42, DATE '2024-01-10', 'Daily trainer with responsive foam and breathable upper.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Brooks', 'Ghost 16', 'running', 'Navy', '7-14', 149.99, 30, DATE '2024-02-05', 'Soft cushioning for neutral runners logging high mileage.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Hoka', 'Clifton 9', 'running', 'Blue Coral', '6-14', 144.99, 28, DATE '2023-11-20', 'Plush ride with lightweight construction.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('On', 'Cloudrunner 2', 'running', 'All Black', '7-13', 149.99, 22, DATE '2024-03-01', 'Supportive road shoe with CloudTec cushioning.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Adidas', 'Samba OG', 'casual', 'White/Black', '4-14', 109.99, 55, DATE '2023-09-15', 'Classic indoor soccer silhouette turned street staple.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('New Balance', '574 Core', 'casual', 'Grey', '5-15', 89.99, 60, DATE '2023-08-01', 'Retro runner with suede and mesh upper.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Converse', 'Chuck Taylor All Star', 'casual', 'Optical White', '3-15', 59.99, 80, DATE '2024-01-05', 'Canvas high-top icon for everyday wear.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Puma', 'Suede Classic', 'casual', 'Peacoat', '4-14', 74.99, 45, DATE '2023-10-12', 'Soft suede with rubber outsole.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Salomon', 'XA Pro 3D v9', 'hiking', 'Black', '7-14', 149.99, 18, DATE '2024-02-18', 'Stable trail shoe with aggressive grip.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Salomon', 'Quest 4 GTX', 'hiking', 'Magnet', '7-13', 199.99, 12, DATE '2023-12-01', 'Waterproof boot for long hikes.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Adidas', 'Terrex Free Hiker 2', 'hiking', 'Core Black', '7-14', 119.99, 25, DATE '2023-07-22', 'Lightweight hiking boot with Continental rubber outsole.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Nike', 'LeBron XXI', 'basketball', 'Purple', '7-15', 249.99, 20, DATE '2024-01-25', 'Court shoe with Air Zoom units for explosive moves.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Adidas', 'Harden Vol. 8', 'basketball', 'Solar Red', '7-14', 159.99, 16, DATE '2024-02-10', 'Lightstrike cushioning for quick cuts.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Puma', 'MB.03', 'basketball', 'Green Gecko', '7-14', 129.99, 14, DATE '2023-11-05', 'Signature style with grippy rubber.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Vans', 'Old Skool', 'skateboarding', 'Black/White', '4-14', 74.99, 70, DATE '2023-06-01', 'Waffle sole and durable suede for skate sessions.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Vans', 'Sk8-Hi', 'skateboarding', 'Navy', '4-14', 79.99, 50, DATE '2023-08-20', 'High-top protection with classic side stripe.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Converse', 'CONS Louie Lopez Pro', 'skateboarding', 'Black', '4-13', 84.99, 33, DATE '2024-01-12', 'Cupsole skate shoe with suede upper.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('New Balance', 'Numeric 480', 'skateboarding', 'Grey', '4-14', 89.99, 27, DATE '2023-09-30', 'Heritage silhouette tuned for board feel.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Brooks', 'Adrenaline GTS 23', 'running', 'Grey/Blue', '7-14', 139.99, 35, DATE '2023-05-15', 'Supportive daily trainer with GuideRails.');
INSERT INTO products (brand, model, category, color, size_range, price, stock_qty, released, description) VALUES ('Hoka', 'Speedgoat 5', 'hiking', 'Blue Graphite', '6-14', 159.99, 19, DATE '2023-10-01', 'Aggressive trail shoe for technical terrain.');

-- Customers (15) — include Gresham OR
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Marcus', 'Chen', 'marcus.chen@example.com', 'Portland', 'OR', DATE '2023-04-12');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Sofia', 'Martinez', 'sofia.m@example.com', 'Austin', 'TX', DATE '2023-06-20');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('James', 'O''Brien', 'james.obrien@example.com', 'Chicago', 'IL', DATE '2023-08-05');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Priya', 'Nair', 'priya.nair@example.com', 'Seattle', 'WA', DATE '2023-09-14');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Elena', 'Volkov', 'elena.v@example.com', 'Denver', 'CO', DATE '2023-11-02');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Tyler', 'Brooks', 'tyler.brooks@example.com', 'Gresham', 'OR', DATE '2024-01-08');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Aisha', 'Khan', 'aisha.khan@example.com', 'Atlanta', 'GA', DATE '2024-01-22');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Noah', 'Williams', 'noah.w@example.com', 'Boston', 'MA', DATE '2024-02-03');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Lily', 'Nguyen', 'lily.nguyen@example.com', 'San Jose', 'CA', DATE '2024-02-17');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Diego', 'Ramirez', 'diego.r@example.com', 'Phoenix', 'AZ', DATE '2024-03-01');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Hannah', 'Lee', 'hannah.lee@example.com', 'Minneapolis', 'MN', DATE '2023-05-30');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Omar', 'Hassan', 'omar.hassan@example.com', 'Detroit', 'MI', DATE '2023-07-11');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Rachel', 'Green', 'rachel.g@example.com', 'Miami', 'FL', DATE '2023-12-09');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Kevin', 'Park', 'kevin.park@example.com', 'Nashville', 'TN', DATE '2024-03-15');
INSERT INTO customers (first_name, last_name, email, city, state, joined_date) VALUES ('Zoe', 'Adams', 'zoe.adams@example.com', 'Philadelphia', 'PA', DATE '2024-04-02');

-- Transactions (40) — mix of patterns, 3 returns, 2 pending; totals = price * qty
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (1, 3, 1, 144.99, DATE '2024-01-15', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (1, 4, 2, 299.98, DATE '2024-02-20', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (1, 19, 1, 139.99, DATE '2024-03-10', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (2, 15, 1, 74.99, DATE '2024-01-05', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (2, 16, 2, 159.98, DATE '2024-02-12', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (2, 17, 1, 84.99, DATE '2024-03-22', 'returned');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (3, 1, 1, 139.99, DATE '2024-04-01', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (3, 2, 1, 149.99, DATE '2024-05-18', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (4, 5, 1, 109.99, DATE '2024-01-28', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (4, 6, 2, 179.98, DATE '2024-02-14', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (5, 9, 1, 149.99, DATE '2024-03-05', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (5, 10, 1, 199.99, DATE '2024-04-20', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (6, 7, 3, 179.97, DATE '2024-02-01', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (6, 8, 1, 74.99, DATE '2024-03-30', 'pending');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (7, 12, 1, 249.99, DATE '2024-01-12', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (7, 13, 1, 159.99, DATE '2024-02-25', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (8, 14, 2, 259.98, DATE '2024-03-08', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (8, 11, 1, 119.99, DATE '2024-04-11', 'returned');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (9, 18, 1, 89.99, DATE '2024-01-20', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (9, 19, 1, 139.99, DATE '2024-02-28', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (10, 20, 1, 159.99, DATE '2024-03-18', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (10, 9, 1, 149.99, DATE '2024-04-25', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (11, 15, 1, 74.99, DATE '2024-01-07', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (11, 16, 1, 79.99, DATE '2024-02-09', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (12, 17, 2, 169.98, DATE '2024-03-03', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (12, 18, 1, 89.99, DATE '2024-04-14', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (13, 6, 1, 89.99, DATE '2024-01-30', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (13, 5, 1, 109.99, DATE '2024-02-22', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (14, 2, 1, 149.99, DATE '2024-03-12', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (14, 3, 2, 289.98, DATE '2024-04-05', 'pending');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (15, 8, 1, 74.99, DATE '2024-01-18', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (15, 4, 1, 149.99, DATE '2024-02-27', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (1, 1, 1, 139.99, DATE '2024-04-28', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (4, 1, 1, 139.99, DATE '2024-05-02', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (5, 20, 1, 159.99, DATE '2024-05-10', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (7, 10, 1, 199.99, DATE '2024-05-15', 'returned');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (3, 4, 1, 149.99, DATE '2024-06-01', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (10, 6, 1, 89.99, DATE '2024-06-08', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (11, 1, 1, 139.99, DATE '2024-06-15', 'completed');
INSERT INTO transactions (customer_id, product_id, quantity, total_amount, txn_date, status) VALUES (12, 5, 2, 219.98, DATE '2024-06-22', 'completed');

COMMIT;

-- Verification
SELECT 'products' AS tbl, COUNT(*) AS row_count FROM products
UNION ALL
SELECT 'customers', COUNT(*) FROM customers
UNION ALL
SELECT 'transactions', COUNT(*) FROM transactions;
