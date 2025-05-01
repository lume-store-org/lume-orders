CREATE TABLE IF NOT EXISTS pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    data TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente'
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT NOT NULL,
    item_id INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE
);

-- Inserir dados iniciais para testes
INSERT INTO pedidos (id, usuario_id, data, status)
VALUES 
    (1, 1, '2025-04-20 10:30:00', 'enviado');

INSERT INTO itens_pedido (pedido_id, item_id, quantidade, preco_unitario)
VALUES
    (1, 1, 2, 4999.90),
    (1, 3, 1, 2799.90);