"""
WebSocket events for real-time job updates and notifications.
"""
from flask_socketio import SocketIO, emit, join_room, leave_room
from functools import wraps
import logging

# Initialize SocketIO
socketio = SocketIO(cors_allowed_origins="*")

logger = logging.getLogger(__name__)


def authenticated_only(f):
    """Decorator to require authentication for Socket.IO events."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        # In production, verify JWT token from handshake
        # For now, allow all connections
        return f(*args, **kwargs)
    return wrapped


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected")
    emit('connected', {'message': 'Connected to Print Job Manager'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected")


@socketio.on('join_notifications')
@authenticated_only
def handle_join_notifications(data):
    """Join notifications room for real-time updates."""
    user_id = data.get('user_id')
    if user_id:
        room = f"user_{user_id}"
        join_room(room)
        emit('joined', {'room': room})
        logger.info(f"User {user_id} joined notifications")


@socketio.on('leave_notifications')
@authenticated_only
def handle_leave_notifications(data):
    """Leave notifications room."""
    user_id = data.get('user_id')
    if user_id:
        room = f"user_{user_id}"
        leave_room(room)
        emit('left', {'room': room})
        logger.info(f"User {user_id} left notifications")


def broadcast_job_update(job_id, action, job_data=None):
    """
    Broadcast job update to all connected clients.
    
    Args:
        job_id: Job ID
        action: 'created', 'updated', 'completed', 'deleted'
        job_data: Optional job details
    """
    socketio.emit('job:updated', {
        'job_id': job_id,
        'action': action,
        'job': job_data,
        'timestamp': str(__import__('datetime').datetime.utcnow())
    })
    logger.info(f"Broadcast job update: {job_id} - {action}")


def broadcast_stats_update(stats):
    """
    Broadcast statistics update to all clients.
    
    Args:
        stats: Statistics dict with total, pending, acknowledged, completed
    """
    socketio.emit('stats:update', {
        'stats': stats,
        'timestamp': str(__import__('datetime').datetime.utcnow())
    })
    logger.info(f"Broadcast stats update: {stats}")


def send_notification(user_id, notification_type, message, data=None):
    """
    Send notification to specific user.
    
    Args:
        user_id: Target user ID
        notification_type: Type of notification (info, success, warning, error)
        message: Notification message
        data: Optional additional data
    """
    room = f"user_{user_id}"
    socketio.emit('notification', {
        'type': notification_type,
        'message': message,
        'data': data,
        'timestamp': str(__import__('datetime').datetime.utcnow())
    }, room=room)
    logger.info(f"Sent notification to user {user_id}: {message}")


def broadcast_new_job(job_data):
    """
    Broadcast new job alert to all staff/managers.
    
    Args:
        job_data: New job details
    """
    socketio.emit('job:new', {
        'job': job_data,
        'timestamp': str(__import__('datetime').datetime.utcnow())
    })
    logger.info(f"Broadcast new job: {job_data.get('job_id')}")
