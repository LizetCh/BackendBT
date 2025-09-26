from flask import Blueprint, jsonify, request 
from config.db import get_db
from functools import wraps 
from datetime import datetime, timedelta
from bson import ObjectId 
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
import os

users_bp = Blueprint('users', __name__)

def serialize_doc(doc):
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc

# CREAR USUARIO - en la colección 'usuarios'
@users_bp.route('/create', methods=['POST'])
def create_user():
    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not all([name, email, password]):
        return jsonify({"error": "name, email y password son requeridos"}), 400

    try:
        # ✅ BUSCAR en la colección 'usuarios'
        if db.usuarios.find_one({"email": email}):
            return jsonify({"error": "El email ya está registrado"}), 409

        user_doc = {
            "name": name,
            "email": email,
            "phone": (data.get("phone") or "").strip() or None,
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

        # ✅ INSERTAR en la colección 'usuarios'
        result = db.usuarios.insert_one(user_doc)
        new_user = db.usuarios.find_one({"_id": result.inserted_id})

        token = jwt.encode({
            'user_id': str(result.inserted_id),
            'exp': datetime.utcnow() + timedelta(days=30)
        }, os.getenv('JWT_SECRET', 'lunas'), algorithm='HS256')

        return jsonify({
            "message": "Usuario creado exitosamente",
            "user": serialize_doc(new_user),
            "token": token
        }), 201

    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500

# LOGIN - desde la colección 'usuarios'
@users_bp.route('/login', methods=['POST'])
def login():
    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"error": "Email y password son requeridos"}), 400

    try:
        # ✅ BUSCAR en la colección 'usuarios'
        user = db.usuarios.find_one({"email": email, "is_active": True})
        
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Credenciales inválidas"}), 401

        token = jwt.encode({
            'user_id': str(user['_id']),
            'exp': datetime.utcnow() + timedelta(days=30)
        }, os.getenv('JWT_SECRET', 'lunas'), algorithm='HS256')

        return jsonify({
            "message": "Login exitoso",
            "user": serialize_doc(user),
            "token": token
        })

    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500

# Obtener perfil - desde 'usuarios'
@users_bp.route('/profile', methods=['GET'])
def get_profile():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({"error": "Token requerido"}), 401

    try:
        data = jwt.decode(token, os.getenv('JWT_SECRET', 'lunas'), algorithms=['HS256'])
        db = get_db()
        
        if db is None:
            return jsonify({"error": "Base de datos no disponible"}), 500

        # ✅ BUSCAR en la colección 'usuarios'
        user = db.usuarios.find_one({"_id": ObjectId(data['user_id'])})
        
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        return jsonify({"user": serialize_doc(user)})

    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 401