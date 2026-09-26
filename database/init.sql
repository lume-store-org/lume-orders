SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    data TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
    endereco_entrega TEXT,
    valor_total DECIMAL(10, 2) NOT NULL DEFAULT 0,
    INDEX idx_pedidos_usuario (usuario_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Nome, imagem e preço ficam gravados no pedido: mudanças no catálogo não alteram pedidos antigos
CREATE TABLE IF NOT EXISTS itens_pedido (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT NOT NULL,
    item_id INT NOT NULL,
    nome VARCHAR(255) NOT NULL,
    imagem TEXT,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Pedido de exemplo da conta cliente@loja.dev (usuário 2)
INSERT INTO pedidos (id, usuario_id, data, status, endereco_entrega, valor_total) VALUES
    (1, 2, '2025-04-20 10:30:00', 'entregue', 'Rua de Teste, 123 - São Paulo/SP', 5449.80);

INSERT INTO itens_pedido (pedido_id, item_id, nome, imagem, quantidade, preco_unitario) VALUES
    (1, 1, 'Smartphone Pro 128 GB', '/produtos/smartphone.jpg', 1, 4999.90),
    (1, 7, 'Fone over-ear Bluetooth', '/produtos/fone-over-ear.jpg', 1, 449.90);
