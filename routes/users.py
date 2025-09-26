from flask import Blueprint, jsonify, request 
from config.db import get_db
from functools import wraps 
from datetime import datetime, timedelta
from bson import ObjectId 
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
import os

users_bp = Blueprint('users', __name__)

# Helper para serializar ObjectId
def serialize_doc(doc):
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc

# Decorador para rutas que requieren autenticación
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({"error": "Token es requerido"}), 401
        
        try:
            # Remover 'Bearer ' del token
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, os.getenv('JWT_SECRET', 'secret_key'), algorithms=['HS256'])
            
            # Obtener la base de datos dentro de la función
            db = get_db()
            if db is None:
                return jsonify({"error": "Base de datos no disponible"}), 500
                
            current_user = db.users.find_one({"_id": ObjectId(data['user_id'])})
            
            if not current_user:
                return jsonify({"error": "Usuario no válido"}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# Crear usuario - VERSIÓN CORREGIDA
@users_bp.route('/create', methods=['POST'])
def create_user():
    # Obtener la conexión a la base de datos
    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = data.get("password")

    # Validaciones básicas
    if not all([name, email, password]):
        return jsonify({"error": "name, email y password son requeridos"}), 400

    if len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400

    try:
        # Verificar si el usuario ya existe
        if db.users.find_one({"email": email}):
            return jsonify({"error": "El email ya está registrado"}), 409

        user_doc = {
            "name": name,
            "email": email,
            "phone": phone or None,
            "password_hash": generate_password_hash(password),
            "bio": data.get("bio", ""),
            "skills": data.get("skills", []),
            "rating_avg": 0.0,
            "rating_count": 0,
            "hours_balance": 0.0,
            "role": "user",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = db.users.insert_one(user_doc)
        new_user = db.users.find_one({"_id": result.inserted_id})

        # Generar token JWT
        token = jwt.encode({
            'user_id': str(result.inserted_id),
            'exp': datetime.utcnow() + timedelta(days=30)
        }, os.getenv('JWT_SECRET', 'secret_key'), algorithm='HS256')

        return jsonify({
            "message": "Usuario creado exitosamente",
            "user": {
                "id": str(result.inserted_id),
                "name": name,
                "email": email,
                "bio": new_user.get("bio", ""),
                "skills": new_user.get("skills", [])
            },
            "token": token
        }), 201

    except Exception as e:
        return jsonify({"error": f"Error en la base de datos: {str(e)}"}), 500

# Login de usuario - VERSIÓN CORREGIDA
@users_bp.route('/login', methods=['POST'])
def login():
    # Obtener la conexión a la base de datos
    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"error": "Email y password son requeridos"}), 400

    try:
        user = db.users.find_one({"email": email, "is_active": True})
        
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Credenciales inválidas"}), 401

        # Generar token JWT
        token = jwt.encode({
            'user_id': str(user['_id']),
            'exp': datetime.utcnow() + timedelta(days=30)
        }, os.getenv('JWT_SECRET', 'secret_key'), algorithm='HS256')

        return jsonify({
            "message": "Login exitoso",
            "user": {
                "id": str(user['_id']),
                "name": user['name'],
                "email": user['email'],
                "bio": user.get("bio", ""),
                "skills": user.get("skills", []),
                "rating_avg": user.get("rating_avg", 0.0),
                "hours_balance": user.get("hours_balance", 0.0)
            },
            "token": token
        })
    except Exception as e:
        return jsonify({"error": f"Error en la base de datos: {str(e)}"}), 500

# Obtener perfil del usuario autenticado - VERSIÓN CORREGIDA
@users_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({
        "user": serialize_doc(current_user)
    })

# Actualizar perfil de usuario - VERSIÓN CORREGIDA
@users_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    # Obtener la conexión a la base de datos
    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    data = request.get_json() or {}
    
    update_data = {
        "name": data.get("name", current_user['name']).strip(),
        "bio": data.get("bio", current_user.get("bio", "")),
        "skills": data.get("skills", current_user.get("skills", [])),
        "phone": data.get("phone", current_user.get("phone", "")).strip(),
        "updated_at": datetime.utcnow()
    }

    # Si se proporciona nueva contraseña
    if data.get("new_password"):
        if not data.get("current_password"):
            return jsonify({"error": "Contraseña actual requerida"}), 400
        
        if not check_password_hash(current_user['password_hash'], data['current_password']):
            return jsonify({"error": "Contraseña actual incorrecta"}), 401
        
        update_data["password_hash"] = generate_password_hash(data['new_password'])

    try:
        db.users.update_one(
            {"_id": current_user['_id']},
            {"$set": update_data}
        )

        updated_user = db.users.find_one({"_id": current_user['_id']})
        return jsonify({
            "message": "Perfil actualizado",
            "user": serialize_doc(updated_user)
        })
    except Exception as e:
        return jsonify({"error": f"Error al actualizar perfil: {str(e)}"}), 500