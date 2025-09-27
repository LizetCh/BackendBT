from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.db import get_db
from bson import ObjectId
from datetime import datetime

# Crear blueprint
services_bp = Blueprint('services', __name__)

# Serialización de servicios
def serialize_service(service):
    if service and '_id' in service:
        service = service.copy()
        service['_id'] = str(service['_id'])
        service['owner_id'] = str(service['owner_id'])
    for key, value in service.items():
        if isinstance(value, datetime):
            service[key] = value.isoformat()
    return service

# Crear servicio
@services_bp.route('/crear', methods=['POST'])
@jwt_required()
def create_service():
    current_user = get_jwt_identity()
    data = request.get_json() or {}

    # Validación de campos requeridos
    required_fields = ['title', 'description', 'category', 'hours', 'contact', 'location']
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return jsonify({"error": f"Faltan campos: {', '.join(missing)}"}), 400

    # Validación de horas
    try:
        hours = float(data['hours'])
        if hours <= 0:
            return jsonify({"error": "El valor de 'hours' debe ser mayor a 0"}), 400
    except ValueError:
        return jsonify({"error": "'hours' debe ser un número válido"}), 400

    db = get_db()
    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        # Verificar que el usuario existe
        user = db.usuarios.find_one({"_id": ObjectId(current_user)})
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Validación de categoría (comentada, activar si decides usar tabla de categorías)
        # if not db.categories.find_one({"name": data['category'].strip()}):
        #     return jsonify({"error": f"La categoría '{data['category']}' no existe"}), 400

        # Crear servicio
        service_doc = {
            "owner_id": ObjectId(current_user),
            "title": data['title'].strip(),
            "description": data['description'].strip(),
            "category": data['category'].strip(),
            "hours": hours,
            "contact": data['contact'].strip(),
            "date_created": datetime.utcnow(),
            "location": data['location'].strip()
        }

        result = db.services.insert_one(service_doc)
        new_service = db.services.find_one({"_id": result.inserted_id})

        return jsonify({
            "message": "Servicio creado exitosamente",
            "service": serialize_service(new_service)
        }), 201

    except Exception as e:
        return jsonify({"error": f"Error al crear servicio: {str(e)}"}), 500

# Obtener todos los servicios
@services_bp.route('/', methods=['GET'])
def get_all_services():
    db = get_db()
    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    services = list(db.services.find())
    return jsonify([serialize_service(s) for s in services]), 200

# Obtener servicios de un usuario
@services_bp.route('/user/<user_id>', methods=['GET'])
def get_services_by_user(user_id):
    db = get_db()
    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    services = list(db.services.find({"owner_id": ObjectId(user_id)}))
    return jsonify([serialize_service(s) for s in services]), 200

# Actualizar servicio
@services_bp.route('/<service_id>', methods=['PUT'])
@jwt_required()
def update_service(service_id):
    current_user = get_jwt_identity()
    data = request.get_json() or {}
    db = get_db()
    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    service = db.services.find_one({"_id": ObjectId(service_id)})
    if not service:
        return jsonify({"error": "Servicio no encontrado"}), 404

    if str(service['owner_id']) != current_user:
        return jsonify({"error": "No tienes permisos para actualizar este servicio"}), 403

    update_fields = {}

    if 'title' in data:
        update_fields['title'] = data['title'].strip()
    if 'description' in data:
        update_fields['description'] = data['description'].strip()
    if 'category' in data:
        update_fields['category'] = data['category'].strip()
        # Validar categoría si es necesario
        # if not db.categories.find_one({"name": data['category'].strip()}):
        #     return jsonify({"error": f"La categoría '{data['category']}' no existe"}), 400
    if 'hours' in data:
        try:
            hours = float(data['hours'])
            if hours <= 0:
                return jsonify({"error": "El valor de 'hours' debe ser mayor a 0"}), 400
            update_fields['hours'] = hours
        except ValueError:
            return jsonify({"error": "'hours' debe ser un número válido"}), 400
    if 'contact' in data:
        update_fields['contact'] = data['contact'].strip()
    if 'location' in data:
        update_fields['location'] = data['location'].strip()

    if not update_fields:
        return jsonify({"error": "No hay campos para actualizar"}), 400

    try:
        db.services.update_one({"_id": ObjectId(service_id)}, {"$set": update_fields})
        updated_service = db.services.find_one({"_id": ObjectId(service_id)})
        return jsonify({"message": "Servicio actualizado", "service": serialize_service(updated_service)}), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar servicio: {str(e)}"}), 500

# Eliminar servicio
@services_bp.route('/<service_id>', methods=['DELETE'])
@jwt_required()
def delete_service(service_id):
    current_user = get_jwt_identity()
    db = get_db()
    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    service = db.services.find_one({"_id": ObjectId(service_id)})
    if not service:
        return jsonify({"error": "Servicio no encontrado"}), 404

    if str(service['owner_id']) != current_user:
        return jsonify({"error": "No tienes permisos para eliminar este servicio"}), 403

    try:
        db.services.delete_one({"_id": ObjectId(service_id)})
        return jsonify({"message": "Servicio eliminado"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al eliminar servicio: {str(e)}"}), 500
