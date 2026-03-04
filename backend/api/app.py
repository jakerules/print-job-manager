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

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Configure app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JSON_SORT_KEYS'] = False

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)


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
            'jobs': '/api/jobs (coming soon)',
            'scanner': '/api/scan (coming soon)'
        }
    })


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'print-job-manager-api'
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
    print("📍 Running on http://localhost:5000")
    print("⚠️  Default admin credentials: admin / admin123")
    print()
    app.run(host='0.0.0.0', port=5000, debug=True)
