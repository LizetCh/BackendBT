from flask import Blueprint, jsonify, request
from config.db import get_db
from bson import ObjectId 

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

    try:
        # Validar que los IDs sean ObjectIds válidos
        service_obj_id = ObjectId(service_id)
        user_obj_id = ObjectId(user_id)
    except:
        return jsonify({"error": "IDs inválidos"}), 400

    # checar si existe el usuario
    if not db.users.find_one({"_id": user_obj_id}):
        return jsonify({"error": "El usuario no existe"}), 400

    # checar si existe el servicio (CORREGIDO: _id no service_id)
    if not db.services.find_one({"_id": service_obj_id}):
        return jsonify({"error": "El servicio no existe"}), 400

    # checar que el rating esté entre 1 y 5
    if rating < 1 or rating > 5:
        return jsonify({"error": "El rating debe estar entre 1 y 5"}), 400

    # crear review (USANDO ObjectIds)
    review = {
        "service_id": service_obj_id,
        "user_id": user_obj_id,
        "rating": rating,
        "comment": comment
    }

    result = db.reviews.insert_one(review)

    return jsonify({
        "mensaje": "Reseña creada",
        "review_id": str(result.inserted_id)
    }), 201


# obtener reviews de un servicio
@reviews_bp.route('/service/<service_id>', methods=['GET'])
def get_reviews_by_service(service_id):
    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        service_obj_id = ObjectId(service_id)
    except:
        return jsonify({"error": "ID de servicio inválido"}), 400

    # checar si existe el servicio (CORREGIDO)
    if not db.services.find_one({"_id": service_obj_id}):
        return jsonify({"error": "El servicio no existe"}), 400

    # obtener reviews (USANDO ObjectId)
    reviews = list(db.reviews.find({"service_id": service_obj_id}, {'_id': 0}))

    # Convertir ObjectIds a strings para JSON
    for review in reviews:
        review['service_id'] = str(review['service_id'])
        review['user_id'] = str(review['user_id'])

    return jsonify(reviews), 200


# obtener reviews de un usuario
@reviews_bp.route('/user/<user_id>', methods=['GET'])
def get_reviews_by_user(user_id):
    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        user_obj_id = ObjectId(user_id)
    except:
        return jsonify({"error": "ID de usuario inválido"}), 400

    # checar si existe el usuario (CORREGIDO)
    if not db.users.find_one({"_id": user_obj_id}):
        return jsonify({"error": "El usuario no existe"}), 400

    # obtener reviews (USANDO ObjectId)
    reviews = list(db.reviews.find({"user_id": user_obj_id}, {'_id': 0}))

    # Convertir ObjectIds a strings para JSON
    for review in reviews:
        review['service_id'] = str(review['service_id'])
        review['user_id'] = str(review['user_id'])

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

    try:
        review_obj_id = ObjectId(review_id)
    except:
        return jsonify({"error": "ID de reseña inválido"}), 400

    # checar si existe el id (CORREGIDO: usando ObjectId)
    if not db.reviews.find_one({"_id": review_obj_id}):
        return jsonify({"error": "La reseña no existe"}), 400

    # actualizar review (CORREGIDO: usando ObjectId)
    db.reviews.update_one({"_id": review_obj_id}, {
                          "$set": {"rating": rating, "comment": comment}})

    return jsonify({"mensaje": "Reseña actualizada"}), 200

# borrar review
@reviews_bp.route('/<review_id>', methods=['DELETE'])
def delete_review(review_id):
    # obtener base de datos
    db = get_db()

    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        review_obj_id = ObjectId(review_id)
    except:
        return jsonify({"error": "ID de reseña inválido"}), 400

    # checar si existe el id (CORREGIDO: usando ObjectId)
    if not db.reviews.find_one({"_id": review_obj_id}):
        return jsonify({"error": "La reseña no existe"}), 400

    # borrar review (CORREGIDO: usando ObjectId)
    db.reviews.delete_one({"_id": review_obj_id})

    return jsonify({"mensaje": "Reseña eliminada"}), 200