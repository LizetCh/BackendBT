from flask import Blueprint, jsonify
from config.db import get_db

test_bp = Blueprint("test", __name__)

@test_bp.route("/test-db", methods=["GET"])
def test_db_connection():
    db = get_db()
    if db is None:
        return jsonify({"status": "error", "message": "No se pudo conectar a la base de datos"}), 500

    try:
        # Listar colecciones existentes
        collections = db.list_collection_names()
        return jsonify({
            "status": "success",
            "message": "Conexión a MongoDB exitosa",
            "collections": collections
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500
