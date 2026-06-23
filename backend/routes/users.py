from flask import Blueprint, jsonify, request
from database.db import get_db
from datetime import datetime
import re

users_bp = Blueprint('users', __name__, url_prefix='/api')

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    phone_clean = phone.replace('+', '').replace('-', '').replace(' ', '')
    return len(phone_clean) >= 10 and phone_clean.isdigit()

@users_bp.route('/profile/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    """Get user profile from MongoDB Atlas"""
    try:
        db = get_db()
        profile = db.user_profiles.find_one({'user_id': user_id})
        
        if not profile:
            user = db.users.find_one({'user_id': user_id})
            if not user:
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            # Create default profile
            profile = {
                'user_id': user_id,
                'full_name': user.get('email', '').split('@')[0].capitalize(),
                'blood_group': 'O+',
                'phone': '',
                'email': user.get('email'),
                'age': 25,
                'weight_kg': 65.0,
                'avatar': 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png',
                'total_donations': 0,
                'lives_saved': 0,
                'last_donation_date': None,
                'is_recovered': True,
                'donor_status': 'available',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            db.user_profiles.insert_one(profile)
        
        return jsonify({
            'success': True,
            'profile': {
                'full_name': profile.get('full_name', ''),
                'blood_group': profile.get('blood_group', 'O+'),
                'avatar': profile.get('avatar', 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png'),
                'phone': profile.get('phone', ''),
                'email': profile.get('email', ''),
                'age': profile.get('age', 25),
                'weight_kg': profile.get('weight_kg', 65.0),
                'height_cm': profile.get('height_cm'),
                'hemoglobin': profile.get('hemoglobin'),
                'blood_pressure': profile.get('blood_pressure'),
                'notes': profile.get('notes'),
                'location': profile.get('location', ''),
                'total_donations': profile.get('total_donations', 0),
                'lives_saved': profile.get('lives_saved', 0),
                'last_donation_date': profile.get('last_donation_date').isoformat() if profile.get('last_donation_date') else None,
                'is_recovered': profile.get('is_recovered', True),
                'donor_status': profile.get('donor_status', 'available'),
                'user_id': profile.get('user_id', user_id)
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Get profile error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@users_bp.route('/profile/update', methods=['POST'])
def update_user_profile():
    """Update user profile in MongoDB Atlas"""
    try:
        data = request.json or {}
        db = get_db()
        
        # Accept both userId and user_id
        user_id = data.get('user_id') or data.get('userId')
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        print(f"📝 Updating profile for user: {user_id}")
        print(f"📦 Data received: {data}")
        
        # Build update document
        update_fields = {}
        
        # Map various field names to database field names
        field_mappings = {
            'full_name': ['full_name', 'fullName'],
            'blood_group': ['blood_group', 'bloodGroup'],
            'phone': ['phone'],
            'email': ['email'],
            'avatar': ['avatar'],
            'location': ['location'],
            'age': ['age'],
            'weight_kg': ['weight_kg', 'weight'],
            'height_cm': ['height_cm', 'height'],
            'hemoglobin': ['hemoglobin', 'hb'],
            'blood_pressure': ['blood_pressure', 'bloodPressure'],
            'notes': ['notes', 'medicalNotes'],
            'total_donations': ['total_donations', 'totalDonations'],
            'lives_saved': ['lives_saved', 'livesSaved'],
            'donor_status': ['donor_status', 'donorStatus'],
            'is_recovered': ['is_recovered', 'isRecovered']
        }
        
        for db_field, possible_keys in field_mappings.items():
            for key in possible_keys:
                if key in data and data[key] is not None:
                    value = data[key]
                    # Handle numeric fields
                    if db_field in ['age', 'total_donations'] and value:
                        update_fields[db_field] = int(value)
                    elif db_field in ['weight_kg', 'height_cm', 'hemoglobin'] and value:
                        update_fields[db_field] = float(value)
                    elif db_field in ['is_recovered'] and value is not None:
                        update_fields[db_field] = bool(value)
                    else:
                        update_fields[db_field] = value
                    break
        
        # Handle last donation date separately
        last_donation = data.get('last_donation_date') or data.get('lastDonationDate')
        if last_donation:
            try:
                if isinstance(last_donation, str):
                    date_str = last_donation.replace('Z', '+00:00') if 'Z' in last_donation else last_donation
                    update_fields['last_donation_date'] = datetime.fromisoformat(date_str)
                else:
                    update_fields['last_donation_date'] = last_donation
                print(f"📅 Last donation date set to: {update_fields['last_donation_date']}")
            except Exception as e:
                print(f"Date parsing error: {e}")
                update_fields['last_donation_date'] = datetime.now()
        
        if not update_fields:
            return jsonify({'success': False, 'message': 'No fields to update'}), 400
        
        update_fields['updated_at'] = datetime.now()
        
        print(f"📝 Updating fields: {list(update_fields.keys())}")
        
        # Update user_profiles
        result = db.user_profiles.update_one(
            {'user_id': user_id},
            {'$set': update_fields},
            upsert=True
        )
        
        # If this is a new user, also create health record
        if result.upserted_id:
            health_record = {
                'user_id': user_id,
                'hemoglobin': update_fields.get('hemoglobin', 14.5),
                'weight_kg': update_fields.get('weight_kg', 65.0),
                'height_cm': update_fields.get('height_cm', 170.0),
                'age': update_fields.get('age', 25),
                'blood_pressure': update_fields.get('blood_pressure', '120/80'),
                'hydration': 85,
                'energy': 88,
                'sleep_hours': 7.5,
                'illness': 'none',
                'last_updated': datetime.now(),
                'source': 'profile_update'
            }
            db.health_records.insert_one(health_record)
            print(f"✅ Created health record for new user: {user_id}")
        
        # Get updated profile
        updated_profile = db.user_profiles.find_one({'user_id': user_id})
        if updated_profile:
            updated_profile['_id'] = str(updated_profile['_id'])
            if updated_profile.get('last_donation_date'):
                if isinstance(updated_profile['last_donation_date'], datetime):
                    updated_profile['last_donation_date'] = updated_profile['last_donation_date'].isoformat()
        
        print(f"✅ Profile updated successfully for user: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully in MongoDB Atlas',
            'profile': updated_profile,
            'modified_count': result.modified_count,
            'upserted_id': str(result.upserted_id) if result.upserted_id else None
        }), 200
        
    except Exception as e:
        print(f"❌ Profile update error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500