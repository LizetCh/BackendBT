from flask import Flask
import os
from dotenv import load_dotenv
from routes.categories import categories_bp


load_dotenv()


def create_app():
    app = Flask(__name__)

    # registrar blueprints
    app.register_blueprint(categories_bp, url_prefix='/categories')

    return app


# correr la app
app = create_app()
if __name__ == '__main__':

    port = int(os.getenv('PORT', 8080))

    app.run(host='0.0.0.0', port=port, debug=True)
