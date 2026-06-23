from flask import Blueprint, jsonify, request
from database.db import get_db
from datetime import datetime, timedelta
import uuid

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api')

@dashboard_bp.route('/dashboard/<user_id>', methods=['GET'])
def get_dashboard(user_id):
    try:
        db = get_db()
        profile = db.user_profiles.find_one({"user_id": user_id})
        
        if not profile:
            user = db.users.find_one({"user_id": user_id})
            if not user:
                return jsonify({"error": "User not found"}), 404
            profile = {
                'user_id': user_id,
                'full_name': user.get('email', '').split('@')[0].capitalize(),
                'blood_group': 'O+',
                'total_donations': 0,
                'lives_saved': 0,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            db.user_profiles.insert_one(profile)
        
        health = db.health_records.find_one({"user_id": user_id})
        if not health:
            health = {
                "user_id": user_id,
                "hemoglobin": 14.5,
                "hydration": 85,
                "energy": 88,
                "blood_pressure": "120/80",
                "last_updated": datetime.now()
            }
            db.health_records.insert_one(health)
        
        return jsonify({
            "user_id": user_id,
            "name": profile.get("full_name"),
            "blood_group": profile.get("blood_group"),
            "total_donations": profile.get("total_donations", 0),
            "lives_saved": profile.get("lives_saved", 0),
            "donor_status": profile.get("donor_status", "available"),
            "health": {
                "hemoglobin": health.get("hemoglobin", 14.5),
                "hydration": health.get("hydration", 85),
                "energy": health.get("energy", 88),
                "bloodPressure": health.get("blood_pressure", "120/80")
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500