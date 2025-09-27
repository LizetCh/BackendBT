from flask import Flask, jsonify
import os
from dotenv import load_dotenv
from routes.categories import categories_bp
from routes.users import users_bp
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

    return app

app = create_app()
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
