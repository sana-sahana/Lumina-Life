from flask import Blueprint, jsonify, request
from database.db import get_db
from datetime import datetime, timedelta
import uuid
import math

emergencies_bp = Blueprint('emergencies', __name__, url_prefix='/api/emergencies')

def calculate_distance(lat1, lng1, lat2, lng2):
    R = 6371
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

# ============ ROOT ENDPOINT FOR DONOR PAGE ============
@emergencies_bp.route('', methods=['GET'])
def get_emergencies_root():
    """Get active emergencies - used by donor page"""
    try:
        db = get_db()
        user_lat = float(request.args.get('lat', 12.9716))
        user_lng = float(request.args.get('lng', 77.5946))
        
        # Get active emergencies
        emergencies = list(db.emergency_requests.find({
            'status': 'active'
        }, {'_id': 0}).sort('priority', -1))
        
        # Calculate distance and ETA for each emergency
        for emergency in emergencies:
            # Get hospital location
            hospital = db.hospitals.find_one({'hospital_id': emergency['hospital_id']})
            if hospital:
                hospital_lat = hospital.get('latitude', 12.9716)
                hospital_lng = hospital.get('longitude', 77.5946)
            else:
                hospital_lat = 12.9716
                hospital_lng = 77.5946
            
            # Calculate distance
            distance = calculate_distance(user_lat, user_lng, hospital_lat, hospital_lng)
            emergency['distance_km'] = round(distance, 2)
            emergency['eta_minutes'] = int((distance / 40) * 60)
        
        return jsonify({'success': True, 'emergencies': emergencies}), 200
    except Exception as e:
        print(f"❌ Emergencies error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e), 'emergencies': []}), 500

@emergencies_bp.route('/active', methods=['GET'])
def get_active_emergencies():
    """Get all active emergencies with distances from user"""
    try:
        db = get_db()
        user_lat = float(request.args.get('lat', 12.9716))
        user_lng = float(request.args.get('lng', 77.5946))
        
        # Get active emergencies (not expired or fulfilled)
        emergencies = list(db.emergency_requests.find({
            'status': 'active',
            'expires_at': {'$gt': datetime.now()}
        }, {'_id': 0}).sort('priority', -1))
        
        # Calculate distance and ETA for each emergency
        for emergency in emergencies:
            hospital = db.hospitals.find_one({'hospital_id': emergency['hospital_id']})
            if hospital:
                emergency['hospital'] = hospital
                emergency['distance_km'] = round(calculate_distance(
                    user_lat, user_lng,
                    hospital.get('latitude', 12.9716),
                    hospital.get('longitude', 77.5946)
                ), 2)
                
                # Calculate ETA (assuming 40 km/h average speed)
                eta_minutes = int((emergency['distance_km'] / 40) * 60)
                emergency['eta_minutes'] = eta_minutes
                emergency['eta_text'] = f"{eta_minutes} min" if eta_minutes < 60 else f"{eta_minutes // 60}h {eta_minutes % 60}m"
        
        return jsonify({'success': True, 'emergencies': emergencies}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@emergencies_bp.route('/respond', methods=['POST'])
def respond_to_emergency():
    """Donor responds to an emergency"""
    try:
        data = request.json
        db = get_db()
        
        emergency_id = data.get('emergency_id')
        user_id = data.get('user_id')
        
        if not emergency_id or not user_id:
            return jsonify({'success': False, 'message': 'Emergency ID and User ID required'}), 400
        
        # Check if emergency exists and is active
        emergency = db.emergency_requests.find_one({
            'emergency_id': emergency_id,
            'status': 'active'
        })
        
        if not emergency:
            return jsonify({'success': False, 'message': 'Emergency not found or already fulfilled'}), 404
        
        # Check if donor already responded
        responding_donors = emergency.get('responding_donors', [])
        if any(d.get('user_id') == user_id for d in responding_donors):
            return jsonify({'success': False, 'message': 'You have already responded to this emergency'}), 400
        
        # Add donor response to emergency
        db.emergency_requests.update_one(
            {'emergency_id': emergency_id},
            {'$push': {
                'responding_donors': {
                    'user_id': user_id,
                    'responded_at': datetime.now(),
                    'status': 'en_route'
                }
            }}
        )
        
        # Create notification for donor
        notification = {
            'notification_id': str(uuid.uuid4()),
            'user_id': user_id,
            'title': 'Emergency Response Confirmed',
            'message': f'You have responded to {emergency.get("hospital_name", "the hospital")}. They will contact you shortly.',
            'type': 'emergency',
            'is_read': False,
            'created_at': datetime.now(),
            'priority': 'high'
        }
        db.notifications.insert_one(notification)
        
        return jsonify({'success': True, 'message': 'Emergency response recorded'}), 200
    except Exception as e:
        print(f"❌ Respond error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500