from flask import Blueprint, jsonify, request
from database.db import get_db
from datetime import datetime
import uuid

health_bp = Blueprint('health', __name__, url_prefix='/api')

@health_bp.route('/health/<user_id>', methods=['GET'])
def get_health_data(user_id):
    """Get complete health data for user"""
    try:
        db = get_db()
        
        # Get from health_records collection
        health_record = db.health_records.find_one({'user_id': user_id}, {'_id': 0})
        profile = db.user_profiles.find_one({'user_id': user_id}, {'_id': 0})
        
        if not health_record:
            # Create default health record
            health_record = {
                'user_id': user_id,
                'hemoglobin': 14.5,
                'hydration': 85,
                'energy': 88,
                'blood_pressure': '120/80',
                'stress': 'Low',
                'eligibility': 'Eligible',
                'weight_kg': profile.get('weight_kg', 62) if profile else 62,
                'sleep_hours': 7.5,
                'illness': 'none',
                'last_updated': datetime.now()
            }
            db.health_records.insert_one(health_record)
            print(f"✅ Created default health record for {user_id}")
        
        return jsonify({
            'success': True,
            'hemoglobin': health_record.get('hemoglobin', 14.5),
            'hydration': health_record.get('hydration', 85),
            'energy': health_record.get('energy', 88),
            'blood_pressure': health_record.get('blood_pressure', '120/80'),
            'stress': health_record.get('stress', 'Low'),
            'eligibility': health_record.get('eligibility', 'Eligible'),
            'weight_kg': health_record.get('weight_kg', 62),
            'sleep_hours': health_record.get('sleep_hours', 7.5),
            'illness': health_record.get('illness', 'none'),
            'total_donations': profile.get('total_donations', 0) if profile else 0,
            'lives_saved': profile.get('lives_saved', 0) if profile else 0,
            'last_donation_date': profile.get('last_donation_date').isoformat() if profile and profile.get('last_donation_date') else None,
            'is_recovered': profile.get('is_recovered', True) if profile else True,
            'last_updated': health_record.get('last_updated').isoformat() if health_record.get('last_updated') else None
        }), 200
        
    except Exception as e:
        print(f"❌ Error in get_health_data: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@health_bp.route('/health/update', methods=['POST'])
def update_health_data():
    """Update user health data - SAVES TO MONGODB ATLAS"""
    try:
        data = request.json or {}
        print(f"📝 Received health update: {data}")
        
        db = get_db()
        
        user_id = data.get('userId') or data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        # Build update document
        health_update = {'last_updated': datetime.now()}
        profile_update = {}
        
        # Map all health metrics
        if 'hemoglobin' in data and data['hemoglobin']:
            health_update['hemoglobin'] = float(data['hemoglobin'])
        if 'hydration' in data and data['hydration']:
            health_update['hydration'] = int(data['hydration'])
        if 'energy' in data and data['energy']:
            health_update['energy'] = int(data['energy'])
        if 'blood_pressure' in data and data['blood_pressure']:
            health_update['blood_pressure'] = str(data['blood_pressure'])
        if 'stress' in data and data['stress']:
            health_update['stress'] = str(data['stress'])
        if 'weight_kg' in data and data['weight_kg']:
            health_update['weight_kg'] = float(data['weight_kg'])
            profile_update['weight_kg'] = float(data['weight_kg'])
        if 'sleep_hours' in data and data['sleep_hours']:
            health_update['sleep_hours'] = float(data['sleep_hours'])
        if 'illness' in data and data['illness']:
            health_update['illness'] = str(data['illness'])
        if 'heart_rate' in data and data['heart_rate']:
            health_update['heart_rate'] = int(data['heart_rate'])
        
        # Calculate eligibility
        hb = health_update.get('hemoglobin', 14.5)
        weight = health_update.get('weight_kg', 62)
        hydration = health_update.get('hydration', 85)
        illness = health_update.get('illness', 'none')
        
        if hb >= 12.5 and weight >= 50 and hydration >= 70 and illness == 'none':
            health_update['eligibility'] = 'Eligible'
        else:
            health_update['eligibility'] = 'Not Eligible'
        
        # Update health_records collection
        result = db.health_records.update_one(
            {'user_id': user_id},
            {'$set': health_update},
            upsert=True
        )
        print(f"✅ Health records updated: {result.modified_count} modified")
        
        # Update profile if weight changed
        if profile_update:
            db.user_profiles.update_one(
                {'user_id': user_id},
                {'$set': {**profile_update, 'updated_at': datetime.now()}}
            )
            print(f"✅ Profile updated with weight: {profile_update}")
        
        # Create notification for successful update
        notification = {
            'notification_id': str(uuid.uuid4()),
            'user_id': user_id,
            'title': 'Health Status Updated',
            'message': f'Your health metrics have been updated. You are now {health_update["eligibility"]} to donate.',
            'type': 'success',
            'is_read': False,
            'created_at': datetime.now(),
            'priority': 'medium'
        }
        db.notifications.insert_one(notification)
        
        return jsonify({
            'success': True,
            'message': 'Health data updated successfully in MongoDB Atlas',
            'eligibility': health_update.get('eligibility', 'Unknown'),
            'modified_count': result.modified_count
        }), 200
        
    except Exception as e:
        print(f"❌ Error in update_health_data: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500