import sys
import os
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from datetime import datetime, timedelta
import hashlib
import uuid
import random
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, messaging
from groq import Groq
from bson import ObjectId


# Load environment variables
load_dotenv()
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# Add root directory to python path to resolve sibling imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from routes.hospital_portal import hospital_portal_bp
from database.db import init_app, get_db
from routes.auth import auth_bp
from routes.users import users_bp
from routes.dashboard import dashboard_bp
from routes.health import health_bp
from routes.notifications import notifications_bp
from routes.appointments import appointments_bp
from routes.tracker import tracker_bp
from routes.hospitals import hospitals_bp
from routes.donations import donations_bp
from routes.emergencies import emergencies_bp
from routes.navigation import navigation_bp

app = Flask(__name__, static_folder='../static', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'lumina_life_secret_key_2025')

# Enable CORS for all routes with proper configuration
CORS(app, 
     supports_credentials=True, 
     resources={
         r"/*": {
             "origins": ["http://localhost:5000", "http://127.0.0.1:5000", "http://127.0.0.1:5000/notifications.html"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "X-User-Id"]
         }
     })
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    cred = credentials.Certificate(
        os.path.join(
            BASE_DIR,
            "luminalife-7f217-firebase-adminsdk-fbsvc-921f0445a7.json"
        )
    )

    print("✅ Firebase initialized")

except Exception as e:
    print(f"⚠️ Firebase not initialized: {e}")
# Load configuration
try:
    from backend.config import Config
    app.config.from_object(Config)
except ImportError:
    # Fallback config if config.py doesn't exist
    app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    app.config['MONGO_DB_NAME'] = os.getenv('MONGO_DB_NAME', 'lumina_life')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'lumina_life_secret_key_2025')
    app.config['DEBUG'] = os.getenv('DEBUG', 'True') == 'True'

# Initialize database connection
init_app(app)

# Register Blueprints (all routes are now in blueprint files)
app.register_blueprint(navigation_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(health_bp)
app.register_blueprint(appointments_bp)
app.register_blueprint(tracker_bp)
app.register_blueprint(hospitals_bp)
app.register_blueprint(donations_bp)
app.register_blueprint(emergencies_bp)
app.register_blueprint(hospital_portal_bp)

# ========== REMOVED DUPLICATE ROUTES ==========
# The following routes are now handled by blueprint files:
# - /api/health/<user_id>     (in routes/health.py)
# - /api/health/update        (in routes/health.py)
# - /api/health/history/<user_id> (in routes/health.py)
# - /api/profile/<user_id>    (in routes/users.py)
# - /api/profile/update       (in routes/users.py)

# ========== ORGAN DONOR REGISTRATION ==========
@app.route('/api/donor/organ-register', methods=['POST'])
def register_organ_donor():
    """Register donor for organ donation in MongoDB Atlas"""
    try:
        data = request.json
        db = get_db()
        
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        organ_record = {
            'user_id': user_id,
            'donor_name': data.get('donor_name', ''),
            'organ_types': data.get('organ_types', []),
            'registered_at': datetime.now(),
            'status': 'active',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Check if already registered
        existing = db.organ_donors.find_one({'user_id': user_id})
        if existing:
            db.organ_donors.update_one(
                {'user_id': user_id},
                {'$set': {
                    'organ_types': data.get('organ_types', []),
                    'updated_at': datetime.now()
                }}
            )
            message = 'Organ donor registry updated'
        else:
            db.organ_donors.insert_one(organ_record)
            message = 'Organ donor registered successfully'
        
        # Update user profile
        db.user_profiles.update_one(
            {'user_id': user_id},
            {'$set': {
                'is_organ_donor': True,
                'organ_types': data.get('organ_types', []),
                'organ_registered_at': datetime.now(),
                'updated_at': datetime.now()
            }},
            upsert=True
        )
        
        return jsonify({
            'success': True,
            'message': message,
            'organ_types': data.get('organ_types', [])
        })
    except Exception as e:
        print(f"❌ Organ donor registration error: {e}")
        return jsonify({'error': str(e)}), 500





# ========== DONOR STATS UPDATE ==========
@app.route('/api/donor/update-stats', methods=['POST'])
def update_donor_stats():
    """Update donor statistics in MongoDB Atlas"""
    try:
        data = request.json
        db = get_db()
        
        user_id = data.get('userId') or data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        update_fields = {}
        
        if 'totalDonations' in data:
            update_fields['total_donations'] = int(data['totalDonations'])
        if 'livesSaved' in data:
            update_fields['lives_saved'] = int(data['livesSaved'])
        if 'lastDonationDate' in data:
            update_fields['last_donation_date'] = datetime.fromisoformat(
                data['lastDonationDate'].replace('Z', '+00:00')
            )
        if 'isRecovered' in data:
            update_fields['is_recovered'] = bool(data['isRecovered'])
        
        update_fields['updated_at'] = datetime.now()
        
        result = db.user_profiles.update_one(
            {'user_id': user_id},
            {'$set': update_fields}
        )
        
        return jsonify({
            'success': True, 
            'message': 'Stats updated in MongoDB Atlas',
            'matched_count': result.matched_count,
            'modified_count': result.modified_count
        })
    except Exception as e:
        print(f"❌ Stats update error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ========== EMERGENCY ROUTES ==========
@app.route('/api/notifications/delete/<notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    """Delete a notification from MongoDB Atlas"""
    try:
        db = get_db()
        
        result = db.notifications.delete_one({'notification_id': notification_id})
        
        if result.deleted_count == 0:
            return jsonify({'success': False, 'message': 'Notification not found'}), 404
        
        return jsonify({
            'success': True, 
            'message': 'Notification deleted successfully'
        }), 200
    except Exception as e:
        print(f"❌ Delete notification error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
# ========== DONATION ROUTES ==========
@app.route('/api/donations/complete', methods=['POST'])
def complete_donation_record():
    """Mark donation as completed - PREVENTS DUPLICATES"""
    try:
        data = request.json
        db = get_db()
        print("DONATION REQUEST:", data)
        
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        hospital_name = data.get('hospital_name')
        navigation_id = data.get('navigationId')
        
        # ===== DUPLICATE CHECK =====
        # Check 1: By navigation_id
        if navigation_id:
            existing = db.donations.find_one({
                'user_id': user_id,
                'navigation_id': navigation_id
            })
            if existing:
                print(f"⚠️ DUPLICATE: Donation exists for navigation_id: {navigation_id}")
                return jsonify({
                    'success': True,
                    'message': 'Donation already recorded',
                    'already_exists': True
                }), 200
        
        # Check 2: By hospital_name within last 1 hour
        if hospital_name:
            one_hour_ago = datetime.now() - timedelta(hours=1)
            existing_recent = db.donations.find_one({
                'user_id': user_id,
                'hospital_name': hospital_name,
                'created_at': {'$gt': one_hour_ago}
            })
            if existing_recent:
                print(f"⚠️ DUPLICATE: Recent donation for {hospital_name}")
                return jsonify({
                    'success': True,
                    'message': 'Donation already recorded recently',
                    'already_exists': True
                }), 200
        
        # Check if user exists
        user = db.users.find_one({'user_id': user_id})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Create donation record
        donation_record = {
            'donation_id': str(uuid.uuid4()),
            'user_id': user_id,
            'hospital_id': data.get('hospital_id'),
            'hospital_name': hospital_name or 'Unknown Hospital',
            'blood_type': data.get('blood_type', 'Unknown'),
            'status': 'completed',
            'completed_at': datetime.now(),
            'created_at': datetime.now(),
            'navigation_id': navigation_id
        }
        
        result = db.donations.insert_one(donation_record)
        print(f"✅ New donation created: {result.inserted_id}")
        
        # Update user profile stats
        db.user_profiles.update_one(
            {'user_id': user_id},
            {
                '$inc': {
                    'total_donations': 1,
                    'lives_saved': 3
                },
                '$set': {
                    'last_donation_date': datetime.now(),
                    'updated_at': datetime.now()
                }
            },
            upsert=True
        )
        
        return jsonify({
            'success': True, 
            'message': 'Donation completed successfully',
            'donation_id': str(result.inserted_id)
        })
    except Exception as e:
        print(f"❌ Donation complete error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
# ========== DONATION HISTORY ROUTE ==========

# Add this after your other donation routes
@app.route('/api/donations/check', methods=['GET'])
def check_donation_exists():
    """Check if a donation already exists for a user and hospital (within 1 hour)"""
    try:
        user_id = request.args.get('user_id')
        hospital_name = request.args.get('hospital_name')
        
        if not user_id or not hospital_name:
            return jsonify({'exists': False, 'error': 'Missing parameters'}), 400
        
        db = get_db()
        
        # Check for recent donation (within last 1 hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        existing = db.donations.find_one({
            'user_id': user_id,
            'hospital_name': hospital_name,
            'created_at': {'$gt': one_hour_ago}
        })
        
        return jsonify({
            'exists': existing is not None,
            'donation': {
                'id': str(existing.get('_id')) if existing else None,
                'hospital_name': existing.get('hospital_name') if existing else None,
                'created_at': existing.get('created_at').isoformat() if existing else None
            } if existing else None
        }), 200
        
    except Exception as e:
        print(f"❌ Check donation error: {e}")
        return jsonify({'exists': False, 'error': str(e)}), 500





# ========== HOSPITAL REQUESTS ROUTE ==========
@app.route('/api/hospital/requests', methods=['GET'])
def get_hospital_emergency_requests():
    """Get all emergency requests for a specific hospital from MongoDB"""
    try:
        hospital_id = request.args.get('hospital_id')
        if not hospital_id:
            return jsonify({'success': False, 'message': 'hospital_id parameter required'}), 400
        
        db = get_db()
        
        # Query emergency_requests collection for this hospital
        requests = list(db.emergency_requests.find(
            {'hospital_id': hospital_id}
        ).sort('created_at', -1))
        
        # Convert ObjectId to string for JSON serialization
        for req in requests:
            req['_id'] = str(req['_id'])
            # Convert datetime objects to ISO format
            if req.get('created_at'):
                req['created_at'] = req['created_at'].isoformat()
            if req.get('updated_at'):
                req['updated_at'] = req['updated_at'].isoformat()
            if req.get('expires_at'):
                req['expires_at'] = req['expires_at'].isoformat()
            if req.get('completed_at'):
                req['completed_at'] = req['completed_at'].isoformat()
        
        # Also fetch navigation history for these emergencies to show arrivals
        emergency_ids = [req.get('emergency_id') for req in requests if req.get('emergency_id')]
        navigation_data = {}
        
        if emergency_ids:
            nav_history = list(db.navigation_history.find(
                {'emergency_id': {'$in': emergency_ids}}
            ).sort('timestamp', -1))
            
            # Group by emergency_id
            for nav in nav_history:
                nav['_id'] = str(nav['_id'])
                if nav.get('timestamp'):
                    nav['timestamp'] = nav['timestamp'].isoformat()
                emergency_id = nav.get('emergency_id')
                if emergency_id:
                    if emergency_id not in navigation_data:
                        navigation_data[emergency_id] = []
                    navigation_data[emergency_id].append(nav)
        
        # Attach navigation history to each request
        for req in requests:
            req['navigation_history'] = navigation_data.get(req.get('emergency_id'), [])
            
            # Determine if any donor has arrived
            has_arrived = any(
                nav.get('status') == 'arrived' or nav.get('action') == 'arrived' 
                for nav in req.get('navigation_history', [])
            )
            req['has_donor_arrived'] = has_arrived
        
        return jsonify({
            'success': True,
            'requests': requests,
            'count': len(requests)
        }), 200
        
    except Exception as e:
        print(f"❌ Get hospital requests error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': str(e),
            'requests': []
        }), 500


# ========== HOSPITAL REQUEST CANCEL ROUTE ==========
@app.route('/api/hospital/request/cancel', methods=['POST'])
def cancel_hospital_request():
    """Cancel an emergency request"""
    try:
        data = request.json
        db = get_db()
        
        emergency_id = data.get('emergency_id')
        hospital_id = data.get('hospital_id')
        
        if not emergency_id or not hospital_id:
            return jsonify({'success': False, 'message': 'emergency_id and hospital_id required'}), 400
        
        # Verify this hospital owns this request
        existing = db.emergency_requests.find_one({
            'emergency_id': emergency_id,
            'hospital_id': hospital_id
        })
        
        if not existing:
            return jsonify({'success': False, 'message': 'Request not found or not owned by this hospital'}), 404
        
        # Update status to cancelled
        result = db.emergency_requests.update_one(
            {'emergency_id': emergency_id},
            {'$set': {
                'status': 'cancelled',
                'cancelled_at': datetime.now(),
                'cancelled_reason': data.get('reason', 'Cancelled by hospital'),
                'updated_at': datetime.now()
            }}
        )
        
        # Notify all responding donors that request was cancelled
        responding_donors = existing.get('responding_donors', [])
        for donor in responding_donors:
            donor_id = donor.get('user_id')
            if donor_id:
                notification = {
                    'notification_id': str(uuid.uuid4()),
                    'user_id': donor_id,
                    'title': '❌ Emergency Request Cancelled',
                    'message': f'The emergency request at {existing.get("hospital_name")} has been cancelled by the hospital.',
                    'type': 'emergency_cancelled',
                    'is_read': False,
                    'created_at': datetime.now(),
                    'priority': 'medium',
                    'metadata': {
                        'emergency_id': emergency_id,
                        'hospital_name': existing.get('hospital_name')
                    }
                }
                db.notifications.insert_one(notification)
        
        return jsonify({
            'success': True,
            'message': 'Request cancelled successfully'
        }), 200
        
    except Exception as e:
        print(f"❌ Cancel request error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========== NAVIGATION HISTORY ROUTE ==========
@app.route('/api/navigation/history', methods=['GET'])
def get_navigation_history():
    """Get navigation history for multiple emergency IDs"""
    try:
        emergency_ids_str = request.args.get('emergency_ids', '')
        if not emergency_ids_str:
            return jsonify({'success': True, 'history': []}), 200
        
        # Parse comma-separated emergency IDs
        emergency_ids = [id.strip() for id in emergency_ids_str.split(',') if id.strip()]
        
        db = get_db()
        
        # Get all navigation history for these emergencies
        history = list(db.navigation_history.find(
            {'emergency_id': {'$in': emergency_ids}}
        ).sort('timestamp', -1))
        
        # Convert for JSON
        for item in history:
            item['_id'] = str(item['_id'])
            if item.get('timestamp'):
                item['timestamp'] = item['timestamp'].isoformat()
            if item.get('started_at'):
                item['started_at'] = item['started_at'].isoformat()
            if item.get('arrived_at'):
                item['arrived_at'] = item['arrived_at'].isoformat()
            if item.get('completed_at'):
                item['completed_at'] = item['completed_at'].isoformat()
        
        return jsonify({
            'success': True,
            'history': history
        }), 200
        
    except Exception as e:
        print(f"❌ Navigation history error: {e}")
        return jsonify({'success': False, 'message': str(e), 'history': []}), 500


# ========== EMERGENCIES ACTIVE ROUTE ==========
@app.route('/api/emergencies/active', methods=['GET'])
def get_active_emergencies_for_donors():
    """Get active emergency requests for donor dashboard"""
    try:
        db = get_db()
        
        # Get all active emergencies
        emergencies = list(db.emergency_requests.find(
            {'status': 'active'}
        ).sort('created_at', -1))
        
        # Convert for JSON
        for em in emergencies:
            em['_id'] = str(em['_id'])
            if em.get('created_at'):
                em['created_at'] = em['created_at'].isoformat()
            if em.get('expires_at'):
                em['expires_at'] = em['expires_at'].isoformat()
            if em.get('updated_at'):
                em['updated_at'] = em['updated_at'].isoformat()
        
        return jsonify({
            'success': True,
            'emergencies': emergencies,
            'count': len(emergencies)
        }), 200
        
    except Exception as e:
        print(f"❌ Get active emergencies error: {e}")
        return jsonify({'success': False, 'message': str(e), 'emergencies': []}), 500



# ========== DONATION HISTORY ROUTE ==========
@app.route('/api/donations/<user_id>', methods=['GET'])
def get_donations(user_id):
    """Get donation history for a user from MongoDB Atlas"""
    try:
        db = get_db()
        
        # Get user profile
        profile = db.user_profiles.find_one({'user_id': user_id})
        
        # Get donation records
        donations = list(db.donations.find(
            {'user_id': user_id},
            {'_id': 0}
        ).sort('completed_at', -1).limit(20))
        
        # Format donations for frontend
        formatted_donations = []
        for d in donations:
            formatted_donations.append({
                'hospital_name': d.get('hospital_name', 'Unknown Hospital'),
                'completed_at': d.get('completed_at', d.get('created_at')),
                'blood_type': d.get('blood_type', 'Unknown'),
                'status': d.get('status', 'completed'),
                'lives_saved': 3
            })
        
        # If no donation records found but profile has total_donations
        if not formatted_donations and profile and profile.get('total_donations', 0) > 0:
            total = profile.get('total_donations', 0)
            for i in range(min(total, 5)):
                date = datetime.now() - timedelta(days=(i * 90 + 30))
                formatted_donations.append({
                    'hospital_name': f'Donation #{i+1}',
                    'completed_at': date,
                    'blood_type': profile.get('blood_group', 'Unknown'),
                    'status': 'completed',
                    'lives_saved': 3
                })
        
        return jsonify({
            'success': True,
            'donations': formatted_donations,
            'total': len(formatted_donations)
        })
        
    except Exception as e:
        print(f"❌ Get donations error: {e}")
        return jsonify({'success': False, 'error': str(e), 'donations': []}), 500

# ========== NOTIFICATION ROUTES ==========
@app.route('/api/notifications/create', methods=['POST'])
def create_notification():
    """Create a new notification in MongoDB Atlas"""
    try:
        data = request.json
        db = get_db()
        
        notification = {
            'notification_id': str(uuid.uuid4()),
            'user_id': data.get('user_id'),
            'title': data.get('title'),
            'message': data.get('message'),
            'type': data.get('type', 'info'),
            'is_read': False,
            'created_at': datetime.now(),
            'priority': data.get('priority', 'medium'),
            'metadata': data.get('metadata', {})
        }
        
        db.notifications.insert_one(notification)
        
        return jsonify({
            'success': True,
            'message': 'Notification created in MongoDB Atlas',
            'notification_id': notification['notification_id']
        }), 201
    except Exception as e:
        print(f"❌ Notification create error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/save-fcm-token', methods=['POST'])
def save_fcm_token():
    try:
        data = request.json

        print("FCM RECEIVED:", data)  # ADD THIS

        token = data.get('token')
        user_id = data.get('user_id')

        db = get_db()

        db.fcm_tokens.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "token": token,
                    "updated_at": datetime.now()
                }
            },
            upsert=True
        )

        print("TOKEN SAVED")

        return jsonify({"success": True})

    except Exception as e:
        print("FCM SAVE ERROR:", e)
        return jsonify({"success": False}), 500


@app.route('/test-notification')
def test_notification():

    try:
        db = get_db()

        token_doc = db.fcm_tokens.find_one()

        print("TOKEN DOC:", token_doc)

        if not token_doc:
            return jsonify({"error": "No token found"})

        message = messaging.Message(
            notification=messaging.Notification(
                title="LuminaLife Test",
                body="Firebase notification working!"
            ),
            token=token_doc["token"]
        )

        response = messaging.send(message)

        print("FCM RESPONSE:", response)

        return jsonify({
            "success": True,
            "response": response
        })

    except Exception as e:
        print("FCM ERROR:", e)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/notifications/<user_id>', methods=['GET'])
def get_user_notifications(user_id):
    """Get notifications for a user from MongoDB Atlas"""
    try:
        db = get_db()
        
        notifications = list(db.notifications.find(
            {'user_id': user_id}
        ).sort('created_at', -1).limit(20))
        
        for notif in notifications:
            notif['_id'] = str(notif['_id'])
            if 'created_at' in notif:
                notif['timestamp'] = notif['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'unread_count': sum(1 for n in notifications if not n.get('is_read', False))
        })
    except Exception as e:
        print(f"❌ Get notifications error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/read/<notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    """Mark a notification as read in MongoDB Atlas"""
    try:
        db = get_db()
        
        result = db.notifications.update_one(
            {'notification_id': notification_id},
            {'$set': {'is_read': True, 'read_at': datetime.now()}}
        )
        
        return jsonify({
            'success': True, 
            'message': 'Notification marked as read',
            'matched_count': result.matched_count
        })
    except Exception as e:
        print(f"❌ Mark notification read error: {e}")
        return jsonify({'error': str(e)}), 500

# ========== HOSPITAL ROUTES ==========
@app.route('/api/hospitals', methods=['GET'])
def get_hospitals():
    """Get all hospitals with location filtering from MongoDB Atlas"""
    try:
        db = get_db()
        
        user_lat = float(request.args.get('lat', 12.9716))
        user_lng = float(request.args.get('lng', 77.5946))
        
        hospitals = list(db.hospitals.find({}, {'_id': 0}))
        
        import math
        for hospital in hospitals:
            hospital_lat = hospital.get('latitude', 12.9716)
            hospital_lng = hospital.get('longitude', 77.5946)
            
            R = 6371
            lat1, lon1, lat2, lon2 = map(math.radians, [user_lat, user_lng, hospital_lat, hospital_lng])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            distance = R * 2 * math.asin(math.sqrt(a))
            
            hospital['distance_km'] = round(distance, 2)
        
        return jsonify({'success': True, 'hospitals': hospitals})
    except Exception as e:
        print(f"❌ Get hospitals error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ========== DONOR LOCATION UPDATE ==========
@app.route('/api/donor/location', methods=['POST'])
def update_donor_location():
    """Update donor's current location in MongoDB Atlas"""
    try:
        data = request.json
        db = get_db()
        
        user_id = data.get('user_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not user_id or not latitude or not longitude:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        db.user_profiles.update_one(
            {'user_id': user_id},
            {'$set': {
                'current_location': {
                    'type': 'Point',
                    'coordinates': [longitude, latitude]
                },
                'last_location_update': datetime.now(),
                'latitude': latitude,
                'longitude': longitude
            }}
        )
        
        return jsonify({'success': True, 'message': 'Location updated in MongoDB Atlas'}), 200
    except Exception as e:
        print(f"❌ Location update error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
# ========== EMERGENCIES GET ROUTE ==========
@app.route('/api/emergencies', methods=['GET'])
def get_emergencies():
    """Get active emergencies from MongoDB Atlas"""
    try:
        db = get_db()
        
        # Check if collection exists, if not create it
        if 'emergency_requests' not in db.list_collection_names():
            db.create_collection('emergency_requests')
            print("✅ Created emergency_requests collection")
        
        user_lat = float(request.args.get('lat', 12.9716))
        user_lng = float(request.args.get('lng', 77.5946))
        
        # Get emergencies from MongoDB
        emergencies = list(db.emergency_requests.find({'status': 'active'}, {'_id': 0}))
        
        # If no emergencies in DB, create some sample ones
        if not emergencies:
            print("⚠️ No emergencies found in DB, creating sample...")
            
            sample_emergencies = [
                {
                    "emergency_id": "EMG001",
                    "hospital_id": "H001",
                    "hospital_name": "Memorial Health",
                    "blood_type_needed": "A-",
                    "units_needed": 3,
                    "priority": "critical",
                    "status": "active",
                    "created_at": datetime.now(),
                    "expires_at": datetime.now() + timedelta(hours=4),
                    "responders": 0,
                    "latitude": 12.9750,
                    "longitude": 77.6035
                },
                {
                    "emergency_id": "EMG002",
                    "hospital_id": "H004",
                    "hospital_name": "Holy Cross Hospital",
                    "blood_type_needed": "O+",
                    "units_needed": 5,
                    "priority": "high",
                    "status": "active",
                    "created_at": datetime.now(),
                    "expires_at": datetime.now() + timedelta(hours=3),
                    "responders": 0,
                    "latitude": 12.9650,
                    "longitude": 77.5850
                },
                {
                    "emergency_id": "EMG003",
                    "hospital_id": "H002",
                    "hospital_name": "St. Luke's Medical",
                    "blood_type_needed": "AB+",
                    "units_needed": 2,
                    "priority": "medium",
                    "status": "active",
                    "created_at": datetime.now(),
                    "expires_at": datetime.now() + timedelta(hours=5),
                    "responders": 0,
                    "latitude": 12.9820,
                    "longitude": 77.6220
                }
            ]
            
            try:
                db.emergency_requests.insert_many(sample_emergencies)
                emergencies = list(db.emergency_requests.find({'status': 'active'}, {'_id': 0}))
                print(f"✅ Created {len(emergencies)} sample emergencies in DB")
            except Exception as insert_error:
                print(f"⚠️ Error inserting sample data: {insert_error}")
                # Return empty array if can't insert
                return jsonify({
                    'success': True, 
                    'emergencies': [],
                    'message': 'No emergencies found'
                }), 200
        
        # Calculate distance and ETA for each emergency
        import math
        for emergency in emergencies:
            hospital_lat = emergency.get('latitude', 12.9716)
            hospital_lng = emergency.get('longitude', 77.5946)
            
            R = 6371  # Earth's radius in km
            lat1, lon1, lat2, lon2 = map(math.radians, [user_lat, user_lng, hospital_lat, hospital_lng])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            distance = R * 2 * math.asin(math.sqrt(a))
            
            emergency['distance_km'] = round(distance, 2)
            emergency['eta_minutes'] = int((distance / 40) * 60)  # Assuming 40 km/h average speed
        
        return jsonify({'success': True, 'emergencies': emergencies})
        
    except Exception as e:
        print(f"❌ Emergencies error: {e}")
        import traceback
        traceback.print_exc()
        # Return empty array instead of 500 error
        return jsonify({
            'success': False, 
            'message': str(e),
            'emergencies': []
        }), 500
# ========== EMERGENCIES GET ROUTE ==========
@app.route('/api/emergencies/respond', methods=['POST'])
def respond_to_emergency():
    """Donor responds to an emergency request - saves response in emergency_requests"""
    try:
        data = request.json
        db = get_db()
        
        print("=" * 60)
        print("🚨 EMERGENCY RESPONSE RECEIVED")
        print("📤 Data:", data)
        
        user_id = data.get('user_id')
        emergency_id = data.get('emergency_id')
        donor_name = data.get('donor_name', 'Anonymous Donor')
        blood_type = data.get('blood_type', 'Unknown')
        donor_phone = data.get('donor_phone', '')
        
        if not user_id or not emergency_id:
            return jsonify({'error': 'user_id and emergency_id required'}), 400
        
        # Find the emergency
        emergency = db.emergency_requests.find_one({
            'emergency_id': emergency_id,
            'status': 'active'
        })
        
        if not emergency:
            return jsonify({'error': 'Emergency not found or already fulfilled'}), 404
        
        # Check if donor already responded
        responding_donors = emergency.get('responding_donors', [])
        if any(d.get('user_id') == user_id for d in responding_donors):
            return jsonify({'error': 'You have already responded to this emergency'}), 400
        
        # ============ UPDATE THE SAME emergency_requests DOCUMENT ============
        db.emergency_requests.update_one(
            {'emergency_id': emergency_id},
            {
                '$push': {
                    'responding_donors': {
                        'user_id': user_id,
                        'donor_name': donor_name,
                        'blood_type': blood_type,
                        'donor_phone': donor_phone,
                        'responded_at': datetime.now(),
                        'status': 'en_route'
                    }
                },
                '$inc': {'responders': 1},
                '$set': {
                    'last_responded_at': datetime.now(),
                    'updated_at': datetime.now()
                }
            }
        )
        print(f"✅ Donor {user_id} added to emergency {emergency_id}")
        
        # ============ CREATE DONATION RECORD (Optional - for history) ============
        donation_record = {
            'donation_id': str(uuid.uuid4()),
            'user_id': user_id,
            'hospital_id': emergency.get('hospital_id'),
            'hospital_name': emergency.get('hospital_name'),
            'blood_type': blood_type,
            'emergency_id': emergency_id,
            'status': 'in_progress',
            'responded_at': datetime.now(),
            'created_at': datetime.now()
        }
        db.donations.insert_one(donation_record)
        print(f"✅ Donation record created: {donation_record['donation_id']}")
        
        # ============ UPDATE USER PROFILE STATS ============
        db.user_profiles.update_one(
            {'user_id': user_id},
            {
                '$inc': {'total_donations': 1, 'lives_saved': 3},
                '$set': {
                    'last_donation_date': datetime.now(),
                    'updated_at': datetime.now()
                }
            },
            upsert=True
        )
        print("✅ User profile stats updated")
        
        # ============ CREATE NOTIFICATION ============
        notification = {
            'notification_id': str(uuid.uuid4()),
            'user_id': user_id,
            'title': '🩸 Emergency Response Confirmed',
            'message': f"You have responded to {emergency.get('hospital_name')} for {emergency.get('blood_type_needed')} blood donation.",
            'type': 'emergency_response',
            'is_read': False,
            'created_at': datetime.now(),
            'priority': 'high'
        }
        db.notifications.insert_one(notification)
        print("✅ Notification created")
        
        print("=" * 60)
        print("✅ EMERGENCY RESPONSE COMPLETE")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'message': 'Emergency response recorded successfully',
            'donation_id': donation_record['donation_id']
        }), 200
        
    except Exception as e:
        print(f"❌ Emergency response error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500




#==========arrival=================

# ========== PROFILE UPDATE ROUTE ==========
@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    """Update user profile in MongoDB Atlas"""
    try:
        data = request.json
        db = get_db()
        
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        # ✅ Ensure user exists in users collection
        if not db.users.find_one({'user_id': user_id}):
            db.users.insert_one({
                'user_id': user_id,
                'full_name': data.get('full_name', 'User'),
                'created_at': datetime.now()
            })
            print(f"✅ Created user {user_id} in users collection")
        
        # Prepare update fields
        update_fields = {}
        field_mapping = {
            'full_name': 'full_name',
            'blood_group': 'blood_group',
            'phone': 'phone',
            'age': 'age',
            'weight_kg': 'weight_kg',
            'last_donation_date': 'last_donation_date',
            'hemoglobin': 'hemoglobin',
            'location': 'location',
            'avatar': 'avatar'
        }
        
        for frontend_key, db_key in field_mapping.items():
            if frontend_key in data and data[frontend_key] is not None:
                update_fields[db_key] = data[frontend_key]
        
        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400
        
        update_fields['updated_at'] = datetime.now()
        
        # Update the profile
        result = db.user_profiles.update_one(
            {'user_id': user_id},
            {'$set': update_fields},
            upsert=True
        )
        
        print(f"✅ Profile updated: {result.modified_count} modified")
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'matched_count': result.matched_count,
            'modified_count': result.modified_count
        })
        
    except Exception as e:
        print(f"❌ Profile update error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
# ========== PROFILE GET ROUTE ==========
@app.route('/api/profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    """Get user profile from MongoDB Atlas"""
    try:
        db = get_db()
        
        profile = db.user_profiles.find_one({'user_id': user_id}, {'_id': 0})
        
        if not profile:
            return jsonify({'error': 'Profile not found'}), 404
        
        return jsonify({'success': True, 'profile': profile})
        
    except Exception as e:
        print(f"❌ Get profile error: {e}")
        return jsonify({'error': str(e)}), 500

# ========== HELPER FUNCTIONS ==========
def verify_password(password, stored_password):
    """Verify password - supports both plain text and SHA256"""
    if not stored_password:
        return False
    if len(stored_password) == 64 and all(c in '0123456789abcdef' for c in stored_password.lower()):
        return hashlib.sha256(password.encode()).hexdigest() == stored_password
    return stored_password == password

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

# ========== HEALTH CHECK ==========
@app.route('/api/health-check', methods=['GET'])
def health_check():
    """API health check endpoint - checks MongoDB Atlas connection"""
    try:
        db = get_db()
        db.command('ping')
        db_status = "connected"
        db_message = "MongoDB Atlas is connected"
    except Exception as e:
        db_status = "disconnected"
        db_message = str(e)
        
    return jsonify({
        "status": "healthy",
        "message": "LuminaLife API is running",
        "database": db_status,
        "database_message": db_message,
        "timestamp": datetime.now().isoformat()
    }), 200



# ========== HOSPITAL BLOOD REQUEST ROUTES (UPDATED) ==========

def get_compatible_blood_groups(blood_type):
    """Return all compatible blood groups for donation"""
    compatibility = {
        'O+': ['O+', 'O-'],
        'O-': ['O-'],
        'A+': ['A+', 'A-', 'O+', 'O-'],
        'A-': ['A-', 'O-'],
        'B+': ['B+', 'B-', 'O+', 'O-'],
        'B-': ['B-', 'O-'],
        'AB+': ['AB+', 'AB-', 'A+', 'A-', 'B+', 'B-', 'O+', 'O-'],
        'AB-': ['AB-', 'A-', 'B-', 'O-']
    }
    return compatibility.get(blood_type, [blood_type])
@app.route('/api/hospital/request-blood', methods=['POST'])
def hospital_request_blood():
    """Hospital requests blood or organs"""
    try:
        data = request.json
        db = get_db()

        request_type = data.get("request_type", "Blood")

        required_fields = [
            "hospital_id",
            "hospital_name",
            "units_needed"
        ]

        if request_type == "Blood":
            required_fields.append("blood_type_needed")
        else:
            required_fields.append("organ_type")

        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "success": False,
                    "message": f"{field} is required"
                }), 400

        emergency_id = f"EMG{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}"

        emergency = {
            "emergency_id": emergency_id,
            "request_type": request_type,
            "hospital_id": data["hospital_id"],
            "hospital_name": data["hospital_name"],
            "units_needed": int(data["units_needed"]),
            "priority": data.get("priority", "high"),
            "status": "active",
            "patient_name": data.get("patient_name", ""),
            "patient_age": data.get("patient_age"),
            "reason": data.get("reason", ""),
            "contact_person": data.get("contact_person", ""),
            "contact_phone": data.get("contact_phone", ""),
            "hospital_address": data.get("hospital_address", ""),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(
                hours=int(data.get("expires_in_hours", 4))
            ),
            "responders": 0,
            "matched_donors_notified": 0
        }

        if request_type == "Blood":
            blood_type = data["blood_type_needed"].upper()

            emergency["blood_type_needed"] = blood_type
            emergency["compatible_groups"] = get_compatible_blood_groups(
                blood_type
            )

            compatible_donors = list(
                db.user_profiles.find({
                    "blood_group": {
                        "$in": emergency["compatible_groups"]
                    },
                    "donor_status": "available",
                    "is_recovered": True
                })
            )

        else:
            organ_type = data["organ_type"]

            emergency["organ_type"] = organ_type

            compatible_donors = list(
                db.organ_donors.find({
                    "organ_types": organ_type,
                    "status": "active"
                })
            )

        db.emergency_requests.insert_one(emergency)

        notified_count = 0

        for donor in compatible_donors:

            donor_id = donor.get("user_id")

            notification = {
                "notification_id": str(uuid.uuid4()),
                "user_id": donor_id,
                "title": f"🚨 URGENT: {request_type} Needed",
                "message": (
                    f"{data['hospital_name']} requires "
                    f"{data.get('organ_type') if request_type == 'Organ' else data.get('blood_type_needed')}."
                ),
                "type": "emergency_request",
                "is_read": False,
                "created_at": datetime.now(),
                "priority": "high",
                "metadata": {
                    "emergency_id": emergency_id,
                    "request_type": request_type
                }
            }

            db.notifications.insert_one(notification)
            notified_count += 1

        db.emergency_requests.update_one(
            {"emergency_id": emergency_id},
            {
                "$set": {
                    "matched_donors_notified": notified_count
                }
            }
        )

        return jsonify({
            "success": True,
            "message": f"{request_type} request created successfully",
            "emergency_id": emergency_id,
            "notified_donors": notified_count
        }), 201

    except Exception as e:
        print("❌ Hospital request error:", e)
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
@app.route('/api/organ-donors', methods=['GET'])
def get_organ_donors():
    try:
        db = get_db()

        donors = list(
            db.organ_donors.find({}, {'_id': 0})
        )

        return jsonify({
            "success": True,
            "donors": donors
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/hospital/donors/compatible/<blood_type>', methods=['GET'])
def get_compatible_donors(blood_type):
    """Get count of compatible donors for a blood type"""
    try:
        db = get_db()
        compatible_groups = get_compatible_blood_groups(blood_type.upper())
        
        count = db.user_profiles.count_documents({
            'blood_group': {'$in': compatible_groups},
            'donor_status': 'available',
            'is_recovered': True
        })
        
        return jsonify({
            'success': True,
            'blood_type': blood_type.upper(),
            'compatible_groups': compatible_groups,
            'compatible_donors_count': count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

        
# ========== SERVE STATIC FILES ==========
@app.route('/')
def serve_index():
    try:
        return send_from_directory('../static', 'dashboard.html')
    except:
        return send_from_directory('../static', 'l.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../static', path)

# ========== NAVIGATION ROUTES ==========

# ========== SETTINGS ROUTES ==========
@app.route('/api/settings/<user_id>', methods=['GET'])
def get_user_settings(user_id):
    """Get user settings from MongoDB Atlas"""
    try:
        db = get_db()
        
        settings = db.user_settings.find_one({'user_id': user_id}, {'_id': 0})
        
        if not settings:
            # Create default settings
            default_settings = {
                'user_id': user_id,
                'theme': 'light',
                'notifications': {
                    'emergency_alerts': True,
                    'donation_reminders': True,
                    'health_updates': True,
                    'app_updates': False
                },
                'privacy': {
                    'show_blood_group': True,
                    'show_location': True,
                    'show_donation_history': True
                },
                'communication': {
                    'email': True,
                    'sms': False,
                    'push': True
                },
                'language': 'en',
                'timezone': 'Asia/Kolkata',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            db.user_settings.insert_one(default_settings)
            return jsonify({'settings': default_settings}), 200
        
        return jsonify({'settings': settings}), 200
        
    except Exception as e:
        print(f"❌ Settings error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/update', methods=['POST'])
def update_user_settings():
    """Update user settings in MongoDB Atlas"""
    try:
        data = request.json
        db = get_db()
        
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        # Remove user_id from update data
        update_data = {k: v for k, v in data.items() if k != 'user_id'}
        update_data['updated_at'] = datetime.now()
        
        result = db.user_settings.update_one(
            {'user_id': user_id},
            {'$set': update_data},
            upsert=True
        )
        
        return jsonify({
            'success': True,
            'message': 'Settings updated in MongoDB Atlas',
            'matched_count': result.matched_count,
            'modified_count': result.modified_count
        }), 200
        
    except Exception as e:
        print(f"❌ Settings update error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/settings/theme', methods=['POST'])
def update_theme():
    """Update user theme preference"""
    try:
        data = request.json
        db = get_db()
        
        user_id = data.get('user_id')
        theme = data.get('theme', 'light')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        db.user_settings.update_one(
            {'user_id': user_id},
            {'$set': {'theme': theme, 'updated_at': datetime.now()}},
            upsert=True
        )
        
        return jsonify({
            'success': True,
            'message': f'Theme updated to {theme}',
            'theme': theme
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

#===============AI ROUTE================================
@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """AI chat endpoint for health advice using Groq API"""
    try:
        data = request.json
        user_id = data.get('user_id')
        message = data.get('message', '')
        
        if not user_id:
            return jsonify({'reply': 'Please log in to use the AI assistant.'}), 400
        
        if not message:
            return jsonify({'reply': 'Please ask me a question about your health.'}), 400
        
        db = get_db()
        
        # Get latest health record
        health = db.health_records.find_one(
            {'user_id': user_id},
            sort=[('last_updated', -1)]
        )
        
        # Get user profile
        profile = db.user_profiles.find_one({'user_id': user_id})
        
        # Build context from user data with fallbacks
        hb = health.get('hemoglobin', 0) if health else 0
        weight = health.get('weight_kg', 0) if health else 0
        hydration = health.get('hydration', 0) if health else 0
        stress = health.get('stress', 0) if health else 0
        exercise = health.get('exercise_minutes', 0) if health else 0
        steps = health.get('steps', 0) if health else 0
        menstrual_day = health.get('menstrual_day', 0) if health else 0
        mood = health.get('mood', 'good') if health else 'good'
        blood_group = profile.get('blood_group', 'Unknown') if profile else 'Unknown'
        total_donations = profile.get('total_donations', 0) if profile else 0
        last_donation = profile.get('last_donation_date', None) if profile else None
        
        # Calculate eligibility
        eligible = False
        days_until_eligible = 0
        if last_donation:
            last = last_donation
            if isinstance(last, str):
                try:
                    last = datetime.fromisoformat(last.replace('Z', '+00:00'))
                except:
                    last = datetime.now() - timedelta(days=90)  # Fallback
            days_since = (datetime.now() - last).days
            days_until_eligible = max(0, 90 - days_since)
            eligible = (hb >= 12.5 and weight >= 50 and days_until_eligible == 0)
        
        # Check if on period (days 1-5)
        on_period = menstrual_day >= 1 and menstrual_day <= 5
        
        # Build system prompt with user context
        system_prompt = f"""You are Lumi, the intelligent health assistant of LuminaLife. 
You help users understand their health, blood donation readiness, hydration, nutrition, exercise, stress, hemoglobin levels, menstrual health, and overall wellness.

IMPORTANT RULES:
1. Answer the user's actual question first.
2. Do NOT always talk about blood donation eligibility.
3. Mention donation eligibility ONLY if the user's question is related to donating blood.
4. Give personalized answers based on the health data provided.
5. Be supportive, professional, and easy to understand.
6. Never diagnose diseases or replace a doctor.
7. Keep answers concise (3-6 sentences unless more detail is requested).
8. Use the donor's health metrics when giving advice.

USER HEALTH DATA:
- Hydration: {hydration} glasses (goal: 8 glasses)
- Stress: {stress}% (low is better, under 40% is ideal)
- Exercise: {exercise} minutes today (goal: 30+ minutes)
- Steps: {steps} steps (goal: 8000+ steps)
- Weight: {weight} kg (minimum for donation: 50kg)
- Hemoglobin: {hb} g/dL (minimum for donation: 12.5 g/dL)
- Blood group: {blood_group}
- Total donations: {total_donations}
- Last donation: {last_donation if last_donation else 'Never'}
- Days until eligible: {days_until_eligible}
- Currently eligible to donate: {eligible}
- Menstrual cycle day: {menstrual_day} (1-5 = on period)
- On period: {on_period}
- Current mood: {mood}

SPECIAL RULES:
- If the user expresses an emotion like "I'm stressed", "I'm anxious", "I'm worried", "I'm overwhelmed", or "I'm tired", acknowledge their feeling first with empathy before giving advice.
- If the user is on their period (days 1-5), mention that blood donation is temporarily paused and recommend iron-rich foods.
- Only provide eligibility information when the user specifically asks about blood donation or donation readiness.
- Never say "Not eligible yet. Wait X days." repeatedly - provide actionable advice instead.

RESPONSE BEHAVIOR:
- If the user asks about hydration → discuss water intake and hydration
- If the user asks about stress → discuss relaxation, sleep, and stress reduction
- If the user asks about exercise → discuss activity and fitness
- If the user asks about hemoglobin → discuss iron-rich foods and nutrition
- If the user asks about blood donation → discuss eligibility and donation readiness
- If the user asks about nutrition → discuss healthy foods and habits
- If the user asks about general health → analyze overall health metrics
- If the user asks about menstrual cycle → discuss menstrual health and donation considerations

Always provide actionable recommendations based on the user's data.
Your tone should feel like a premium healthcare companion inside LuminaLife.

Keep responses warm, encouraging, and under 4 sentences unless the user asks for more detail."""


        # Call Groq API
        print("AI QUESTION:", message)
        print("USING GROQ ROUTE")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        reply = response.choices[0].message.content
        print("AI REPLY:", reply)
        
        # If no reply from API, use fallback
        if not reply:
            reply = "I'm here to help! Ask me about your hydration, stress, exercise, hemoglobin, or donation eligibility."
        
        return jsonify({'reply': reply})
        
    except Exception as e:
        print(f"❌ AI chat error: {e}")
        # Return a helpful fallback response
        return jsonify({'reply': 'I apologize, but I\'m having trouble connecting right now. Please try again in a moment. In the meantime, remember to stay hydrated and get plenty of rest!'}), 200

# ========== GRAPH DATA ROUTE ==========
@app.route('/api/graph-data/<user_id>', methods=['GET'])
def get_graph_data(user_id):
    """Get weekly activity data for graphs"""
    try:
        db = get_db()
        
        # Get user's health records history
        health_records = list(db.health_records.find(
            {'user_id': user_id},
            {'_id': 0, 'created_at': 1, 'steps': 1, 'exercise_minutes': 1, 'hydration': 1}
        ).sort('created_at', -1).limit(7))
        
        if not health_records:
            return jsonify({
                'success': True,
                'steps': [0, 0, 0, 0, 0, 0, 0],
                'exercise': [0, 0, 0, 0, 0, 0, 0],
                'hydration': [0, 0, 0, 0, 0, 0, 0],
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            }), 200
        
        steps = [record.get('steps', 0) for record in reversed(health_records)]
        exercise = [record.get('exercise_minutes', 0) for record in reversed(health_records)]
        hydration = [record.get('hydration', 0) for record in reversed(health_records)]
        
        while len(steps) < 7:
            steps.insert(0, 0)
            exercise.insert(0, 0)
            hydration.insert(0, 0)
        
        return jsonify({
            'success': True,
            'steps': steps[-7:],
            'exercise': exercise[-7:],
            'hydration': hydration[-7:],
            'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        }), 200
        
    except Exception as e:
        print(f"❌ Graph data error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== INITIALIZE SAMPLE DATA ==========
def initialize_sample_data():
    """Initialize sample data for MongoDB Atlas"""
    try:
        with app.app_context():
            db = get_db()
            
            # Create indexes for better performance
            db.user_profiles.create_index([('user_id', 1)], unique=True)
            db.users.create_index([('user_id', 1)], unique=True)
            db.users.create_index([('email', 1)], unique=True)
            db.emergency_requests.create_index([('status', 1)])
            db.emergency_requests.create_index([('hospital_id', 1)])
            db.navigation_history.create_index([('user_id', 1)])
            db.navigation_history.create_index([('status', 1)])
            db.health_records.create_index([('user_id', 1)])
            db.health_records.create_index([('last_updated', -1)])
            
            print("✅ Indexes created in MongoDB Atlas")
            
            # Check if sample donor exists
            if db.users.count_documents({}) == 0:
                user_id = "D001"
                
                sample_user = {
                    "user_id": user_id,
                    "full_name": "Ira",
                    "email": "ira@gmail.com",
                    "password_hash": hash_password("password123"),
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                db.users.insert_one(sample_user)
                
                sample_profile = {
                    "user_id": user_id,
                    "full_name": "Ira",
                    "blood_group": "O+",
                    "phone": "+1-555-123-4567",
                    "email": "ira@gmail.com",
                    "age": 21,
                    "weight_kg": 62.0,
                    "height_cm": 165,
                    "avatar": "https://i.pinimg.com/736x/9a/d2/5e/9ad25e15e3d881a3fc9bdd2f86b2f740.jpg",
                    "total_donations": 4,
                    "lives_saved": 7,
                    "last_donation_date": datetime(2026, 1, 15),
                    "is_recovered": True,
                    "donor_status": "available",
                    "location": "Bengaluru",
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                db.user_profiles.insert_one(sample_profile)
                print("✅ Sample user and profile created in MongoDB Atlas")
                print("   📧 Email: ira@gmail.com")
                print("   🔑 Password: password123")
                
                # Sample health record with graph data
                sample_health = {
                    "user_id": user_id,
                    "hemoglobin": 14.5,
                    "weight_kg": 62.0,
                    "height_cm": 165,
                    "age": 21,
                    "gender": "Female",
                    "blood_pressure": "120/80",
                    "steps": 6200,
                    "exercise_minutes": 28,
                    "hydration": 5,
                    "created_at": datetime.now(),
                    "last_updated": datetime.now(),
                    "source": "initial_setup"
                }
                db.health_records.insert_one(sample_health)
                print("✅ Sample health record with graph data created")
                
                # Add sample health records for graph (last 7 days)
                print("📊 Creating sample graph data for last 7 days...")
                for i in range(1, 8):
                    date = datetime.now() - timedelta(days=i)
                    steps = random.randint(4000, 8000)
                    exercise = random.randint(15, 45)
                    hydration = random.randint(3, 7)
                    
                    graph_sample = {
                        "user_id": user_id,
                        "steps": steps,
                        "exercise_minutes": exercise,
                        "hydration": hydration,
                        "created_at": date,
                        "last_updated": date,
                        "source": "graph_sample"
                    }
                    db.health_records.insert_one(graph_sample)
                print(f"✅ Added 7 sample graph records")
            
            # Populate sample hospitals if empty
            if db.hospitals.count_documents({}) == 0:
                sample_hospitals = [
                    {
                        "hospital_id": "H001", 
                        "name": "Memorial Health", 
                        "latitude": 12.9750, 
                        "longitude": 77.6035,
                        "address": "456 Health Ave", 
                        "contact_number": "+1-555-987-6543",
                        "blood_inventory": {"A+": 15, "O+": 25, "B+": 12},
                        "emergency_status": True,
                        "rating": 4.8
                    },
                    {
                        "hospital_id": "H002", 
                        "name": "St. Luke's Medical", 
                        "latitude": 12.9820, 
                        "longitude": 77.6220,
                        "address": "789 Medical Plaza", 
                        "contact_number": "+1-555-654-3210",
                        "blood_inventory": {"A-": 8, "O+": 20, "AB+": 5},
                        "emergency_status": True,
                        "rating": 4.7
                    },
                    {
                        "hospital_id": "H003", 
                        "name": "City General", 
                        "latitude": 12.9580, 
                        "longitude": 77.6140,
                        "address": "101 City Rd", 
                        "contact_number": "+1-555-321-0987",
                        "blood_inventory": {"B+": 10, "O-": 8, "A+": 15},
                        "emergency_status": False,
                        "rating": 4.5
                    },
                    {
                        "hospital_id": "H004", 
                        "name": "Holy Cross Hospital", 
                        "latitude": 12.9650, 
                        "longitude": 77.5850,
                        "address": "222 Cross St", 
                        "contact_number": "+1-555-210-9876",
                        "blood_inventory": {"O+": 30, "A-": 12, "B-": 6},
                        "emergency_status": True,
                        "rating": 4.9
                    }
                ]
                db.hospitals.insert_many(sample_hospitals)
                print("✅ Sample hospitals populated in MongoDB Atlas")
                
            # Populate sample emergencies if empty
            if db.emergency_requests.count_documents({}) == 0:
                sample_emergencies = [
                    {
                        "emergency_id": "EMG001", 
                        "hospital_id": "H001",
                        "hospital_name": "Memorial Health",
                        "blood_type_needed": "A-", 
                        "units_needed": 3,
                        "priority": "critical", 
                        "status": "active",
                        "created_at": datetime.now(),
                        "expires_at": datetime.now() + timedelta(hours=4),
                        "responders": 0
                    },
                    {
                        "emergency_id": "EMG002", 
                        "hospital_id": "H004",
                        "hospital_name": "Holy Cross Hospital",
                        "blood_type_needed": "O+", 
                        "units_needed": 5,
                        "priority": "high", 
                        "status": "active",
                        "created_at": datetime.now(),
                        "expires_at": datetime.now() + timedelta(hours=3),
                        "responders": 0
                    },
                    {
                        "emergency_id": "EMG003", 
                        "hospital_id": "H002",
                        "hospital_name": "St. Luke's Medical",
                        "blood_type_needed": "AB+", 
                        "units_needed": 2,
                        "priority": "medium", 
                        "status": "active",
                        "created_at": datetime.now(),
                        "expires_at": datetime.now() + timedelta(hours=5),
                        "responders": 0
                    }
                ]
                db.emergency_requests.insert_many(sample_emergencies)
                print("✅ Sample emergencies populated in MongoDB Atlas")

            # Populate sample donations if empty
            if db.donations.count_documents({}) == 0:
                user_id = "D001"
                sample_donations = [
                    {
                        'user_id': user_id,
                        'hospital_name': 'Manipal Hospitals, Whitefield',
                        'blood_type': 'O+',
                        'status': 'completed',
                        'completed_at': datetime.now() - timedelta(days=30),
                        'created_at': datetime.now() - timedelta(days=30)
                    },
                    {
                        'user_id': user_id,
                        'hospital_name': 'Apollo Hospitals, Bannerghatta',
                        'blood_type': 'O+',
                        'status': 'completed',
                        'completed_at': datetime.now() - timedelta(days=120),
                        'created_at': datetime.now() - timedelta(days=120)
                    },
                    {
                        'user_id': user_id,
                        'hospital_name': 'Fortis Hospital, Cunningham Road',
                        'blood_type': 'O+',
                        'status': 'completed',
                        'completed_at': datetime.now() - timedelta(days=210),
                        'created_at': datetime.now() - timedelta(days=210)
                    }
                ]
                db.donations.insert_many(sample_donations)
                print("✅ Sample donation history created")
                
    except Exception as e:
        print(f"⚠️ Error initializing sample data: {e}")

# ========== MAIN ==========
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 LuminaLife Blood Donation Management System Backend")
    print("📦 MongoDB Atlas Integration")
    print("=" * 60)
    print("📍 Server URL: http://127.0.0.1:5000")
    print("📋 Available Endpoints:")
    print("   POST   /api/profile/update - Update profile in MongoDB Atlas")
    print("   GET    /api/profile/<user_id> - Get profile from MongoDB Atlas")
    print("   GET    /api/emergencies - Get active emergencies")
    print("   POST   /api/donations/complete - Complete donation")
    print("   POST   /api/donor/update-stats - Update donor stats")
    print("   POST   /api/donor/organ-register - Register organ donor")
    print("   POST   /api/navigation/start - Start navigation")
    print("   POST   /api/navigation/complete - Complete navigation")
    print("   GET    /api/notifications/<user_id> - Get notifications")
    print("   GET    /api/graph-data/<user_id> - Get graph data")
    print("=" * 60)
    print("📊 MongoDB Collections Used:")
    print("   📁 user_profiles - Main donor profile data")
    print("   📁 users - Authentication & basic user info")
    print("   📁 health_records - Health metrics & history")
    print("   📁 donations - Donation records")
    print("   📁 emergency_requests - Hospital emergency requests")
    print("   📁 notifications - User notifications")
    print("   📁 navigation_history - Navigation tracking")
    print("   📁 hospitals - Hospital information")
    print("=" * 60)
    
    initialize_sample_data()
    
    print("=" * 60)
    print("✨ Server is ready! Press Ctrl+C to stop")
    print("📝 Test Login: ira@gmail.com / password123")
    print("📝 Dashboard: http://127.0.0.1:5000/dashboard.html")
    print("📝 Profile: http://127.0.0.1:5000/profile.html")
    print("=" * 60)
    
import os

app.run(
    host='0.0.0.0',
    port=int(os.environ.get("PORT", 5000))
)