from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash
from backend.database import execute_query
from backend.routes.auth import login_required

members_bp = Blueprint('members', __name__)

@members_bp.route('', methods=['GET'])
@login_required(role='admin')
def get_all_members():
    """
    Get all members with active loan count and pending fine summaries (Admin only).
    """
    search = request.args.get('search', '').strip()
    
    query = """
        SELECT 
            m.member_id,
            m.name,
            m.email,
            m.phone,
            m.username,
            m.registration_date,
            COUNT(DISTINCT CASE WHEN l.status = 'Issued' THEN l.loan_id END) AS active_loans_count,
            COALESCE(SUM(CASE WHEN l.fine_paid = FALSE THEN l.fine_amount ELSE 0 END), 0) AS unpaid_fines
        FROM members m
        LEFT JOIN loans l ON m.member_id = l.member_id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (m.name LIKE %s OR m.username LIKE %s OR m.email LIKE %s OR m.phone LIKE %s)"
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, pattern])

    query += " GROUP BY m.member_id ORDER BY m.registration_date DESC"

    members, err = execute_query(query, tuple(params), fetch_all=True)
    if err:
        return jsonify({'error': 'Failed to retrieve members.'}), 500

    # Ensure float conversion for fines
    for m in members or []:
        m['unpaid_fines'] = float(m['unpaid_fines'])

    return jsonify({'members': members or []})

@members_bp.route('/profile', methods=['GET'])
@login_required(role='member')
def get_member_profile():
    """
    Get profile information for the currently logged-in member.
    """
    member_id = session.get('user_id')
    query = "SELECT member_id, name, email, phone, username, registration_date FROM members WHERE member_id = %s LIMIT 1"
    member, err = execute_query(query, (member_id,), fetch_one=True)
    if not member:
        return jsonify({'error': 'Member not found.'}), 404

    return jsonify({'member': member})

@members_bp.route('/<int:member_id>', methods=['GET'])
@login_required(role='admin')
def get_member_details(member_id):
    """
    Get member details and their current loans and loan history (Admin only).
    """
    member_query = "SELECT member_id, name, email, phone, username, registration_date FROM members WHERE member_id = %s LIMIT 1"
    member, err = execute_query(member_query, (member_id,), fetch_one=True)
    if not member:
        return jsonify({'error': 'Member not found.'}), 404

    loans_query = """
        SELECT l.*, b.title, b.author, b.isbn
        FROM loans l
        JOIN books b ON l.book_id = b.book_id
        WHERE l.member_id = %s
        ORDER BY l.issue_date DESC
    """
    loans, _ = execute_query(loans_query, (member_id,), fetch_all=True)

    return jsonify({
        'member': member,
        'loans': loans or []
    })

@members_bp.route('', methods=['POST'])
@login_required(role='admin')
def add_member_by_admin():
    """
    Add a new member manually (Admin only).
    """
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not all([name, email, phone, username, password]):
        return jsonify({'error': 'Please fill in all fields.'}), 400

    check_query = "SELECT member_id FROM members WHERE username = %s OR email = %s LIMIT 1"
    existing, _ = execute_query(check_query, (username, email), fetch_one=True)
    if existing:
        return jsonify({'error': 'Duplicate username or email.'}), 400

    password_hash = generate_password_hash(password)
    insert_query = """
        INSERT INTO members (name, email, phone, username, password_hash)
        VALUES (%s, %s, %s, %s, %s)
    """
    _, err = execute_query(insert_query, (name, email, phone, username, password_hash), commit=True)
    if err:
        return jsonify({'error': 'Failed to add member.'}), 500

    return jsonify({'success': True, 'message': 'Member added successfully.'}), 201

@members_bp.route('/<int:member_id>', methods=['PUT'])
@login_required(role='admin')
def update_member(member_id):
    """
    Update member details (Admin only).
    """
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()

    if not all([name, email, phone]):
        return jsonify({'error': 'Please fill in all fields.'}), 400

    # Check email duplicate with another member
    check_query = "SELECT member_id FROM members WHERE email = %s AND member_id != %s LIMIT 1"
    existing, _ = execute_query(check_query, (email, member_id), fetch_one=True)
    if existing:
        return jsonify({'error': 'Another member is already using this email address.'}), 400

    update_query = "UPDATE members SET name = %s, email = %s, phone = %s WHERE member_id = %s"
    _, err = execute_query(update_query, (name, email, phone, member_id), commit=True)
    if err:
        return jsonify({'error': 'Failed to update member.'}), 500

    return jsonify({'success': True, 'message': 'Member updated successfully.'})

@members_bp.route('/<int:member_id>', methods=['DELETE'])
@login_required(role='admin')
def delete_member(member_id):
    """
    Delete a member (Admin only).
    Prevent deleting a member who has active loans.
    """
    # Check active loans
    check_active = "SELECT COUNT(*) AS count FROM loans WHERE member_id = %s AND status = 'Issued'"
    res, _ = execute_query(check_active, (member_id,), fetch_one=True)
    if res and res['count'] > 0:
        return jsonify({'error': 'Cannot delete member: Member has active borrowed books.'}), 400

    # Clean returned loan history for this member so foreign key constraint passes
    execute_query("DELETE FROM loans WHERE member_id = %s AND status = 'Returned'", (member_id,), commit=True)

    delete_query = "DELETE FROM members WHERE member_id = %s"
    _, err = execute_query(delete_query, (member_id,), commit=True)
    if err:
        return jsonify({'error': 'Failed to delete member.'}), 500

    return jsonify({'success': True, 'message': 'Member deleted successfully.'})
