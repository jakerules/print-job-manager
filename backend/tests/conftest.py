"""
Shared test fixtures for the backend test suite.
"""
import os
import sys
import tempfile
import pytest

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    import database.db_config as db_config
    original_path = db_config.DB_PATH
    db_config.DB_PATH = tmp_path / 'test_users.db'
    db_config.init_db()
    yield db_config.DB_PATH
    db_config.DB_PATH = original_path


@pytest.fixture
def user_repo(temp_db):
    """Get a UserRepository with a fresh temp database."""
    from api.user_repository import UserRepository
    return UserRepository()


@pytest.fixture
def admin_user(user_repo):
    """Create and return an admin user."""
    from api.models import User
    user = User(username='testadmin', email='admin@test.com', role='admin')
    user.set_password('password123')
    return user_repo.create(user)


@pytest.fixture
def staff_user(user_repo):
    """Create and return a staff user."""
    from api.models import User
    user = User(username='teststaff', email='staff@test.com', role='staff')
    user.set_password('password123')
    return user_repo.create(user)


@pytest.fixture
def submitter_user(user_repo):
    """Create and return a submitter user."""
    from api.models import User
    user = User(username='testsubmitter', email='submitter@test.com', role='submitter')
    user.set_password('password123')
    return user_repo.create(user)


@pytest.fixture
def app(temp_db):
    """Create a Flask test app with jobs blueprint mocked out."""
    from flask import Flask
    from flask_cors import CORS
    from api.auth import auth_bp
    from api.users import users_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    CORS(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)

    return app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def admin_token(client, admin_user):
    """Get a valid JWT token for admin user."""
    resp = client.post('/api/auth/login', json={
        'username': 'testadmin',
        'password': 'password123'
    })
    return resp.get_json()['access_token']


@pytest.fixture
def staff_token(client, staff_user):
    """Get a valid JWT token for staff user."""
    resp = client.post('/api/auth/login', json={
        'username': 'teststaff',
        'password': 'password123'
    })
    return resp.get_json()['access_token']


@pytest.fixture
def submitter_token(client, submitter_user):
    """Get a valid JWT token for submitter user."""
    resp = client.post('/api/auth/login', json={
        'username': 'testsubmitter',
        'password': 'password123'
    })
    return resp.get_json()['access_token']
