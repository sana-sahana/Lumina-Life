from flask import Blueprint, jsonify, request
from database.db import get_db
import math

hospitals_bp = Blueprint('hospitals', __name__, url_prefix='/api')

@hospitals_bp.route('/hospitals', methods=['GET'])
def get_hospitals():
    try:
        db = get_db()
        hospitals = list(db.hospitals.find({}, {'_id': 0}))
        return jsonify({'success': True, 'hospitals': hospitals}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500