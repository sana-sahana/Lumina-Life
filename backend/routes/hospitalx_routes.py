from flask import Blueprint, jsonify, request
from database.db import get_db
from datetime import datetime

hospitalx_bp = Blueprint('hospitalx', __name__)

# ----------------------
# LOGIN
# ----------------------
@hospitalx_bp.route('/hospitalx/login', methods=['POST'])
def hospitalx_login():

    data = request.json

    db = get_db()

    hospital = db.hospitalx_accounts.find_one({
        "email": data.get("email")
    })

    if not hospital:
        return jsonify({
            "success": False,
            "message": "Hospital not found"
        })

    if hospital["password"] != data["password"]:
        return jsonify({
            "success": False,
            "message": "Wrong password"
        })

    return jsonify({
        "success": True,
        "hospital_id": hospital["hospital_id"],
        "hospital_name": hospital["hospital_name"]
    })


# ----------------------
# PROFILE
# ----------------------
@hospitalx_bp.route('/hospitalx/profile/<hospital_id>')
def hospitalx_profile(hospital_id):

    db = get_db()

    profile = db.hospitalx_profiles.find_one(
        {"hospital_id": hospital_id},
        {"_id": 0}
    )

    return jsonify(profile)


# ----------------------
# CREATE REQUEST
# ----------------------
@hospitalx_bp.route('/hospitalx/request', methods=['POST'])
def hospitalx_request():

    db = get_db()

    data = request.json

    data["created_at"] = datetime.now().strftime("%Y-%m-%d")

    db.hospitalx_requests.insert_one(data)

    return jsonify({
        "success": True
    })


# ----------------------
# REQUEST STATUS
# ----------------------
@hospitalx_bp.route('/hospitalx/request-status/<hospital_id>')
def hospitalx_request_status(hospital_id):

    db = get_db()

    requests = list(
        db.hospitalx_requests.find(
            {"hospital_id": hospital_id},
            {"_id": 0}
        )
    )

    return jsonify({
        "success": True,
        "requests": requests
    })


# ----------------------
# DASHBOARD
# ----------------------
@hospitalx_bp.route('/hospitalx/dashboard/<hospital_id>')
def hospitalx_dashboard(hospital_id):

    db = get_db()

    total = db.hospitalx_requests.count_documents({
        "hospital_id": hospital_id
    })

    pending = db.hospitalx_requests.count_documents({
        "hospital_id": hospital_id,
        "status": "Pending"
    })

    approved = db.hospitalx_requests.count_documents({
        "hospital_id": hospital_id,
        "status": "Approved"
    })

    return jsonify({
        "success": True,
        "total_requests": total,
        "pending_requests": pending,
        "approved_requests": approved
    })