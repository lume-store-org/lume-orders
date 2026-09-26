import os

import mysql.connector


def get_db_connection():
    """Conexão com o MySQL do serviço. Credenciais vêm só das variáveis de ambiente."""
    return mysql.connector.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        charset='utf8mb4',
        collation='utf8mb4_unicode_ci',
    )
