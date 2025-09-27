from flask import Blueprint,request,jsonify
from flask_jwt_extended import jwt_required,get_jwt_identity
from config.db import get_db_connection

# Crear el blueprint
services_bp = Blueprint('services',__name__)

#Crear servicio
@services_bp.route('/crear', methods = ['POST'])
@jwt_required()
def create_Service(): 
    #Datos del usuario 
    current_user = get_jwt_identity()
    #Datos del body
    data=request.get_json()

    id_owner = data.get('id_owner')
    if not id_owner:
        return jsonify({"error":"No id_owner."}),400
    
    title = data.get('title')
    if not title:
        return jsonify({"error":"No title"}),400
    
    description = data.get('description')
    if not description:
        return jsonify({"error":"No description"}),400
    
    category = data.get('category')
    if not category:
        return jsonify({"error":"No category"}),400
    
    hours = data.get('hours')
    if not hours:
        return jsonify({"error":"No hours"}),400

    contact_type = data.get('contact_type')
    if not contact_type:
        return jsonify({"error":"No contact_type"}),400
    
    date = data.get('date')
    if not date:
        return jsonify({"error":"No date"}),400
    
    location = data.get('location')
    if not location:
        return jsonify({"error":"No location"}),400
    
    reviews = data.get('review')
    if not reviews:
        return jsonify({"error":"No reviews"}),400

    cursor = get_db_connection()


