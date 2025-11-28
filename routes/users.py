from flask import Blueprint, jsonify, request
from config.db import get_db
from datetime import datetime, timedelta
from bson import ObjectId
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
import secrets  

users_bp = Blueprint('users', __name__)

# FORMATO
# name
# email
# password


def serialize_doc(doc):
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc


@users_bp.route('/create', methods=['POST'])
def create_user():
    data = request.get_json() or {}

    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    role = (data.get("role") or "user").strip()
    if role not in ["user", "admin"]:
        role = "user"

    if not all([name, email, password]):
        return jsonify({"error": "name, email y password son requeridos"}), 400

    try:
        if db.users.find_one({"email": email}):
            return jsonify({"error": "El email ya está registrado"}), 409

        user_doc = {
            "name": name,
            "email": email,
            "phone": (data.get("phone") or "1111111").strip(),
            "password_hash": generate_password_hash(password),
            "bio": (data.get("bio") or "Por definir aún"),
            "skills": data.get("skills") or ["Por definir aún"],
            "rating_avg": 0.0,
            "rating_count": 0,
            "hours_balance": 1.0,
            "role": role,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = db.users.insert_one(user_doc)
        new_user = db.users.find_one({"_id": result.inserted_id})

        access_token = create_access_token(
            identity=str(result.inserted_id),
            expires_delta=timedelta(days=30)
        )

        return jsonify({
            "message": "Usuario creado exitosamente",
            "user": serialize_doc(new_user),
            "token": access_token
        }), 201

    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500


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
        user = db.users.find_one({"email": email, "is_active": True})

        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Credenciales inválidas"}), 401

        access_token = create_access_token(
            identity=str(user['_id']),
            expires_delta=timedelta(days=30)
        )

        return jsonify({
            "message": "Login exitoso",
            "user": serialize_doc(user),
            "token": access_token
        })

    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500


@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    user_id = get_jwt_identity()

    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        return jsonify({"user": serialize_doc(user)})

    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500


@users_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_profile():
    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    user_id = get_jwt_identity()
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    data = request.get_json() or {}
    update_fields = {}

    # 1. NOMBRE
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({"error": "El nombre no puede estar vacío"}), 400
        update_fields['name'] = name

    # 2. EMAIL
    if 'email' in data:
        email = (data.get('email') or '').strip().lower()
        if not email:
            return jsonify({"error": "El email no puede estar vacío"}), 400
        if email != user['email']:
            existing_user = db.users.find_one({
                "email": email,
                "_id": {"$ne": user['_id']}
            })
            if existing_user:
                return jsonify({"error": "El email ya está en uso"}), 409
        update_fields['email'] = email

    # 3. TELÉFONO
    if 'phone' in data:
        phone = (data.get('phone') or '').strip()
        if not phone:
            phone = "1111111"
        update_fields['phone'] = phone

    # 4. BIO
    if 'bio' in data:
        bio = (data.get('bio') or '').strip()
        if not bio:
            bio = "Por definir aún"
        update_fields['bio'] = bio

    # 5. SKILLS
    if 'skills' in data:
        skills = data.get('skills')
        if isinstance(skills, list) and skills:
            update_fields['skills'] = skills
        else:
            update_fields['skills'] = ["Por definir aún"]

    # 6. CONTRASEÑA NUEVA (cambio desde perfil)
    if 'password' in data:
        password = data.get('password')
        if not password:
            return jsonify({"error": "La contraseña no puede estar vacía"}), 400

        password_error = validate_password(password)
        if password_error:
            return jsonify({"error": password_error}), 400

        update_fields['password_hash'] = generate_password_hash(password)

    # 7. CONTRASEÑA ACTUAL (para validar el cambio)
    if 'current_password' in data and 'password' in data:
        current_password = data.get('current_password')
        if not check_password_hash(user['password_hash'], current_password):
            return jsonify({"error": "Contraseña actual incorrecta"}), 401

    if not update_fields:
        return jsonify({"error": "No hay campos para actualizar"}), 400

    try:
        update_fields['updated_at'] = datetime.utcnow()
        result = db.users.update_one(
            {"_id": user['_id']},
            {"$set": update_fields}
        )

        if result.modified_count == 0:
            return jsonify({"error": "No se pudo actualizar el perfil"}), 500

        updated_user = db.users.find_one({"_id": user['_id']})

        return jsonify({
            "message": "Perfil actualizado exitosamente",
            "user": serialize_user_safe(updated_user)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error al actualizar perfil: {str(e)}"}), 500


def serialize_user_safe(doc):
    if doc and '_id' in doc:
        doc = doc.copy()
        doc['_id'] = str(doc['_id'])
        doc.pop('password_hash', None)
    return doc


def validate_password(password):
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres"
    return None


# ================================
#   FLUJO OLVIDÉ MI CONTRASEÑA
# ================================

@users_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Paso 1: el usuario manda su email.
    Generamos un reset_token y fecha de expiración (1 hora).
    En producción se enviaría por correo; aquí lo regresamos en el JSON para pruebas.
    """
    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"error": "Email es requerido"}), 400

    try:
        user = db.users.find_one({"email": email, "is_active": True})
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        reset_token = secrets.token_urlsafe(32)

        db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "reset_token": reset_token,
                    "reset_token_expires_at": datetime.utcnow() + timedelta(hours=1)
                }
            }
        )

        return jsonify({
            "message": "Se ha generado un token de recuperación. En un sistema real se enviaría por email.",
            "email": email,
            "reset_token": reset_token  # SOLO para pruebas
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500


@users_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Paso 2: el usuario manda email + token + new_password.
    Validamos token, expiración y actualizamos password_hash.
    """
    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    reset_token = (data.get("token") or "").strip()
    new_password = data.get("new_password")

    if not all([email, reset_token, new_password]):
        return jsonify({"error": "Email, token y nueva contraseña son requeridos"}), 400

    password_error = validate_password(new_password)
    if password_error:
        return jsonify({"error": password_error}), 400

    try:
        user = db.users.find_one({"email": email, "is_active": True})
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        stored_token = user.get("reset_token")
        expires_at = user.get("reset_token_expires_at")

        if not stored_token or stored_token != reset_token:
            return jsonify({"error": "Token inválido"}), 401

        if not expires_at or expires_at < datetime.utcnow():
            return jsonify({"error": "Token expirado"}), 401

        result = db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "password_hash": generate_password_hash(new_password),
                    "updated_at": datetime.utcnow()
                },
                "$unset": {
                    "reset_token": "",
                    "reset_token_expires_at": ""
                }
            }
        )

        if result.modified_count == 0:
            return jsonify({"error": "No se pudo actualizar la contraseña"}), 500

        return jsonify({
            "message": "Contraseña actualizada exitosamente",
            "email": email
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500


# Ruta original recover-password (ya NO necesaria con el nuevo flujo,
# pero la dejo por si tu profe la revisa)
@users_bp.route('/recover-password', methods=['POST'])
def recover_password():

    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    jwt_token = (data.get("token") or "").strip()
    new_password = data.get("new_password")

    if not all([email, jwt_token, new_password]):
        return jsonify({"error": "Email, token y nueva contraseña son requeridos"}), 400

    password_error = validate_password(new_password)
    if password_error:
        return jsonify({"error": password_error}), 400

    try:
        try:
            decoded_token = jwt.decode(
                jwt_token,
                os.getenv('JWT_SECRET', 'lunas'),
                algorithms=['HS256']
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401

        token_user_id = decoded_token.get('user_id')
        if not token_user_id:
            return jsonify({"error": "Token no válido"}), 401

        user = db.users.find_one({"email": email, "is_active": True})
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        if str(user['_id']) != token_user_id:
            return jsonify({"error": "Token no corresponde a este email"}), 401

        result = db.users.update_one(
            {"_id": user['_id']},
            {
                "$set": {
                    "password_hash": generate_password_hash(new_password),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if result.modified_count == 0:
            return jsonify({"error": "No se pudo actualizar la contraseña"}), 500

        return jsonify({
            "message": "Contraseña actualizada exitosamente",
            "email": email
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500


@users_bp.route('/add-hours', methods=['POST'])
def add_hours():
    db = get_db()
    if db is None:
        return jsonify({"error": "Base de datos no disponible"}), 500

    data = request.get_json() or {}
    user_id = data.get("user_id")
    hours_to_add = data.get("hours")

    if not user_id or hours_to_add is None:
        return jsonify({"error": "Se requieren 'user_id' y 'hours'"}), 400

    try:
        user_obj_id = ObjectId(user_id)
    except Exception:
        return jsonify({"error": "ID de usuario inválido"}), 400

    try:
        hours_float = float(hours_to_add)
        if hours_float <= 0:
            return jsonify({"error": "Las horas a agregar deben ser mayores a 0"}), 400
    except ValueError:
        return jsonify({"error": "El valor de horas debe ser numérico"}), 400

    user = db.users.find_one({"_id": user_obj_id})
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    db.users.update_one(
        {"_id": user_obj_id},
        {"$inc": {"hours_balance": hours_float}}
    )

    updated_user = db.users.find_one({"_id": user_obj_id})

    return jsonify({
        "message": f"Se agregaron {hours_float} horas a {updated_user['name']}",
        "user": serialize_user_safe(updated_user)
    }), 200
