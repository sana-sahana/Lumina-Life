from flask import Blueprint, jsonify, request
from database.db import get_db
from datetime import datetime, timedelta
tracker_bp = Blueprint('tracker', __name__, url_prefix='/api')
@tracker_bp.route('/tracker/<user_id>', methods=['GET'])
def get_donation_tracker(user_id):
    """Get donation tracking information"""
    try:
        db = get_db()
        
        # Check tracker collection first
        tracker_data = db.tracker.find_one({'user_id': user_id})
        
        # Fallback/Calculate if not cached in tracker collection
        if not tracker_data:
            profile = db.user_profiles.find_one({'user_id': user_id})
            if not profile:
                return jsonify({'error': 'User profile not found'}), 404
                
            total_donations = profile.get('total_donations', 0)
            last_donation = profile.get('last_donation_date')
            lives_saved = profile.get('lives_saved', 0)
            
            # Calculate next eligible date (90 days after last donation)
            next_eligible_date = None
            if last_donation:
                next_eligible_date = last_donation + timedelta(days=90)
            else:
                next_eligible_date = datetime.now()
                
            # Count donations this year
            current_year = datetime.now().year
            donation_history = list(db.donation_history.find({
                'user_id': user_id,
                'donation_date': {
                    '$gte': datetime(current_year, 1, 1),
                    '$lte': datetime(current_year, 12, 31)
                }
            }))
            donations_this_year = len(donation_history)
            
            # Cache it in tracker collection
            tracker_doc = {
                'user_id': user_id,
                'total_donations': total_donations,
                'last_donation_date': last_donation,
                'next_eligible_date': next_eligible_date,
                'donations_this_year': donations_this_year,
                'lives_saved': lives_saved,
                'updated_at': datetime.now()
            }
            db.tracker.update_one({'user_id': user_id}, {'$set': tracker_doc}, upsert=True)
            tracker_data = tracker_doc
            
        # Format the response fields
        total_donations = tracker_data.get('total_donations', 0)
        last_donation = tracker_data.get('last_donation_date')
        next_eligible = tracker_data.get('next_eligible_date')
        donations_this_year = tracker_data.get('donations_this_year', total_donations)
        lives_saved = tracker_data.get('lives_saved', 0)
        
        return jsonify({
            'totalDonations': total_donations,
            'lastDonation': last_donation.isoformat() if last_donation else None,
            'nextEligible': next_eligible.isoformat() if next_eligible else None,
            'donationsThisYear': donations_this_year,
            'livesSaved': lives_saved
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@tracker_bp.route('/history/<user_id>', methods=['GET'])
def get_donation_history(user_id):
    """Get donation history records"""
    try:
        db = get_db()
        
        history = list(db.donation_history.find(
            {'user_id': user_id}
        ).sort('donation_date', -1).limit(20))
        
        # Format the data
        formatted_history = []
        for record in history:
            formatted_history.append({
                'donation_id': record.get('donation_id'),
                'hospital_name': record.get('hospital_name', 'Unknown Hospital'),
                'donation_date': record['donation_date'].isoformat() if record.get('donation_date') else None,
                'blood_type': record.get('blood_type', 'O+'),
                'units_donated': record.get('units_donated', 1),
                'status': record.get('status', 'Completed')
            })
        
        return jsonify({
            'success': True,
            'history': formatted_history
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
        