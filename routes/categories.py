from flask import Blueprint, jsonify, request
from config.db import get_db

# Crear blueprint
categories_bp = Blueprint('categories', __name__)

# Crear categoría


@categories_bp.route('/new', methods=['POST'])
def new_category():
    # obtener datos
    data = request.get_json()

    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    print(type(db))

    name = data.get('name')

    # validación
    if not name:
        return jsonify({"error": "Falta nombre de la categoría"}), 400

    # evitar duplicados
    if db.categories.find_one({"name": name}):
        return jsonify({"error": "La categoría ya existe"}), 400

    # crear categoría
    category = {
        "name": name
    }

    db.categories.insert_one(category)

    return jsonify({"mensaje": "Categoría creada"}), 201
