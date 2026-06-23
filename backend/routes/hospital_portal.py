print("HOSPITAL PORTAL FILE LOADED")
from flask import Blueprint, jsonify, request
from database.db import get_db
from datetime import datetime

hospital_portal_bp = Blueprint(
    'hospital_portal',
    __name__,
    url_prefix='/api/hospital-portal'
)

# ------------------------
# HOSPITAL LOGIN
# ------------------------
@hospital_portal_bp.route('/login', methods=['POST'])
def hospital_login():

    try:
        data = request.json

        email = data.get('email')
        password = data.get('password')

        db = get_db()

        hospital = db.hospital_portal_accounts.find_one({
            'email': email
        })

        if not hospital:
            return jsonify({
                'success': False,
                'message': 'Hospital not found'
            }), 404

        if hospital['password'] != password:
            return jsonify({
                'success': False,
                'message': 'Wrong password'
            }), 401

        return jsonify({
            'success': True,
            'hospital_id': hospital['hospital_id'],
            'hospital_name': hospital['hospital_name']
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ------------------------
# HOSPITAL PROFILE
# ------------------------
@hospital_portal_bp.route('/profile/<hospital_id>')
def hospital_profile(hospital_id):

    db = get_db()

    profile = db.hospital_portal_profiles.find_one(
        {'hospital_id': hospital_id},
        {'_id': 0}
    )

    return jsonify({
        'success': True,
        'profile': profile
    })


# ------------------------
# CREATE REQUEST
# ------------------------
@hospital_portal_bp.route('/request', methods=['POST'])
def create_request():

    print("CREATE REQUEST HIT")

    data = request.json

    db = get_db()

    
    request_doc = {
    'request_id': f"REQ{int(datetime.now().timestamp())}",
    'hospital_id': data.get('hospital_id'),
    'patient_id': data.get('patient_id'),
    'request_type': data.get('request_type'),
    'blood_group': data.get('blood_group'),
    'organ_type': data.get('organ_type'),
    'priority': data.get('priority'),
    'area': data.get('area'),
    'notes': data.get('notes'),
    'units': data.get('units'),
    'status': 'Pending',
    'created_at': datetime.now()
}

    print(data)
    print(request_doc)
    db.hospital_portal_requests.insert_one(request_doc)

    return jsonify({'success': True})


# ------------------------
# REQUEST STATUS
# ------------------------
@hospital_portal_bp.route('/requests/<hospital_id>')
def request_status(hospital_id):

    db = get_db()

    requests = list(
        db.hospital_portal_requests.find(
            {'hospital_id': hospital_id},
            {'_id': 0}
        )
    )

    return jsonify({
        'success': True,
        'requests': requests
    })


# ------------------------
# DASHBOARD
# ------------------------
@hospital_portal_bp.route('/dashboard/<hospital_id>')
def dashboard(hospital_id):

    db = get_db()

    total = db.hospital_portal_requests.count_documents({
        'hospital_id': hospital_id
    })

    pending = db.hospital_portal_requests.count_documents({
        'hospital_id': hospital_id,
        'status': 'Pending'
    })

    return jsonify({
        'success': True,
        'total_requests': total,
        'pending_requests': pending
    })
@hospital_portal_bp.route('/test')
def test():
    return jsonify({
        "success": True,
        "message": "Hospital Portal Working"
    })
@hospital_portal_bp.route('/hello')
def hello():
    return "HELLO"
@hospital_portal_bp.route('/all-routes')
def all_routes():

    from flask import current_app

    routes = []

    for rule in current_app.url_map.iter_rules():

        routes.append({
            "endpoint": rule.endpoint,
            "methods": list(rule.methods),
            "route": str(rule)
        })

    return jsonify(routes)