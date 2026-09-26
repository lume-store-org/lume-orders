import os
from datetime import datetime

import requests
from flask import jsonify, request

from database import get_db_connection

ITENS_SERVICE_URL = os.environ.get('ITENS_SERVICE_URL', 'http://service-itens:5001')
STATUS = ['pendente', 'pago', 'enviado', 'entregue', 'cancelado']
CANCELAVEIS = {'pendente', 'pago'}


def usuario_atual():
    """Usuário autenticado, repassado pelo API Gateway nos headers internos."""
    uid = request.headers.get('X-Usuario-Id')
    return (int(uid) if uid else None), request.headers.get('X-Usuario-Admin') == '1'


def carregar_pedidos(cur, where='', params=()):
    cur.execute(
        f'SELECT id, usuario_id, data, status, endereco_entrega, valor_total FROM pedidos {where} ORDER BY data DESC, id DESC',
        params,
    )
    pedidos = []
    for p in cur.fetchall():
        cur.execute(
            'SELECT item_id, nome, imagem, quantidade, preco_unitario FROM itens_pedido WHERE pedido_id = %s ORDER BY id',
            (p[0],),
        )
        itens = [
            {'item_id': i[0], 'nome': i[1], 'imagem': i[2], 'quantidade': i[3], 'preco_unitario': float(i[4])}
            for i in cur.fetchall()
        ]
        pedidos.append({
            'id': p[0],
            'usuario_id': p[1],
            'data': p[2].isoformat() if isinstance(p[2], datetime) else p[2],
            'status': p[3],
            'endereco_entrega': p[4],
            'valor_total': float(p[5]),
            'itens': itens,
        })
    return pedidos


def devolver_estoque(itens):
    try:
        requests.post(f'{ITENS_SERVICE_URL}/interno/estoque/devolver', json={'itens': itens}, timeout=5)
    except requests.exceptions.RequestException:
        pass


def register_routes(app):
    @app.route('/pedidos', methods=['GET'])
    def listar_pedidos():
        uid, admin = usuario_atual()
        if uid is None:
            return jsonify({"erro": "Não autenticado"}), 401
        conn = get_db_connection()
        cur = conn.cursor()
        # Admin vê todos; cliente vê só os próprios
        pedidos = carregar_pedidos(cur) if admin else carregar_pedidos(cur, 'WHERE usuario_id = %s', (uid,))
        cur.close()
        conn.close()
        return jsonify({"pedidos": pedidos})

    @app.route('/pedidos/<int:id>', methods=['GET'])
    def obter_pedido(id):
        uid, admin = usuario_atual()
        conn = get_db_connection()
        cur = conn.cursor()
        pedidos = carregar_pedidos(cur, 'WHERE id = %s', (id,))
        cur.close()
        conn.close()
        if not pedidos or not (admin or pedidos[0]['usuario_id'] == uid):
            return jsonify({"erro": "Pedido não encontrado"}), 404
        return jsonify(pedidos[0])

    @app.route('/pedidos', methods=['POST'])
    def criar_pedido():
        uid, _ = usuario_atual()
        if uid is None:
            return jsonify({"erro": "Não autenticado"}), 401
        dados = request.get_json(silent=True) or {}
        linhas = [
            {'item_id': i.get('item_id'), 'quantidade': i.get('quantidade', 1)}
            for i in dados.get('itens', []) if isinstance(i, dict)
        ]
        if not linhas:
            return jsonify({"erro": "O pedido deve conter pelo menos um item"}), 400

        # Reserva o estoque e obtém os preços do catálogo (o cliente não define preço)
        try:
            resp = requests.post(f'{ITENS_SERVICE_URL}/interno/estoque/reservar', json={'itens': linhas}, timeout=5)
        except requests.exceptions.RequestException:
            return jsonify({"erro": "Serviço de itens indisponível"}), 503
        if resp.status_code != 200:
            return jsonify(resp.json()), resp.status_code
        itens = resp.json()['itens']
        total = round(sum(i['quantidade'] * i['preco_unitario'] for i in itens), 2)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                'INSERT INTO pedidos (usuario_id, endereco_entrega, valor_total) VALUES (%s, %s, %s)',
                (uid, dados.get('endereco_entrega', ''), total),
            )
            pedido_id = cur.lastrowid
            cur.executemany(
                'INSERT INTO itens_pedido (pedido_id, item_id, nome, imagem, quantidade, preco_unitario) VALUES (%s, %s, %s, %s, %s, %s)',
                [(pedido_id, i['item_id'], i['nome'], i['imagem'], i['quantidade'], i['preco_unitario']) for i in itens],
            )
            conn.commit()
            return jsonify(carregar_pedidos(cur, 'WHERE id = %s', (pedido_id,))[0]), 201
        except Exception:
            conn.rollback()
            devolver_estoque(itens)
            return jsonify({"erro": "Erro ao registrar o pedido"}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/pedidos/<int:id>/status', methods=['PATCH'])
    def atualizar_status_pedido(id):
        if not usuario_atual()[1]:
            return jsonify({"erro": "Apenas administradores"}), 403
        novo_status = (request.get_json(silent=True) or {}).get('status')
        if novo_status not in STATUS:
            return jsonify({"erro": f"Status deve ser um de: {', '.join(STATUS)}"}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            pedidos = carregar_pedidos(cur, 'WHERE id = %s', (id,))
            if not pedidos:
                return jsonify({"erro": "Pedido não encontrado"}), 404
            if novo_status == 'cancelado' and pedidos[0]['status'] != 'cancelado':
                devolver_estoque(pedidos[0]['itens'])
            cur.execute('UPDATE pedidos SET status = %s WHERE id = %s', (novo_status, id))
            conn.commit()
            return jsonify(carregar_pedidos(cur, 'WHERE id = %s', (id,))[0])
        finally:
            cur.close()
            conn.close()

    @app.route('/pedidos/<int:id>', methods=['DELETE'])
    def cancelar_pedido(id):
        uid, admin = usuario_atual()
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            pedidos = carregar_pedidos(cur, 'WHERE id = %s', (id,))
            if not pedidos or not (admin or pedidos[0]['usuario_id'] == uid):
                return jsonify({"erro": "Pedido não encontrado"}), 404
            if pedidos[0]['status'] not in CANCELAVEIS:
                return jsonify({"erro": "Só é possível cancelar pedidos pendentes ou pagos"}), 409
            cur.execute("UPDATE pedidos SET status = 'cancelado' WHERE id = %s", (id,))
            conn.commit()
            devolver_estoque(pedidos[0]['itens'])
            return jsonify(carregar_pedidos(cur, 'WHERE id = %s', (id,))[0])
        finally:
            cur.close()
            conn.close()

    @app.route('/health', methods=['GET'])
    def health():
        try:
            conn = get_db_connection()
            conn.close()
        except Exception:
            return jsonify({"status": "erro", "database": "disconnected"}), 500
        try:
            itens = requests.get(f'{ITENS_SERVICE_URL}/health', timeout=2)
            itens_status = 'online' if itens.status_code == 200 else 'erro'
        except requests.exceptions.RequestException:
            itens_status = 'offline'
        return jsonify({"status": "ok", "database": "connected", "dependencias": {"itens_service": itens_status}}), 200
