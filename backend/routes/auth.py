from flask import Blueprint, request, jsonify
from database.db import get_db
from datetime import datetime
import hashlib
import uuid
import re
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
def verify_password(password, stored_password):
    return hash_password(password) == stored_password
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
def validate_phone(phone):
    phone_clean = phone.replace('+', '').replace('-', '').replace(' ', '')
    return len(phone_clean) >= 10 and phone_clean.isdigit()
def generate_user_id():
    return f"D{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.json or {}
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        blood_group = data.get('blood_group', 'O+')
        age = data.get('age')
        weight_kg = data.get('weight_kg')
        
        # Validations
        if not name:
            return jsonify({"error": "Full name is required"}), 400
        if not email or not validate_email(email):
            return jsonify({"error": "Valid email is required"}), 400
        if not phone or not validate_phone(phone):
            return jsonify({"error": "Valid phone number is required"}), 400
        if not password or len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        
        # Validate age (18-65)
        try:
            age_int = int(age) if age is not None else 25
            if not (18 <= age_int <= 65):
                return jsonify({"error": "Age must be between 18 and 65"}), 400
        except ValueError:
            return jsonify({"error": "Age must be a valid integer"}), 400
        # Validate weight (>= 50)
                # Validate weight (>= 50)
        if weight_kg is None:
            weight_kg = 65.0
        
        try:
            weight_float = float(weight_kg)
            if weight_float < 50.0:
                return jsonify({"error": "Weight must be at least 50 kg"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Weight must be a valid number"}), 400
        except ValueError:
            return jsonify({"error": "Weight must be a valid number"}), 400
            
        db = get_db()
        
        # Check if user already exists
        existing = db.users.find_one({"email": email})
        if existing:
            return jsonify({"error": "Email already registered"}), 400
            
        user_id = generate_user_id()
        hashed_password = hash_password(password)
        
        # Insert credentials in users collection
        user_doc = {
            "user_id": user_id,
            "email": email,
            "password_hash": hashed_password,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        db.users.insert_one(user_doc)
        
        # Insert profile in user_profiles collection
        profile_doc = {
            "user_id": user_id,
            "full_name": name,
            "blood_group": blood_group,
            "phone": phone,
            "email": email,
            "age": age_int,
            "weight_kg": weight_float,
            "avatar": data.get('avatar', 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png'),
            "total_donations": 0,
            "lives_saved": 0,
            "last_donation_date": None,
            "is_recovered": True,
            "donor_status": "available",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        db.user_profiles.insert_one(profile_doc)
        
        # Create default health record
        health_doc = {
            "user_id": user_id,
            "hemoglobin": 14.5,
            "hydration": 85,
            "energy": 88,
            "blood_pressure": "120/80",
            "stress": "Low",
            "eligibility": "Eligible",
            "last_updated": datetime.now()
        }
        db.health_records.insert_one(health_doc)
        
        # Create welcome notification
        notification = {
            "notification_id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": "Welcome to LuminaLife! 🩸",
            "message": f"Thank you {name} for joining our life-saving community.",
            "type": "success",
            "is_read": False,
            "created_at": datetime.now(),
            "priority": "high"
        }
        db.notifications.insert_one(notification)
        
        # Create token
        token = hashlib.sha256(f"{user_id}{datetime.now().timestamp()}".encode()).hexdigest()
        
        return jsonify({
            "message": "Account created successfully",
            "status": "success",
            "userId": user_id,
            "token": token,
            "user": {
                "userId": user_id,
                "name": name,
                "email": email,
                "blood_group": blood_group
            }
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.json or {}
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400
            
        db = get_db()
        user = db.users.find_one({"email": email})
        
        if not user or not verify_password(password, user.get("password_hash", "")):
            return jsonify({"error": "Invalid email or password"}), 401
            
        user_id = user["user_id"]
        profile = db.user_profiles.find_one({"user_id": user_id})
        
        # Generate token
        token = hashlib.sha256(f"{user_id}{datetime.now().timestamp()}".encode()).hexdigest()
        
        return jsonify({
            "message": "Login successful",
            "status": "success",
            "userId": user_id,
            "token": token,
            "user": {
                "userId": user_id,
                "name": profile.get("full_name") if profile else "User",
                "email": email,
                "blood_group": profile.get("blood_group") if profile else "O+",
                "total_donations": profile.get("total_donations", 0) if profile else 0
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@auth_bp.route('/logout', methods=['POST'])
def logout():
    return jsonify({"success": True, "message": "Logged out successfully"}), 200