from flask import Blueprint, jsonify, request
from config.db import get_db

# Crear blueprint
reviews_bp = Blueprint('reviews', __name__)


# crear review
@reviews_bp.route('/new', methods=['POST'])
def new_review():
    # obtener datos
    data = request.get_json()

    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    service_id = data.get('service_id')
    user_id = data.get('user_id')
    rating = data.get('rating')
    comment = data.get('comment')

    # validación
    if not service_id or not user_id or not rating or not comment:
        return jsonify({"error": "Faltan datos para crear la reseña"}), 400

    # checar si existe el usuario
    if not db.users.find_one({"user_id": user_id}):
        return jsonify({"error": "El usuario no existe"}), 400

    # checar si existe el servicio
    if not db.services.find_one({"service_id": service_id}):
        return jsonify({"error": "El servicio no existe"}), 400

    # checar que el rating esté entre 1 y 5
    if rating < 1 or rating > 5:
        return jsonify({"error": "El rating debe estar entre 1 y 5"}), 400

    # crear review
    review = {
        "service_id": service_id,
        "user_id": user_id,
        "rating": rating,
        "comment": comment
    }

    db.reviews.insert_one(review)

    return jsonify({"mensaje": "Reseña creada"}), 201


# obtener reviews de un servicio
@reviews_bp.route('/service/<service_id>', methods=['GET'])
def get_reviews_by_service(service_id):
    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    # checar si existe el servicio
    if not db.services.find_one({"service_id": service_id}):
        return jsonify({"error": "El servicio no existe"}), 400

    # obtener reviews sin imprimir _id
    reviews = list(db.reviews.find({"service_id": service_id}, {'_id': 0}))

    return jsonify(reviews), 200


# obtener reviews de un usuario
@reviews_bp.route('/user/<user_id>', methods=['GET'])
def get_reviews_by_user(user_id):
    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    # checar si existe el usuario
    if not db.users.find_one({"user_id": user_id}):
        return jsonify({"error": "El usuario no existe"}), 400

    # obtener reviews sin imprimir _id
    reviews = list(db.reviews.find({"user_id": user_id}, {'_id': 0}))

    return jsonify(reviews), 200

# update review


@reviews_bp.route('/<review_id>', methods=['PUT'])
def update_review(review_id):
    # obtener datos
    data = request.get_json()

    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    rating = data.get('rating')
    comment = data.get('comment')

    # validación de datos necesarios
    if not rating or not comment:
        return jsonify({"error": "Faltan datos para actualizar la reseña"}), 400

    # checar si existe el id
    if not db.reviews.find_one({"_id": review_id}):
        return jsonify({"error": "La reseña no existe"}), 400

    # actualizar review
    db.reviews.update_one({"_id": review_id}, {
                          "$set": {"rating": rating, "comment": comment}})

    return jsonify({"mensaje": "Reseña actualizada"}), 200

# borrar review


@reviews_bp.route('/<review_id>', methods=['DELETE'])
def delete_review(review_id):
    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    # checar si existe el id
    if not db.reviews.find_one({"_id": review_id}):
        return jsonify({"error": "La reseña no existe"}), 400

    # borrar review
    db.reviews.delete_one({"_id": review_id})

    return jsonify({"mensaje": "Reseña eliminada"}), 200
