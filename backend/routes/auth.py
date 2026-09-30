from functools import wraps
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import execute_query

auth_bp = Blueprint('auth', __name__)

def login_required(role=None):
    """
    Decorator to protect routes requiring authentication.
    If role is specified ('admin' or 'member'), verifies the session matches.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or 'role' not in session:
                return jsonify({'error': 'Please login to continue.'}), 401
            
            if role and session.get('role') != role:
                return jsonify({'error': 'Access forbidden: Insufficient permissions.'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Handle new member registration.
    Validates fields, checks unique username and email,
    hashes password with werkzeug.security, and inserts member into MySQL.
    """
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()

    # Validate required fields
    if not all([name, email, phone, username, password]):
        return jsonify({'error': 'Please fill in all fields.'}), 400

    if confirm_password and password != confirm_password:
        return jsonify({'error': 'Passwords do not match.'}), 400

    # Basic length checks
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters.'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400

    # Check for duplicate username or email
    check_query = "SELECT member_id, username, email FROM members WHERE username = %s OR email = %s LIMIT 1"
    existing, err = execute_query(check_query, (username, email), fetch_one=True)
    if err:
        return jsonify({'error': 'Database error while checking account details.'}), 500

    if existing:
        if existing['username'].lower() == username.lower():
            return jsonify({'error': 'Username is already taken. Please choose another.'}), 400
        else:
            return jsonify({'error': 'Email is already registered. Please login or use another email.'}), 400

    # Hash password safely
    password_hash = generate_password_hash(password)

    insert_query = """
        INSERT INTO members (name, email, phone, username, password_hash)
        VALUES (%s, %s, %s, %s, %s)
    """
    res, err = execute_query(insert_query, (name, email, phone, username, password_hash), commit=True)
    if err:
        return jsonify({'error': 'Failed to complete registration. Please try again.'}), 500

    return jsonify({'success': True, 'message': 'Registration successful! You can now login.'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate a member or admin and create a Flask session.
    Strictly verifies credentials against the selected role.
    """
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'member').strip().lower()

    if not username or not password:
        return jsonify({'error': 'Please fill in all fields.'}), 400

    if role not in ('member', 'admin'):
        return jsonify({'error': 'Invalid role specified.'}), 400

    # Query strictly the table for the chosen role
    if role == 'admin':
        query = "SELECT admin_id AS id, name, username, password_hash FROM admins WHERE username = %s LIMIT 1"
    else:
        query = "SELECT member_id AS id, name, username, password_hash FROM members WHERE username = %s LIMIT 1"

    user, err = execute_query(query, (username,), fetch_one=True)

    if err:
        return jsonify({'error': 'Database connection error. Please try again.'}), 500

    # Verify user exists for this role and password matches hash
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid username or password.'}), 401

    # Store user identity in Flask session
    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['name'] = user['name']
    session['role'] = role

    return jsonify({
        'success': True,
        'message': f'Welcome back, {user["name"]}!',
        'role': role,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'name': user['name'],
            'role': role
        }
    })

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Clear session and log user out.
    """
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully.'})

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """
    Return currently logged-in user details from session.
    """
    if 'user_id' in session and 'role' in session:
        return jsonify({
            'logged_in': True,
            'user': {
                'id': session['user_id'],
                'username': session['username'],
                'name': session['name'],
                'role': session['role']
            }
        })
    return jsonify({'logged_in': False, 'user': None})
