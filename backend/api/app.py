"""
Main Flask application with all routes and WebSocket support.
"""
from flask import Flask, jsonify
from flask_cors import CORS
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import blueprints
from api.auth import auth_bp
from api.users import users_bp
from api.jobs import jobs_bp
from api.notifications import notifications_bp

# Import WebSocket
from api.websocket import socketio

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Configure app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JSON_SORT_KEYS'] = False

# Initialize SocketIO with app
socketio.init_app(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(jobs_bp)
app.register_blueprint(notifications_bp)


@app.route('/')
def index():
    """API root endpoint."""
    return jsonify({
        'name': 'Print Job Manager API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'auth': '/api/auth',
            'users': '/api/users',
            'jobs': '/api/jobs',
            'scanner': '/api/scan (coming soon)'
        },
        'websocket': 'Socket.IO enabled'
    })


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'print-job-manager-api',
        'websocket': 'enabled'
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Development server
    print("🚀 Starting Print Job Manager API...")
    print("📍 HTTP: http://localhost:5000")
    print("📡 WebSocket: ws://localhost:5000")
    print("⚠️  Default admin credentials: admin / admin123")
    print()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
