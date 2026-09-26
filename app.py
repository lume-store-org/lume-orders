import logging

from flask import Flask

from routes import register_routes

logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)
app.json.ensure_ascii = False

register_routes(app)
