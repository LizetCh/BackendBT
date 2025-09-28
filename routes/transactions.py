from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config.db import get_db
from bson import ObjectId
from datetime import datetime

transactions_bp = Blueprint('transactions', __name__)

# Serialización de transacciones
def serialize_transaction(transaction):
    transaction = transaction.copy()
    transaction['_id'] = str(transaction['_id'])
    transaction['service_id'] = str(transaction['service_id'])
    transaction['supplier_id'] = str(transaction['supplier_id'])
    transaction['client_id'] = str(transaction['client_id'])
    for key, value in transaction.items():
        if isinstance(value, datetime):
            transaction[key] = value.isoformat()
    return transaction

# Crear transacción
@transactions_bp.route('/create', methods=['POST'])
@jwt_required()
def create_transaction():
    supplier_id = get_jwt_identity()  # proveedor inicia
    data = request.get_json() or {}

    required_fields = ['service_id', 'client_id', 'hours']
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({"error": f"Faltan campos: {', '.join(missing)}"}), 400

    db = get_db()
    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        service_id = ObjectId(data['service_id'])
        client_id = ObjectId(data['client_id'])
        supplier_id_obj = ObjectId(supplier_id)
        hours = float(data['hours'])
        if hours <= 0:
            return jsonify({"error": "Las horas deben ser mayores a 0"}), 400
    except Exception:
        return jsonify({"error": "ID o valor de horas inválido"}), 400

    service = db.services.find_one({"_id": service_id})
    client = db.usuarios.find_one({"_id": client_id})
    supplier = db.usuarios.find_one({"_id": supplier_id_obj})

    if not service:
        return jsonify({"error": "Servicio no encontrado"}), 404
    if not client or not supplier:
        return jsonify({"error": "Proveedor o cliente no encontrado"}), 404

    # Validar horas del cliente
    if client['hours_balance'] < hours:
        return jsonify({"error": "El cliente no tiene horas suficientes para la transacción"}), 400

    transaction_doc = {
        "service_id": service_id,
        "supplier_id": supplier_id_obj,
        "client_id": client_id,
        "hours": hours,
        "status_supplier": "accepted",  # proveedor acepta automáticamente
        "status_client": "pending",
        "status_transaction": "pending",
        "created_at": datetime.utcnow()
    }

    try:
        result = db.transactions.insert_one(transaction_doc)
        new_transaction = db.transactions.find_one({"_id": result.inserted_id})
        return jsonify({
            "message": "Transacción creada, pendiente de aceptación del cliente",
            "transaction": serialize_transaction(new_transaction)
        }), 201
    except Exception as e:
        return jsonify({"error": f"Error al crear transacción: {str(e)}"}), 500


# Actualizar transacción
@transactions_bp.route('/<transaction_id>', methods=['PUT'])
@jwt_required()
def update_transaction(transaction_id):
    current_user = get_jwt_identity()
    data = request.get_json() or {}
    db = get_db()
    if db is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        trans_id = ObjectId(transaction_id)
        user_id = ObjectId(current_user)
    except Exception:
        return jsonify({"error": "ID inválido"}), 400

    transaction = db.transactions.find_one({"_id": trans_id})
    if not transaction:
        return jsonify({"error": "Transacción no encontrada"}), 404

    update_fields = {}

    # Supplier solo puede actualizar status_supplier (ya aceptado automáticamente)
    if 'status_supplier' in data:
        return jsonify({"error": "El proveedor ya inició la transacción"}), 400

    # Client solo puede actualizar status_client
    if 'status_client' in data and str(transaction['client_id']) == str(current_user):
        if data['status_client'] not in ['accepted', 'rejected']:
            return jsonify({"error": "status_client inválido"}), 400

        client = db.usuarios.find_one({"_id": ObjectId(transaction['client_id'])})
        supplier = db.usuarios.find_one({"_id": ObjectId(transaction['supplier_id'])})

        if data['status_client'] == 'accepted':
            # Validar horas nuevamente
            if client['hours_balance'] < transaction['hours']:
                return jsonify({"error": "Horas insuficientes para completar la transacción"}), 400
            # Transferir horas
            db.usuarios.update_one(
                {"_id": client['_id']},
                {"$inc": {"hours_balance": -transaction['hours']}}
            )
            db.usuarios.update_one(
                {"_id": supplier['_id']},
                {"$inc": {"hours_balance": transaction['hours']}}
            )
            update_fields['status_client'] = 'accepted'
        elif data['status_client'] == 'rejected':
            update_fields['status_client'] = 'rejected'

    # Actualizar status_transaction
    if update_fields.get('status_client') == 'accepted':
        update_fields['status_transaction'] = 'completed'
    elif update_fields.get('status_client') == 'rejected':
        update_fields['status_transaction'] = 'cancelled'

    if not update_fields:
        return jsonify({"error": "No hay campos para actualizar o no tienes permisos"}), 400

    try:
        db.transactions.update_one({"_id": trans_id}, {"$set": update_fields})
        updated_transaction = db.transactions.find_one({"_id": trans_id})
        return jsonify({
            "message": "Transacción actualizada",
            "transaction": serialize_transaction(updated_transaction)
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar transacción: {str(e)}"}), 500
    
# Obtener transacciones del usuario
@transactions_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user_transactions():
    current_user = get_jwt_identity()
    db = get_db()
    try:
        user_id = ObjectId(current_user)
    except Exception:
        return jsonify({"error": "ID de usuario inválido"}), 400

    transactions = list(db.transactions.find({
        "$or": [{"client_id": user_id}, {"supplier_id": user_id}]
    }))
    return jsonify([serialize_transaction(t) for t in transactions]), 200

# Obtener transacciones de un servicio
@transactions_bp.route('/service/<service_id>', methods=['GET'])
@jwt_required()
def get_service_transactions(service_id):
    db = get_db()
    try:
        svc_id = ObjectId(service_id)
    except Exception:
        return jsonify({"error": "ID de servicio inválido"}), 400

    transactions = list(db.transactions.find({"service_id": svc_id}))
    return jsonify([serialize_transaction(t) for t in transactions]), 200

# Admin: obtener todas las transacciones
@transactions_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_transactions():
    current_user = get_jwt_identity()
    db = get_db()
    try:
        user_id = ObjectId(current_user)
    except Exception:
        return jsonify({"error": "ID de usuario inválido"}), 400

    user = db.usuarios.find_one({"_id": user_id})
    if not user or user.get('role') != 'admin':
        return jsonify({"error": "No autorizado"}), 403

    transactions = list(db.transactions.find())
    return jsonify([serialize_transaction(t) for t in transactions]), 200

# Admin: eliminar transacción
@transactions_bp.route('/<transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction(transaction_id):
    current_user = get_jwt_identity()
    db = get_db()
    try:
        user_id = ObjectId(current_user)
        trans_id = ObjectId(transaction_id)
    except Exception:
        return jsonify({"error": "ID inválido"}), 400

    user = db.usuarios.find_one({"_id": user_id})
    if not user or user.get('role') != 'admin':
        return jsonify({"error": "No autorizado"}), 403

    transaction = db.transactions.find_one({"_id": trans_id})
    if not transaction:
        return jsonify({"error": "Transacción no encontrada"}), 404

    db.transactions.delete_one({"_id": trans_id})
    return jsonify({"message": "Transacción eliminada"}), 200
