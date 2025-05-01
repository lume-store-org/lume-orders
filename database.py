import os
import mysql.connector

def get_db_connection():
    """Estabelece e retorna uma conexão com o banco de dados MySQL"""
    db_host = os.environ.get('DB_HOST', 'mysql-pedidos')
    db_name = os.environ.get('DB_NAME', 'pedidos_db')
    db_user = os.environ.get('DB_USER', 'root')
    db_password = os.environ.get('DB_PASSWORD', 'root')
    
    conn = mysql.connector.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password
    )
    
    return conn