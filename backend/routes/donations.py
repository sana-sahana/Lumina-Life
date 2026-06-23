from flask import Blueprint, jsonify, request
from database.db import get_db
from datetime import datetime
import uuid

donations_bp = Blueprint('donations', __name__, url_prefix='/api')

@donations_bp.route('/donations/register', methods=['POST'])
def register_donation():
    """Register a new donation - sends notifications to both user and hospital"""
    try:
        data = request.json
        db = get_db()
        
        user_id = data.get('user_id')
        hospital_id = data.get('hospital_id')
        hospital_name = data.get('hospital_name')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        # Get user's health data and profile
        health_data = db.health_records.find_one({'user_id': user_id})
        user_profile = db.user_profiles.find_one({'user_id': user_id})
        
        # Create donation record
        donation = {
            'donation_id': str(uuid.uuid4()),
            'user_id': user_id,
            'user_name': user_profile.get('full_name') if user_profile else 'Donor',
            'user_email': user_profile.get('email') if user_profile else '',
            'user_phone': user_profile.get('phone') if user_profile else '',
            'hospital_id': hospital_id,
            'hospital_name': hospital_name,
            'donation_type': data.get('donation_type', 'whole_blood'),
            'blood_group': data.get('blood_group') or (user_profile.get('blood_group') if user_profile else 'O+'),
            'units': data.get('units', 1),
            'scheduled_date': data.get('scheduled_date'),
            'scheduled_time': data.get('scheduled_time'),
            'health_metrics_at_donation': {
                'hemoglobin': health_data.get('hemoglobin') if health_data else None,
                'blood_pressure': health_data.get('blood_pressure') if health_data else None,
                'weight_kg': user_profile.get('weight_kg') if user_profile else None,
                'hydration': health_data.get('hydration') if health_data else None
            },
            'status': 'scheduled',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        db.donations.insert_one(donation)
        
        # ========== NOTIFICATION 1: TO DONOR (Success Confirmation) ==========
        donor_notification = {
            'notification_id': str(uuid.uuid4()),
            'user_id': user_id,
            'title': '✅ Donation Scheduled Successfully!',
            'message': f'Your blood donation at {hospital_name} on {data.get("scheduled_date")} at {data.get("scheduled_time")} has been scheduled. Thank you for saving lives!',
            'type': 'success',
            'is_read': False,
            'created_at': datetime.now(),
            'priority': 'high',
            'metadata': {
                'donation_id': donation['donation_id'],
                'hospital_name': hospital_name,
                'scheduled_date': data.get('scheduled_date')
            }
        }
        db.notifications.insert_one(donor_notification)
        
        # ========== NOTIFICATION 2: TO HOSPITAL (New Donation Request) ==========
        # Check if hospital_notifications collection exists, create if not
        if 'hospital_notifications' not in db.list_collection_names():
            db.create_collection('hospital_notifications')
        
        hospital_notification = {
            'notification_id': str(uuid.uuid4()),
            'hospital_id': hospital_id,
            'hospital_name': hospital_name,
            'title': '🩸 New Donation Scheduled',
            'message': f'Donor {user_profile.get("full_name") if user_profile else "Anonymous"} has scheduled a {donation["donation_type"]} donation.\n\n📋 Details:\n• Blood Group: {donation["blood_group"]}\n• Units: {donation["units"]}\n• Date: {data.get("scheduled_date")}\n• Time: {data.get("scheduled_time")}\n• Contact: {user_profile.get("phone") if user_profile else "N/A"}',
            'type': 'donation_request',
            'is_read': False,
            'created_at': datetime.now(),
            'priority': 'high',
            'metadata': {
                'donation_id': donation['donation_id'],
                'user_id': user_id,
                'donor_name': user_profile.get('full_name') if user_profile else 'Donor',
                'donor_phone': user_profile.get('phone') if user_profile else '',
                'donor_email': user_profile.get('email') if user_profile else ''
            }
        }
        db.hospital_notifications.insert_one(hospital_notification)
        
        # ========== UPDATE USER PROFILE with last donation request ==========
        db.user_profiles.update_one(
            {'user_id': user_id},
            {'$set': {
                'last_donation_request_date': datetime.now(),
                'pending_donation_id': donation['donation_id']
            }}
        )
        
        return jsonify({
            'success': True,
            'message': 'Donation registered successfully! Hospital has been notified.',
            'donation_id': donation['donation_id'],
            'donation': donation
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@donations_bp.route('/donations/user/<user_id>', methods=['GET'])
def get_user_donations(user_id):
    """Get all donations for a user"""
    try:
        db = get_db()
        donations = list(db.donations.find(
            {'user_id': user_id},
            {'_id': 0}
        ).sort('created_at', -1))
        
        return jsonify({'success': True, 'donations': donations}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@donations_bp.route('/donations/hospital/<hospital_id>', methods=['GET'])
def get_hospital_donations(hospital_id):
    """Get all donations for a hospital"""
    try:
        db = get_db()
        donations = list(db.donations.find(
            {'hospital_id': hospital_id},
            {'_id': 0}
        ).sort('created_at', -1))
        
        return jsonify({'success': True, 'donations': donations}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@donations_bp.route('/donations/<donation_id>/status', methods=['PUT'])
def update_donation_status(donation_id):
    """Update donation status (completed/cancelled)"""
    try:
        data = request.json
        db = get_db()
        
        new_status = data.get('status')
        if new_status not in ['scheduled', 'completed', 'cancelled', 'in_progress']:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        donation = db.donations.find_one({'donation_id': donation_id})
        if not donation:
            return jsonify({'success': False, 'message': 'Donation not found'}), 404
        
        # Update donation
        db.donations.update_one(
            {'donation_id': donation_id},
            {'$set': {
                'status': new_status,
                'updated_at': datetime.now(),
                'completed_date': datetime.now() if new_status == 'completed' else None
            }}
        )
        
        # If completed, update user stats
        if new_status == 'completed':
            user_id = donation.get('user_id')
            user_profile = db.user_profiles.find_one({'user_id': user_id})
            
            new_total = (user_profile.get('total_donations', 0) + 1) if user_profile else 1
            new_lives_saved = (user_profile.get('lives_saved', 0) + 3) if user_profile else 3
            
            db.user_profiles.update_one(
                {'user_id': user_id},
                {'$set': {
                    'total_donations': new_total,
                    'lives_saved': new_lives_saved,
                    'last_donation_date': datetime.now(),
                    'is_recovered': False,
                    'updated_at': datetime.now()
                }}
            )
            
            # Send completion notification to donor
            db.notifications.insert_one({
                'notification_id': str(uuid.uuid4()),
                'user_id': user_id,
                'title': '🎉 Donation Completed!',
                'message': f'Your donation at {donation.get("hospital_name")} has been completed. You\'ve saved 3 lives!',
                'type': 'success',
                'is_read': False,
                'created_at': datetime.now(),
                'priority': 'high'
            })
        
        return jsonify({'success': True, 'message': f'Donation {new_status}'}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@donations_bp.route('/donations/hospital-notifications/<hospital_id>', methods=['GET'])
def get_hospital_notifications(hospital_id):
    """Get notifications for a hospital"""
    try:
        db = get_db()
        notifications = list(db.hospital_notifications.find(
            {'hospital_id': hospital_id},
            {'_id': 0}
        ).sort('created_at', -1).limit(50))
        
        unread_count = db.hospital_notifications.count_documents({
            'hospital_id': hospital_id,
            'is_read': False
        })
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'unread_count': unread_count
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@donations_bp.route('/donations/hospital-notifications/mark-read', methods=['POST'])
def mark_hospital_notification_read():
    """Mark hospital notification as read"""
    try:
        data = request.json
        db = get_db()
        
        hospital_id = data.get('hospital_id')
        notification_id = data.get('notification_id')
        
        query = {'hospital_id': hospital_id, 'is_read': False}
        if notification_id:
            query['notification_id'] = notification_id
        
        result = db.hospital_notifications.update_many(
            query,
            {'$set': {'is_read': True, 'read_at': datetime.now()}}
        )
        
        return jsonify({'success': True, 'modified_count': result.modified_count}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500