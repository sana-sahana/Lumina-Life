from flask import Blueprint, request, jsonify
from database.db import get_db
from datetime import datetime

navigation_bp = Blueprint('navigation', __name__, url_prefix='/api')

@navigation_bp.route('/navigation/start', methods=['POST'])
def record_navigation_start():
    """Record when donor starts navigation to hospital"""
    try:
        data = request.json
        db = get_db()
        print("🚗 NAVIGATION START CALLED")
        print("📦 Data:", data)
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id required'}), 400
        
        record = {
            'user_id': user_id,
            'donor_name': data.get('donor_name', 'Donor'),
            'hospital_id': data.get('hospital_id'),
            'hospital_name': data.get('hospital_name'),
            'hospital_lat': data.get('hospital_lat'),
            'hospital_lng': data.get('hospital_lng'),
            'donor_lat': data.get('donor_lat'),
            'donor_lng': data.get('donor_lng'),
            'mode': data.get('mode', 'drive'),
            'started_at': data.get('started_at', datetime.now().isoformat()),
            'status': 'in_progress',
            'created_at': datetime.now()
        }
        
        result = db.navigation_history.insert_one(record)
        
        return jsonify({
            'success': True, 
            'message': 'Navigation start recorded',
            'navigationId': str(result.inserted_id)
        })
    except Exception as e:
        print(f"❌ Navigation start error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@navigation_bp.route('/navigation/complete', methods=['POST'])
def record_navigation_complete():
    """Record when donor arrives at hospital"""
    try:
        data = request.json
        db = get_db()
        print("🏁 NAVIGATION COMPLETE CALLED")
        print("📦 Data:", data)
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        user_id = data.get('user_id')
        hospital_id = data.get('hospital_id')
        
        if not user_id or not hospital_id:
            return jsonify({'success': False, 'error': 'user_id and hospital_id required'}), 400
        
        # Update navigation log
        result = db.navigation_history.update_one(
            {
                'user_id': user_id, 
                'hospital_id': hospital_id, 
                'status': 'in_progress'
            },
            {'$set': {
                'completed_at': data.get('completedAt', datetime.now().isoformat()),
                'status': 'completed',
                'updated_at': datetime.now()
            }}
        )
        
        return jsonify({
            'success': True, 
            'message': 'Navigation completion recorded',
            'matched': result.matched_count,
            'modified': result.modified_count
        })
    except Exception as e:
        print(f"❌ Navigation complete error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# REMOVE THIS DUPLICATE - it's already in app.py
# @navigation_bp.route('/donations/complete', methods=['POST'])
# def complete_donation_record():
#     # ... remove this

@navigation_bp.route('/navigation/latest/<user_id>', methods=['GET'])
def get_latest_navigation(user_id):
    """Get the latest navigation for a donor"""
    try:
        db = get_db()
        print(f"📍 GET LATEST NAVIGATION for user: {user_id}")
        
        # Get most recent navigation for this user
        navigation = db.navigation_history.find_one(
            {'user_id': user_id},
            sort=[('created_at', -1)]
        )
        
        if not navigation:
            return jsonify({
                'success': False, 
                'message': 'No navigation found for this user'
            }), 404
        
        # Convert ObjectId to string
        navigation['_id'] = str(navigation['_id'])
        
        # Convert datetime objects to ISO strings
        if 'created_at' in navigation:
            navigation['created_at'] = navigation['created_at'].isoformat()
        if 'started_at' in navigation and isinstance(navigation['started_at'], datetime):
            navigation['started_at'] = navigation['started_at'].isoformat()
        if 'completed_at' in navigation and isinstance(navigation['completed_at'], datetime):
            navigation['completed_at'] = navigation['completed_at'].isoformat()
        if 'arrived_at' in navigation and isinstance(navigation['arrived_at'], datetime):
            navigation['arrived_at'] = navigation['arrived_at'].isoformat()
        if 'updated_at' in navigation and isinstance(navigation['updated_at'], datetime):
            navigation['updated_at'] = navigation['updated_at'].isoformat()
        
        return jsonify({
            'success': True,
            'navigation': navigation
        }), 200
        
    except Exception as e:
        print(f"❌ Get latest navigation error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@navigation_bp.route('/navigation/arrive', methods=['POST'])
def mark_arrival():
    """Mark donor arrival at hospital"""
    try:
        data = request.json
        db = get_db()
        print("📍 ARRIVAL MARKED CALLED")
        print("📦 Data:", data)
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        navigation_id = data.get('navigation_id')
        user_id = data.get('user_id')
        hospital_id = data.get('hospital_id')
        arrived_at = data.get('arrived_at', datetime.now().isoformat())
        
        if not navigation_id or not user_id:
            return jsonify({'success': False, 'message': 'Navigation ID and User ID required'}), 400
        
        # Parse arrived_at if it's a string
        if isinstance(arrived_at, str):
            try:
                arrived_at_dt = datetime.fromisoformat(arrived_at.replace('Z', '+00:00'))
            except:
                arrived_at_dt = datetime.now()
        else:
            arrived_at_dt = arrived_at
        
        # Update navigation status
        from bson import ObjectId
        
        # Try to find by ObjectId or by navigation_id string
        try:
            result = db.navigation_history.update_one(
                {'_id': ObjectId(navigation_id)},
                {'$set': {
                    'status': 'arrived',
                    'arrived_at': arrived_at_dt,
                    'updated_at': datetime.now()
                }}
            )
        except:
            # If not ObjectId, try as string
            result = db.navigation_history.update_one(
                {'navigation_id': navigation_id},
                {'$set': {
                    'status': 'arrived',
                    'arrived_at': arrived_at_dt,
                    'updated_at': datetime.now()
                }}
            )
        
        if result.matched_count == 0:
            # Also update any in-progress navigation for this user/hospital
            result = db.navigation_history.update_one(
                {
                    'user_id': user_id, 
                    'hospital_id': hospital_id, 
                    'status': 'in_progress'
                },
                {'$set': {
                    'status': 'arrived',
                    'arrived_at': arrived_at_dt,
                    'updated_at': datetime.now()
                }}
            )
        
        if result.matched_count == 0:
            return jsonify({'success': False, 'message': 'Navigation record not found'}), 404
        
        return jsonify({
            'success': True, 
            'message': 'Arrival marked successfully',
            'navigation_id': navigation_id
        }), 200
        
    except Exception as e:
        print(f"❌ Arrival error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500