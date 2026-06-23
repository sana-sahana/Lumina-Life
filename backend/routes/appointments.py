from flask import Blueprint, jsonify, request
from database.db import get_db
from datetime import datetime
import uuid
appointments_bp = Blueprint('appointments', __name__, url_prefix='/api')
@appointments_bp.route('/book-appointment', methods=['POST'])
def book_appointment():
    """Book a new appointment"""
    try:
        data = request.json or {}
        db = get_db()
        
        user_id = data.get('userId') or data.get('user_id')
        hospital = data.get('hospital') or data.get('hospital_name')
        date_str = data.get('date')
        time_str = data.get('time')
        
        # Validations
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required'}), 400
        if not hospital:
            return jsonify({'success': False, 'message': 'Hospital is required'}), 400
        if not date_str:
            return jsonify({'success': False, 'message': 'Date is required'}), 400
        if not time_str:
            return jsonify({'success': False, 'message': 'Time is required'}), 400
            
        try:
            # Check date format
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
            
        appointment = {
            'appointment_id': str(uuid.uuid4()),
            'user_id': user_id,
            'hospital_id': data.get('hospital_id') or 1,
            'hospital_name': hospital,
            'date': date_str,
            'time': time_str,
            'status': 'Booked',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'notes': data.get('notes', '')
        }
        
        db.appointments.insert_one(appointment)
        
        # Create notification for the donor
        notification = {
            'notification_id': str(uuid.uuid4()),
            'user_id': user_id,
            'title': 'Appointment Confirmed',
            'message': f"Your donation appointment at {hospital} on {date_str} at {time_str} has been confirmed.",
            'type': 'success',
            'is_read': False,
            'created_at': datetime.now(),
            'priority': 'medium'
        }
        db.notifications.insert_one(notification)
        
        return jsonify({
            'success': True,
            'message': 'Appointment booked successfully',
            'appointment': appointment
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
@appointments_bp.route('/appointments/<user_id>', methods=['GET'])
def get_appointments(user_id):
    """Get all appointments for a user"""
    try:
        db = get_db()
        
        appointments = list(db.appointments.find(
            {'user_id': user_id}
        ).sort('date', -1))
        
        # Convert ObjectId to string and format dates
        for apt in appointments:
            apt['_id'] = str(apt['_id'])
            apt['created_at'] = apt['created_at'].isoformat() if apt.get('created_at') else None
            apt['updated_at'] = apt['updated_at'].isoformat() if apt.get('updated_at') else None
        
        return jsonify(appointments), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
@appointments_bp.route('/appointments/cancel/<appointment_id>', methods=['PUT'])
def cancel_appointment(appointment_id):
    """Cancel an appointment"""
    try:
        db = get_db()
        
        result = db.appointments.update_one(
            {'appointment_id': appointment_id},
            {
                '$set': {
                    'status': 'Cancelled',
                    'updated_at': datetime.now()
                }
            }
        )
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Appointment cancelled'}), 200
        else:
            return jsonify({'success': False, 'message': 'Appointment not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
        