SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    shipping_address TEXT,
    total DECIMAL(10, 2) NOT NULL DEFAULT 0,
    INDEX idx_orders_user (user_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Name, image and price are stored in the order: catalog changes do not alter past orders
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    image TEXT,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Sample order for cliente@lumestore.dev (user 2)
INSERT INTO orders (id, user_id, created_at, status, shipping_address, total) VALUES
    (1, 2, '2025-04-20 10:30:00', 'delivered', 'Rua de Teste, 123 - São Paulo/SP', 5449.80);

INSERT INTO order_items (order_id, product_id, name, image, quantity, unit_price) VALUES
    (1, 1, 'Smartphone Pro 128 GB', '/produtos/smartphone.jpg', 1, 4999.90),
    (1, 7, 'Fone over-ear Bluetooth', '/produtos/fone-over-ear.jpg', 1, 449.90);
