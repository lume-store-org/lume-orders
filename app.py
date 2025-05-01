from flask import Flask, jsonify, request
from flask_cors import CORS
from routes import register_routes
import os
import logging
from database import get_db_connection

# Configurar logging para minimizar mensagens
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
# Configurações para garantir UTF-8 no Flask
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'

# Desativar o modo debug e reduzir logs
app.logger.setLevel(logging.ERROR)

# Restringir CORS para aceitar apenas requisições do API Gateway
CORS(app, resources={r"/*": {"origins": ["http://localhost:5000", "http://api-gateway:5000"]}})

# Rota de verificação de saúde
@app.route('/health', methods=['GET'])
def health_check():
    try:
        # Versão simplificada sem verificar o banco de dados
        return jsonify({"status": "ok", "message": "Serviço de Pedidos operacional"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Registrar todas as rotas da aplicação
register_routes(app)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port, debug=False)