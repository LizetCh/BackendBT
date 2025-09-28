from flask import Flask, jsonify
import os
from dotenv import load_dotenv
from routes.categories import categories_bp
from routes.users import users_bp
from routes.services import services_bp
from routes.test_db import test_bp
from routes.transactions import transactions_bp
from routes.reviews import reviews_bp
from flask_jwt_extended import JWTManager 
from flask_cors import CORS

load_dotenv()

def create_app():
    app = Flask(__name__)

    # Configuración JWT
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET')  
    app.config['JWT_TOKEN_LOCATION'] = ['headers']  

    # Inicializar JWT
    JWTManager(app)

    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(services_bp, url_prefix='/api/services')
    app.register_blueprint(reviews_bp,url_prefix='/api/reviews')
    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    #Prueba la conexión a la db
    app.register_blueprint(test_bp, url_prefix='/api/test')

    return app

app = create_app()
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
