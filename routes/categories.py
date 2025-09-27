from bson import ObjectId
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


# obtener todas las categorías
@categories_bp.route('/', methods=['GET'])
def get_categories():
    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    # obtener categorias sin imprimir _id
    categories = list(db.categories.find({}, {'_id': 0}))

    return jsonify(categories), 200

# actualizar categoría


@categories_bp.route('/<category_id>', methods=['PUT'])
def update_category(category_id):
    # obtener datos
    data = request.get_json()

    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    name = data.get('name')

    # validación de datos necesarios
    if not name:
        return jsonify({"error": "Falta nombre de la categoría"}), 400

    # evitar actualizar con un nombre que ya existe que no esté con el mismo id
    if db.categories.find_one({"name": name, "_id": {"$ne": ObjectId(category_id)}}):
        return jsonify({"error": "La categoría ya existe"}), 400

    # checar si existe el id
    match = db.categories.find_one({"_id": ObjectId(category_id)}, {'_id': 0})
    if not match:
        return jsonify({"error": "Categoría no encontrada"}), 404

    # actualizar categoría
    db.categories.update_one(
        {"_id": category_id},  # filter
        {"$set": {"name": name}}
    )

    return jsonify({"mensaje": "Categoría actualizada"}), 200


# eliminar categoría
@categories_bp.route('/<category_id>', methods=['DELETE'])
def delete_category(category_id):
    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    # checar si existe el id
    match = db.categories.find_one({"_id": ObjectId(category_id)}, {'_id': 0})
    if not match:
        return jsonify({"error": "Categoría no encontrada"}), 404

    # eliminar categoría
    db.categories.delete_one({"_id": ObjectId(category_id)})

    return jsonify({"mensaje": "Categoría eliminada"}), 200
