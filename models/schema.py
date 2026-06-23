"""
MongoDB Collection Schemas and Sample Documents
"""

# DONORS Collection Schema
DONOR_SCHEMA = {
    "user_id": "string (unique)",
    "email": "string (unique)",
    "password_hash": "string",
    "full_name": "string",
    "age": "integer (18-65)",
    "blood_group": "string (A+, A-, B+, B-, AB+, AB-, O+, O-)",
    "weight_kg": "float (>= 50)",
    "phone": "string",
    "address": {
        "street": "string",
        "city": "string",
        "state": "string",
        "zip_code": "string",
        "latitude": "float",
        "longitude": "float"
    },
    "total_donations": "integer",
    "lives_saved": "integer",
    "last_donation_date": "datetime",
    "is_recovered": "boolean",
    "donor_status": "string (available/unavailable/emergency)",
    "created_at": "datetime",
    "updated_at": "datetime",
    "is_verified": "boolean"
}

# Sample Donor Document
SAMPLE_DONOR = {
    "user_id": "D001",
    "email": "sophia.chen@example.com",
    "full_name": "Sophia Chen",
    "age": 29,
    "blood_group": "O+",
    "weight_kg": 68,
    "phone": "+1-555-123-4567",
    "address": {
        "street": "123 Main Street",
        "city": "New York",
        "state": "NY",
        "zip_code": "10001",
        "latitude": 40.7128,
        "longitude": -74.0060
    },
    "total_donations": 14,
    "lives_saved": 24,
    "last_donation_date": "2026-02-20T00:00:00Z",
    "is_recovered": True,
    "donor_status": "available",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2026-06-10T14:20:00Z",
    "is_verified": True
}

# HEALTH Collection Schema
HEALTH_SCHEMA = {
    "user_id": "string",
    "hemoglobin": "float (g/dL)",
    "hydration": "integer (%)",
    "energy": "integer (%)",
    "blood_pressure": "string (e.g., 120/80)",
    "stress": "string (Low/Medium/High)",
    "eligibility": "string (Eligible/Not Eligible)",
    "last_updated": "datetime",
    "medical_conditions": "array",
    "medications": "array"
}

# Sample Health Document
SAMPLE_HEALTH = {
    "user_id": "D001",
    "hemoglobin": 14.5,
    "hydration": 88,
    "energy": 91,
    "blood_pressure": "120/80",
    "stress": "Low",
    "eligibility": "Eligible",
    "last_updated": "2026-06-10T08:00:00Z",
    "medical_conditions": [],
    "medications": []
}

# HOSPITALS Collection Schema
HOSPITAL_SCHEMA = {
    "hospital_id": "integer",
    "name": "string",
    "location": {
        "type": "Point",
        "coordinates": ["longitude", "latitude"]
    },
    "address": "string",
    "distance_from_city": "float (km)",
    "blood_demand": "integer (%)",
    "urgency_score": "integer (%)",
    "availability": "integer (%)",
    "blood_types_needed": "array",
    "rating": "float",
    "contact_number": "string",
    "emergency_capacity": "integer"
}

# Sample Hospital Document
SAMPLE_HOSPITAL = {
    "hospital_id": 1,
    "name": "Memorial Health",
    "location": {
        "type": "Point",
        "coordinates": [-74.0123, 40.7128]
    },
    "address": "456 Health Ave, New York, NY 10001",
    "distance_from_city": 1.2,
    "blood_demand": 95,
    "urgency_score": 98,
    "availability": 92,
    "blood_types_needed": ["A-", "O+", "AB-"],
    "rating": 4.8,
    "contact_number": "+1-555-987-6543",
    "emergency_capacity": 50
}

# NOTIFICATIONS Collection Schema
NOTIFICATION_SCHEMA = {
    "user_id": "string",
    "title": "string",
    "message": "string",
    "type": "string (emergency/info/reminder/success)",
    "is_read": "boolean",
    "created_at": "datetime",
    "priority": "string (high/medium/low)",
    "metadata": "object"
}

# Sample Notification Document
SAMPLE_NOTIFICATION = {
    "user_id": "D001",
    "title": "Emergency Blood Request",
    "message": "⚠️ New emergency: A- blood required at Memorial Health",
    "type": "emergency",
    "is_read": False,
    "created_at": "2026-06-10T09:15:00Z",
    "priority": "high",
    "metadata": {
        "hospital_id": 1,
        "blood_type": "A-",
        "units_needed": 2
    }
}

# APPOINTMENTS Collection Schema
APPOINTMENT_SCHEMA = {
    "appointment_id": "string",
    "user_id": "string",
    "hospital_id": "integer",
    "hospital_name": "string",
    "date": "string (YYYY-MM-DD)",
    "time": "string",
    "status": "string (Booked/Completed/Cancelled/No-Show)",
    "created_at": "datetime",
    "updated_at": "datetime",
    "notes": "string"
}

# DONATION_HISTORY Collection Schema
DONATION_HISTORY_SCHEMA = {
    "donation_id": "string",
    "user_id": "string",
    "hospital_id": "integer",
    "hospital_name": "string",
    "donation_date": "datetime",
    "blood_type": "string",
    "units_donated": "integer",
    "status": "string (Completed/In Progress)",
    "health_check": {
        "hemoglobin": "float",
        "blood_pressure": "string",
        "weight": "float"
    },
    "recovery_notes": "string",
    "certificate_url": "string"
}