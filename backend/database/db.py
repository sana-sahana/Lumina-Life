from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from flask import g, current_app
import logging
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)

def get_db():
    """Get database connection using Flask's application context"""
    if 'db' not in g:
        try:
            client = MongoClient(
                current_app.config['MONGO_URI'],
                serverSelectionTimeoutMS=5000,
                tlsAllowInvalidCertificates=True
            )
            # Test connection
            client.admin.command('ping')
            g.db = client[current_app.config['MONGO_DB_NAME']]
            logger.info("Connected to MongoDB successfully")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise
    return g.db

def close_db(e=None):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.client.close()

def init_app(app):
    """Initialize database with app context and create indexes"""
    app.teardown_appcontext(close_db)
    
    with app.app_context():
        db = get_db()
        
        # ============ CREATE COLLECTIONS IF NOT EXIST ============
        # List of required collections
        required_collections = [
            'users', 'user_profiles', 'hospitals', 'donations', 
            'emergency_requests', 'notifications', 'navigation_history',
            'health_records', 'appointments', 'tracker', 'hospital_notifications'
        ]
        
        existing_collections = db.list_collection_names()
        for collection in required_collections:
            if collection not in existing_collections:
                db.create_collection(collection)
                print(f"✅ Created collection: {collection}")
        
        # ============ CREATE INDEXES ============
        
        # Users collection
        db.users.create_index('user_id', unique=True)
        db.users.create_index('email', unique=True)
        print("✅ Indexes created for: users")
        
        # User profiles collection
        db.user_profiles.create_index('user_id', unique=True)
        db.user_profiles.create_index([('current_location.coordinates', '2dsphere')])
        print("✅ Indexes created for: user_profiles")
        
        # Health records collection
        db.health_records.create_index('user_id', unique=True)
        print("✅ Indexes created for: health_records")
        
        # Hospitals collection
        db.hospitals.create_index('hospital_id', unique=True)
        db.hospitals.create_index([('location.coordinates', '2dsphere')])
        print("✅ Indexes created for: hospitals")
        
        # Donations collection
        db.donations.create_index('donation_id', unique=True)
        db.donations.create_index([('user_id', 1), ('created_at', -1)])
        db.donations.create_index([('hospital_id', 1), ('created_at', -1)])
        db.donations.create_index('status')
        print("✅ Indexes created for: donations")
        
        # Emergency requests collection
        db.emergency_requests.create_index('emergency_id', unique=True)
        db.emergency_requests.create_index([('status', 1), ('expires_at', 1)])
        db.emergency_requests.create_index('priority')
        print("✅ Indexes created for: emergency_requests")
        
        # Notifications collection (for users)
        db.notifications.create_index([('user_id', 1), ('created_at', -1)])
        db.notifications.create_index('is_read')
        db.notifications.create_index('type')
        print("✅ Indexes created for: notifications")
        
        # Hospital notifications collection
        db.hospital_notifications.create_index([('hospital_id', 1), ('created_at', -1)])
        db.hospital_notifications.create_index('is_read')
        db.hospital_notifications.create_index('type')
        print("✅ Indexes created for: hospital_notifications")
        
        # Navigation history collection
        db.navigation_history.create_index([('user_id', 1), ('created_at', -1)])
        print("✅ Indexes created for: navigation_history")
        
        # Appointments collection
        db.appointments.create_index([('user_id', 1), ('date', 1), ('status', 1)])
        print("✅ Indexes created for: appointments")
        
        # Tracker collection
        db.tracker.create_index('user_id', unique=True)
        print("✅ Indexes created for: tracker")
        
        # ============ SEED INITIAL DATA ============
        seed_initial_data(db)
        
def seed_initial_data(db):
    """Seed initial hospitals and sample data"""
    
    # ============ SEED HOSPITALS ============
    if db.hospitals.count_documents({}) == 0:
        hospitals = [
            {
                'hospital_id': 'H001',
                'name': 'Memorial Health Center',
                'address': '123 Healthcare Ave, Downtown',
                'latitude': 12.9750,
                'longitude': 77.6035,
                'phone': '+1-555-0101',
                'blood_inventory': {
                    'A+': 15, 'A-': 8, 'B+': 12, 'B-': 5,
                    'O+': 25, 'O-': 10, 'AB+': 6, 'AB-': 3
                },
                'emergency_status': True,
                'rating': 4.8,
                'operating_hours': '24/7'
            },
            {
                'hospital_id': 'H002',
                'name': "St. Luke's Medical Center",
                'address': '456 Medical Blvd, Westside',
                'latitude': 12.9820,
                'longitude': 77.6220,
                'phone': '+1-555-0102',
                'blood_inventory': {
                    'A+': 8, 'A-': 3, 'B+': 6, 'B-': 2,
                    'O+': 12, 'O-': 4, 'AB+': 2, 'AB-': 1
                },
                'emergency_status': True,
                'rating': 4.7,
                'operating_hours': '24/7'
            },
            {
                'hospital_id': 'H003',
                'name': 'City General Hospital',
                'address': '789 Health Street, Eastside',
                'latitude': 12.9580,
                'longitude': 77.6140,
                'phone': '+1-555-0103',
                'blood_inventory': {
                    'A+': 20, 'A-': 10, 'B+': 15, 'B-': 7,
                    'O+': 30, 'O-': 12, 'AB+': 8, 'AB-': 4
                },
                'emergency_status': False,
                'rating': 4.6,
                'operating_hours': '8:00 AM - 10:00 PM'
            },
            {
                'hospital_id': 'H004',
                'name': 'Holy Cross Hospital',
                'address': '321 Faith Road, Northside',
                'latitude': 12.9650,
                'longitude': 77.5850,
                'phone': '+1-555-0104',
                'blood_inventory': {
                    'A+': 5, 'A-': 2, 'B+': 4, 'B-': 1,
                    'O+': 8, 'O-': 3, 'AB+': 1, 'AB-': 0
                },
                'emergency_status': True,
                'rating': 4.9,
                'operating_hours': '24/7'
            }
        ]
        db.hospitals.insert_many(hospitals)
        print("✅ Seeded 4 hospitals")
    
    # ============ SEED HEALTH RECORDS ============
    if db.health_records.count_documents({}) == 0:
        health_records = [
            {
                'user_id': 'D001',
                'hemoglobin': 14.2,
                'hydration': 85,
                'energy': 88,
                'blood_pressure': '120/80',
                'stress': 'Low',
                'eligibility': 'Eligible',
                'weight_kg': 62,
                'sleep_hours': 7.5,
                'illness': 'none',
                'last_updated': datetime.now()
            }
        ]
        db.health_records.insert_many(health_records)
        print("✅ Seeded health records")
    
    # ============ SEED EMERGENCY REQUESTS ============
    if db.emergency_requests.count_documents({}) == 0:
        emergencies = [
            {
                'emergency_id': 'EMG001',
                'hospital_id': 'H001',
                'hospital_name': 'Memorial Health Center',
                'blood_type_needed': 'O+',
                'units_needed': 3,
                'priority': 'critical',
                'status': 'active',
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(hours=4),
                'responding_donors': []
            },
            {
                'emergency_id': 'EMG002',
                'hospital_id': 'H004',
                'hospital_name': 'Holy Cross Hospital',
                'blood_type_needed': 'A-',
                'units_needed': 2,
                'priority': 'high',
                'status': 'active',
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(hours=3),
                'responding_donors': []
            }
        ]
        db.emergency_requests.insert_many(emergencies)
        print("✅ Seeded 2 emergency requests")
    
    # ============ SEED SAMPLE USER ============
    if db.users.count_documents({}) == 0:
        user_id = 'D001'
        password_hash = hashlib.sha256('password123'.encode()).hexdigest()
        
        db.users.insert_one({
            'user_id': user_id,
            'email': 'donor@luminalife.com',
            'password_hash': password_hash,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        
        db.user_profiles.insert_one({
            'user_id': user_id,
            'full_name': 'Medini Shetty',
            'blood_group': 'O+',
            'phone': '+1-555-123-4567',
            'email': 'donor@luminalife.com',
            'age': 21,
            'weight_kg': 62,
            'total_donations': 4,
            'lives_saved': 12,
            'last_donation_date': datetime.now() - timedelta(days=120),
            'is_recovered': True,
            'donor_status': 'available',
            'current_location': {
                'type': 'Point',
                'coordinates': [77.5946, 12.9716]
            },
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        print("✅ Created sample donor account")
        print("   📧 Email: donor@luminalife.com")
        print("   🔑 Password: password123")
    
    # ============ SEED SAMPLE NOTIFICATION ============
    if db.notifications.count_documents({}) == 0:
        import uuid
        notification = {
            'notification_id': str(uuid.uuid4()),
            'user_id': 'D001',
            'title': 'Welcome to LuminaLife!',
            'message': 'Thank you for joining our life-saving community. Update your health status to start donating.',
            'type': 'success',
            'is_read': False,
            'created_at': datetime.now(),
            'priority': 'high'
        }
        db.notifications.insert_one(notification)
        print("✅ Seeded welcome notification")
    
    print("=" * 50)
    print("🎉 Database initialization complete!")
    print("=" * 50)