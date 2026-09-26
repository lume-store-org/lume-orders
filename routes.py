import os
from datetime import datetime

import requests
from flask import jsonify, request

from database import get_db_connection

CATALOG_SERVICE_URL = os.environ.get('CATALOG_SERVICE_URL', 'http://lume-catalog:5001')
STATUSES = ['pending', 'paid', 'shipped', 'delivered', 'cancelled']
CANCELLABLE = {'pending', 'paid'}


def current_user():
    """Authenticated user, forwarded by the API Gateway in internal headers."""
    user_id = request.headers.get('X-User-Id')
    return (int(user_id) if user_id else None), request.headers.get('X-User-Admin') == '1'


def load_orders(cur, where='', params=()):
    cur.execute(
        f'SELECT id, user_id, created_at, status, shipping_address, total FROM orders {where} ORDER BY created_at DESC, id DESC',
        params,
    )
    orders = []
    for o in cur.fetchall():
        cur.execute(
            'SELECT product_id, name, image, quantity, unit_price FROM order_items WHERE order_id = %s ORDER BY id',
            (o[0],),
        )
        items = [
            {'product_id': i[0], 'name': i[1], 'image': i[2], 'quantity': i[3], 'unit_price': float(i[4])}
            for i in cur.fetchall()
        ]
        orders.append({
            'id': o[0],
            'user_id': o[1],
            'created_at': o[2].isoformat() if isinstance(o[2], datetime) else o[2],
            'status': o[3],
            'shipping_address': o[4],
            'total': float(o[5]),
            'items': items,
        })
    return orders


def release_stock(items):
    try:
        requests.post(f'{CATALOG_SERVICE_URL}/internal/stock/release', json={'items': items}, timeout=5)
    except requests.exceptions.RequestException:
        pass


def register_routes(app):
    @app.route('/orders', methods=['GET'])
    def list_orders():
        user_id, admin = current_user()
        if user_id is None:
            return jsonify({'error': 'Não autenticado'}), 401
        conn = get_db_connection()
        cur = conn.cursor()
        # Admins see every order; customers only their own
        orders = load_orders(cur) if admin else load_orders(cur, 'WHERE user_id = %s', (user_id,))
        cur.close()
        conn.close()
        return jsonify({'orders': orders})

    @app.route('/orders/<int:order_id>', methods=['GET'])
    def get_order(order_id):
        user_id, admin = current_user()
        conn = get_db_connection()
        cur = conn.cursor()
        orders = load_orders(cur, 'WHERE id = %s', (order_id,))
        cur.close()
        conn.close()
        if not orders or not (admin or orders[0]['user_id'] == user_id):
            return jsonify({'error': 'Pedido não encontrado'}), 404
        return jsonify(orders[0])

    @app.route('/orders', methods=['POST'])
    def create_order():
        user_id, _ = current_user()
        if user_id is None:
            return jsonify({'error': 'Não autenticado'}), 401
        data = request.get_json(silent=True) or {}
        lines = [
            {'product_id': i.get('product_id'), 'quantity': i.get('quantity', 1)}
            for i in data.get('items', []) if isinstance(i, dict)
        ]
        if not lines:
            return jsonify({'error': 'O pedido deve ter pelo menos um produto'}), 400

        # Reserve stock and take prices from the catalog (the client never sets prices)
        try:
            resp = requests.post(f'{CATALOG_SERVICE_URL}/internal/stock/reserve', json={'items': lines}, timeout=5)
        except requests.exceptions.RequestException:
            return jsonify({'error': 'Catálogo indisponível'}), 503
        if resp.status_code != 200:
            return jsonify(resp.json()), resp.status_code
        items = resp.json()['items']
        total = round(sum(i['quantity'] * i['unit_price'] for i in items), 2)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                'INSERT INTO orders (user_id, shipping_address, total) VALUES (%s, %s, %s)',
                (user_id, data.get('shipping_address', ''), total),
            )
            order_id = cur.lastrowid
            cur.executemany(
                'INSERT INTO order_items (order_id, product_id, name, image, quantity, unit_price) VALUES (%s, %s, %s, %s, %s, %s)',
                [(order_id, i['product_id'], i['name'], i['image'], i['quantity'], i['unit_price']) for i in items],
            )
            conn.commit()
            return jsonify(load_orders(cur, 'WHERE id = %s', (order_id,))[0]), 201
        except Exception:
            conn.rollback()
            release_stock(items)
            return jsonify({'error': 'Não foi possível registrar o pedido'}), 500
        finally:
            cur.close()
            conn.close()

    @app.route('/orders/<int:order_id>/status', methods=['PATCH'])
    def update_status(order_id):
        if not current_user()[1]:
            return jsonify({'error': 'Apenas administradores'}), 403
        status = (request.get_json(silent=True) or {}).get('status')
        if status not in STATUSES:
            return jsonify({'error': f"Status deve ser um de: {', '.join(STATUSES)}"}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            orders = load_orders(cur, 'WHERE id = %s', (order_id,))
            if not orders:
                return jsonify({'error': 'Pedido não encontrado'}), 404
            if status == 'cancelled' and orders[0]['status'] != 'cancelled':
                release_stock(orders[0]['items'])
            cur.execute('UPDATE orders SET status = %s WHERE id = %s', (status, order_id))
            conn.commit()
            return jsonify(load_orders(cur, 'WHERE id = %s', (order_id,))[0])
        finally:
            cur.close()
            conn.close()

    @app.route('/orders/<int:order_id>', methods=['DELETE'])
    def cancel_order(order_id):
        user_id, admin = current_user()
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            orders = load_orders(cur, 'WHERE id = %s', (order_id,))
            if not orders or not (admin or orders[0]['user_id'] == user_id):
                return jsonify({'error': 'Pedido não encontrado'}), 404
            if orders[0]['status'] not in CANCELLABLE:
                return jsonify({'error': 'Só é possível cancelar pedidos pendentes ou pagos'}), 409
            cur.execute("UPDATE orders SET status = 'cancelled' WHERE id = %s", (order_id,))
            conn.commit()
            release_stock(orders[0]['items'])
            return jsonify(load_orders(cur, 'WHERE id = %s', (order_id,))[0])
        finally:
            cur.close()
            conn.close()

    @app.route('/health', methods=['GET'])
    def health():
        try:
            conn = get_db_connection()
            conn.close()
        except Exception:
            return jsonify({'status': 'error', 'database': 'disconnected'}), 500
        try:
            catalog = requests.get(f'{CATALOG_SERVICE_URL}/health', timeout=2)
            catalog_status = 'online' if catalog.status_code == 200 else 'error'
        except requests.exceptions.RequestException:
            catalog_status = 'offline'
        return jsonify({'status': 'ok', 'database': 'connected', 'dependencies': {'catalog': catalog_status}}), 200
