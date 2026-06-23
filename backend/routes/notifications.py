from flask import Blueprint, jsonify, request
from database.db import get_db
from datetime import datetime
import uuid

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api')

@notifications_bp.route('/notifications/<user_id>', methods=['GET'])
def get_notifications(user_id):
    """Get all notifications for a user"""
    try:
        db = get_db()
        limit = request.args.get('limit', 50, type=int)
        
        print(f"🔔 Fetching notifications for user: {user_id}")  # Debug
        
        notifications = list(db.notifications.find(
            {'user_id': user_id}
        ).sort('created_at', -1).limit(limit))
        
        # Convert for JSON response
        formatted_notifications = []
        for notif in notifications:
            formatted_notif = {
                'notification_id': notif.get('notification_id', str(notif['_id'])),
                'title': notif.get('title', ''),
                'message': notif.get('message', ''),
                'type': notif.get('type', 'info'),
                'is_read': notif.get('is_read', False),
                'created_at': notif['created_at'].isoformat() if notif.get('created_at') else None,
                'priority': notif.get('priority', 'medium')
            }
            formatted_notifications.append(formatted_notif)
        
        unread_count = db.notifications.count_documents({
            'user_id': user_id,
            'is_read': False
        })
        
        print(f"✅ Found {len(formatted_notifications)} notifications, {unread_count} unread")
        
        return jsonify({
            'success': True,
            'notifications': formatted_notifications,
            'unread_count': unread_count
        }), 200
        
    except Exception as e:
        print(f"❌ Error in get_notifications: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e),
            'notifications': [],
            'unread_count': 0
        }), 500


@notifications_bp.route('/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    """Mark notifications as read"""
    try:
        data = request.json or {}
        db = get_db()
        
        user_id = data.get('user_id') or data.get('userId')
        notification_id = data.get('notification_id') or data.get('notificationId')
        
        print(f"📖 Marking notifications as read for user: {user_id}")  # Debug
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User ID required'
            }), 400
        
        # Build query
        query = {'user_id': user_id, 'is_read': False}
        if notification_id:
            query['notification_id'] = notification_id
        
        # Mark as read
        result = db.notifications.update_many(
            query,
            {'$set': {'is_read': True, 'read_at': datetime.now()}}
        )
        
        print(f"✅ Marked {result.modified_count} notifications as read")
        
        return jsonify({
            'success': True,
            'message': f'{result.modified_count} notification(s) marked as read',
            'modified_count': result.modified_count
        }), 200
        
    except Exception as e:
        print(f"❌ Error in mark_notifications_read: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@notifications_bp.route('/notifications/create', methods=['POST'])
def create_notification():
    """Create a new notification"""
    try:
        data = request.json
        db = get_db()
        
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        notification = {
            'notification_id': str(uuid.uuid4()),
            'user_id': user_id,
            'title': data.get('title', 'Notification'),
            'message': data.get('message', ''),
            'type': data.get('type', 'info'),
            'is_read': False,
            'created_at': datetime.now(),
            'priority': data.get('priority', 'medium'),
            'metadata': data.get('metadata', {})
        }
        
        db.notifications.insert_one(notification)
        
        print(f"✅ Created notification for user {user_id}: {notification['title']}")
        
        return jsonify({
            'success': True,
            'message': 'Notification created',
            'notification_id': notification['notification_id']
        }), 201
        
    except Exception as e:
        print(f"❌ Error creating notification: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500