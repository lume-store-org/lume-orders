from flask import jsonify, request
from database import get_db_connection
import requests
import os
from datetime import datetime

# URL do serviço de itens (fornecido pelo Docker Compose através de variável de ambiente)
ITENS_SERVICE_URL = os.environ.get('ITENS_SERVICE_URL', 'http://service-itens:5001')

def register_routes(app):
    @app.route('/pedidos', methods=['GET'])
    def listar_pedidos():
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Buscar todos os pedidos
        cur.execute('''
            SELECT p.id, p.usuario_id, p.data, p.status
            FROM pedidos p
            ORDER BY p.data DESC
        ''')
        
        pedidos_rows = cur.fetchall()
        pedidos = []
        
        for p_row in pedidos_rows:
            pedido_id = p_row[0]
            
            # Buscar os itens do pedido
            cur.execute('''
                SELECT item_id, quantidade, preco_unitario
                FROM itens_pedido
                WHERE pedido_id = %s
            ''', (pedido_id,))
            
            itens_rows = cur.fetchall()
            itens = []
            valor_total = 0
            
            for i_row in itens_rows:
                item = {
                    'item_id': i_row[0],
                    'quantidade': i_row[1],
                    'preco_unitario': float(i_row[2])
                }
                valor_total += item['quantidade'] * item['preco_unitario']
                itens.append(item)
                
            pedido = {
                'id': p_row[0],
                'usuario_id': p_row[1],
                'data': p_row[2].isoformat() if isinstance(p_row[2], datetime) else p_row[2],
                'status': p_row[3],
                'itens': itens,
                'valor_total': valor_total
            }
            
            pedidos.append(pedido)
            
        cur.close()
        conn.close()
        
        return jsonify({"pedidos": pedidos})

    @app.route('/pedidos/usuario/<int:usuario_id>', methods=['GET'])
    def listar_pedidos_usuario(usuario_id):
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Buscar todos os pedidos do usuário
        cur.execute('''
            SELECT p.id, p.usuario_id, p.data, p.status
            FROM pedidos p
            WHERE p.usuario_id = %s
            ORDER BY p.data DESC
        ''', (usuario_id,))
        
        pedidos_rows = cur.fetchall()
        pedidos = []
        
        for p_row in pedidos_rows:
            pedido_id = p_row[0]
            
            # Buscar os itens do pedido
            cur.execute('''
                SELECT item_id, quantidade, preco_unitario
                FROM itens_pedido
                WHERE pedido_id = %s
            ''', (pedido_id,))
            
            itens_rows = cur.fetchall()
            itens = []
            valor_total = 0
            
            for i_row in itens_rows:
                item = {
                    'item_id': i_row[0],
                    'quantidade': i_row[1],
                    'preco_unitario': float(i_row[2])
                }
                valor_total += item['quantidade'] * item['preco_unitario']
                itens.append(item)
                
            pedido = {
                'id': p_row[0],
                'usuario_id': p_row[1],
                'data': p_row[2].isoformat() if isinstance(p_row[2], datetime) else p_row[2],
                'status': p_row[3],
                'itens': itens,
                'valor_total': valor_total
            }
            
            pedidos.append(pedido)
            
        cur.close()
        conn.close()
        
        return jsonify({"pedidos": pedidos})

    @app.route('/pedidos/<int:id>', methods=['GET'])
    def obter_pedido(id):
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Buscar o pedido específico
        cur.execute('''
            SELECT p.id, p.usuario_id, p.data, p.status
            FROM pedidos p
            WHERE p.id = %s
        ''', (id,))
        
        p_row = cur.fetchone()
        
        if p_row is None:
            cur.close()
            conn.close()
            return jsonify({"erro": "Pedido não encontrado"}), 404
            
        # Buscar os itens do pedido
        cur.execute('''
            SELECT item_id, quantidade, preco_unitario
            FROM itens_pedido
            WHERE pedido_id = %s
        ''', (id,))
        
        itens_rows = cur.fetchall()
        itens = []
        valor_total = 0
        
        for i_row in itens_rows:
            item = {
                'item_id': i_row[0],
                'quantidade': i_row[1],
                'preco_unitario': float(i_row[2])
            }
            valor_total += item['quantidade'] * item['preco_unitario']
            itens.append(item)
            
        pedido = {
            'id': p_row[0],
            'usuario_id': p_row[1],
            'data': p_row[2].isoformat() if isinstance(p_row[2], datetime) else p_row[2],
            'status': p_row[3],
            'itens': itens,
            'valor_total': valor_total
        }
        
        cur.close()
        conn.close()
        
        return jsonify(pedido)

    @app.route('/pedidos', methods=['POST'])
    def criar_pedido():
        novo_pedido = request.json
        usuario_id = novo_pedido.get('usuario_id')
        itens_pedido = novo_pedido.get('itens', [])
        
        # Validar se existem itens no pedido
        if not itens_pedido:
            return jsonify({"erro": "O pedido deve conter pelo menos um item"}), 400
        
        # Verificar estoque disponível
        estoque_ok, mensagem = verificar_estoque(itens_pedido)
        if not estoque_ok:
            return jsonify({"erro": mensagem}), 400
            
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Iniciar transação
            conn.autocommit = False
            
            # Criar o pedido
            cur.execute(
                'INSERT INTO pedidos (usuario_id) VALUES (%s)',
                (usuario_id,)
            )
            # Obter o ID do pedido inserido usando lastrowid (método do MySQL)
            pedido_id = cur.lastrowid
            conn.commit()
            
            # Obter a data do pedido em uma consulta separada
            cur.execute('SELECT data FROM pedidos WHERE id = %s', (pedido_id,))
            pedido_data = cur.fetchone()[0]
            
            # Adicionar os itens ao pedido
            valor_total = 0
            for item in itens_pedido:
                cur.execute(
                    'INSERT INTO itens_pedido (pedido_id, item_id, quantidade, preco_unitario) VALUES (%s, %s, %s, %s)',
                    (pedido_id, item['item_id'], item['quantidade'], item['preco_unitario'])
                )
                valor_total += item['quantidade'] * item['preco_unitario']
            
            # Atualizar o estoque dos itens
            atualizar_estoque(itens_pedido)
            
            # Commit da transação
            conn.commit()
            
            # Montar resposta
            pedido_completo = {
                "id": pedido_id,
                "usuario_id": usuario_id,
                "data": pedido_data.isoformat() if isinstance(pedido_data, datetime) else pedido_data,
                "status": "pendente",
                "itens": itens_pedido,
                "valor_total": valor_total
            }
            
            cur.close()
            conn.close()
            
            return jsonify(pedido_completo), 201
            
        except Exception as e:
            # Rollback em caso de erro
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"erro": f"Erro ao criar pedido: {str(e)}"}), 500

    @app.route('/pedidos/<int:id>/status', methods=['PATCH'])
    def atualizar_status_pedido(id):
        novo_status = request.json.get('status')
        
        if not novo_status:
            return jsonify({"erro": "Status não fornecido"}), 400
            
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar se o pedido existe
        cur.execute('SELECT id FROM pedidos WHERE id = %s', (id,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"erro": "Pedido não encontrado"}), 404
            
        # Atualizar o status do pedido
        cur.execute(
            'UPDATE pedidos SET status = %s WHERE id = %s',
            (novo_status, id)
        )
        conn.commit()
        
        # Recuperar o pedido atualizado
        cur.execute('''
            SELECT p.id, p.usuario_id, p.data, p.status
            FROM pedidos p
            WHERE p.id = %s
        ''', (id,))
        
        p_row = cur.fetchone()
        
        # Buscar os itens do pedido
        cur.execute('''
            SELECT item_id, quantidade, preco_unitario
            FROM itens_pedido
            WHERE pedido_id = %s
        ''', (id,))
        
        itens_rows = cur.fetchall()
        itens = []
        valor_total = 0
        
        for i_row in itens_rows:
            item = {
                'item_id': i_row[0],
                'quantidade': i_row[1],
                'preco_unitario': float(i_row[2])
            }
            valor_total += item['quantidade'] * item['preco_unitario']
            itens.append(item)
            
        pedido = {
            'id': p_row[0],
            'usuario_id': p_row[1],
            'data': p_row[2].isoformat() if isinstance(p_row[2], datetime) else p_row[2],
            'status': p_row[3],
            'itens': itens,
            'valor_total': valor_total
        }
        
        cur.close()
        conn.close()
        
        return jsonify(pedido)

    @app.route('/pedidos/<int:id>', methods=['DELETE'])
    def cancelar_pedido(id):
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar se o pedido existe e qual seu status
        cur.execute('SELECT id, status FROM pedidos WHERE id = %s', (id,))
        row = cur.fetchone()
        
        if row is None:
            cur.close()
            conn.close()
            return jsonify({"erro": "Pedido não encontrado"}), 404
            
        status = row[1]
        
        # Se o pedido já foi enviado ou entregue, não permite cancelar
        if status in ['enviado', 'entregue']:
            cur.close()
            conn.close()
            return jsonify({"erro": "Não é possível cancelar um pedido já enviado ou entregue"}), 400
            
        # Excluir o pedido e seus itens (cascata)
        cur.execute('DELETE FROM pedidos WHERE id = %s', (id,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({"mensagem": f"Pedido {id} cancelado com sucesso"})

    @app.route('/health', methods=['GET'])
    def health():
        try:
            # Verificar conexão com o banco de dados
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT 1')
            cur.close()
            conn.close()
            
            # Verificar conexão com o serviço de itens
            try:
                response = requests.get(f"{ITENS_SERVICE_URL}/health", timeout=1)
                itens_status = "online" if response.status_code == 200 else "erro"
            except requests.exceptions.RequestException:
                itens_status = "offline"
                
            return jsonify({
                "status": "ok", 
                "database": "connected",
                "dependencias": {
                    "itens_service": itens_status
                }
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "erro", 
                "database": "disconnected", 
                "detalhes": str(e)
            }), 500


def verificar_estoque(itens):
    """Verificar se os itens estão disponíveis no estoque"""
    for item_pedido in itens:
        try:
            # Consultar o serviço de itens
            response = requests.get(f"{ITENS_SERVICE_URL}/itens/{item_pedido['item_id']}")
            if response.status_code == 200:
                item_estoque = response.json()
                if item_estoque['estoque'] < item_pedido['quantidade']:
                    return False, f"Item {item_pedido['item_id']} sem estoque suficiente"
            else:
                return False, f"Item {item_pedido['item_id']} não encontrado"
        except requests.exceptions.RequestException:
            return False, "Erro ao consultar serviço de itens"
    return True, ""

def atualizar_estoque(itens):
    """Atualizar o estoque após confirmação do pedido"""
    for item_pedido in itens:
        try:
            # Obter item atual
            response = requests.get(f"{ITENS_SERVICE_URL}/itens/{item_pedido['item_id']}")
            if response.status_code == 200:
                item = response.json()
                # Atualizar estoque
                item['estoque'] -= item_pedido['quantidade']
                # Enviar atualização
                requests.put(
                    f"{ITENS_SERVICE_URL}/itens/{item_pedido['item_id']}", 
                    json=item
                )
        except requests.exceptions.RequestException:
            # Continua mesmo com erro, pois o pedido já foi registrado
            pass