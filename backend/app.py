import os
from datetime import date
from flask import Flask, send_from_directory, jsonify, session, redirect, url_for, request
from backend.config import Config
from backend.database import execute_query, get_system_settings
from backend.routes.auth import auth_bp, login_required
from backend.routes.books import books_bp
from backend.routes.members import members_bp
from backend.routes.loans import loans_bp
from backend.routes.fines import fines_bp

# Resolve paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

app = Flask(__name__, static_folder=None)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['JSON_AS_ASCII'] = False

# Register API blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(books_bp, url_prefix='/api/books')
app.register_blueprint(members_bp, url_prefix='/api/members')
app.register_blueprint(loans_bp, url_prefix='/api/loans')
app.register_blueprint(fines_bp, url_prefix='/api/fines')

# -------------------------------------------------------------
# System Settings & Dashboard Statistics APIs
# -------------------------------------------------------------
@app.route('/api/settings', methods=['GET'])
def get_settings_route():
    """Return system business settings (fine per day, loan duration, max renewals)."""
    return jsonify({'settings': get_system_settings()})

@app.route('/api/settings', methods=['PUT'])
@login_required(role='admin')
def update_settings_route():
    """Update system business settings (Admin only)."""
    data = request.get_json() or {}
    try:
        fine_per_day = float(data.get('fine_per_day', 5.0))
        loan_days = int(data.get('loan_days', 14))
        max_renewals = int(data.get('max_renewals', 2))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid settings values provided.'}), 400

    query = "UPDATE settings SET fine_per_day = %s, loan_days = %s, max_renewals = %s WHERE setting_id = 1"
    _, err = execute_query(query, (fine_per_day, loan_days, max_renewals), commit=True)
    if err:
        return jsonify({'error': 'Failed to update settings.'}), 500

    return jsonify({'success': True, 'message': 'System settings updated successfully.'})

@app.route('/api/admin/dashboard-stats', methods=['GET'])
@login_required(role='admin')
def admin_dashboard_stats():
    """
    Return statistics for Admin dashboard:
    - total books
    - total members
    - total issued books
    - total overdue books
    - total pending fines
    """
    total_books_res, _ = execute_query("SELECT COALESCE(SUM(quantity), 0) AS total_copies, COUNT(*) AS total_titles FROM books", fetch_one=True)
    total_members_res, _ = execute_query("SELECT COUNT(*) AS total FROM members", fetch_one=True)
    total_issued_res, _ = execute_query("SELECT COUNT(*) AS total FROM loans WHERE status = 'Issued'", fetch_one=True)
    total_overdue_res, _ = execute_query("SELECT COUNT(*) AS total FROM loans WHERE status = 'Issued' AND due_date < CURDATE()", fetch_one=True)
    
    # Calculate pending fines
    unpaid_res, _ = execute_query("SELECT COALESCE(SUM(fine_amount), 0) AS total FROM loans WHERE fine_paid = FALSE", fetch_one=True)

    return jsonify({
        'total_books': total_books_res['total_titles'] if total_books_res else 0,
        'total_copies': total_books_res['total_copies'] if total_books_res else 0,
        'total_members': total_members_res['total'] if total_members_res else 0,
        'total_issued': total_issued_res['total'] if total_issued_res else 0,
        'total_overdue': total_overdue_res['total'] if total_overdue_res else 0,
        'total_unpaid_fines': float(unpaid_res['total']) if unpaid_res else 0.0
    })

@app.route('/api/member/dashboard-stats', methods=['GET'])
@login_required(role='member')
def member_dashboard_stats():
    """
    Return statistics for Member dashboard:
    - active borrowed count
    - overdue count
    - total unpaid fine
    - total books read (returned)
    """
    member_id = session.get('user_id')
    settings = get_system_settings()
    fine_per_day = settings.get('fine_per_day', 5.0)

    active_res, _ = execute_query("SELECT COUNT(*) AS total FROM loans WHERE member_id = %s AND status = 'Issued'", (member_id,), fetch_one=True)
    overdue_res, _ = execute_query("SELECT COUNT(*) AS total FROM loans WHERE member_id = %s AND status = 'Issued' AND due_date < CURDATE()", (member_id,), fetch_one=True)
    history_res, _ = execute_query("SELECT COUNT(*) AS total FROM loans WHERE member_id = %s AND status = 'Returned'", (member_id,), fetch_one=True)

    # Calculate active fines + returned unpaid fines
    all_loans, _ = execute_query("SELECT due_date, return_date, fine_amount, fine_paid, status FROM loans WHERE member_id = %s", (member_id,), fetch_all=True)
    today = date.today()
    unpaid_fine = 0.0

    for l in all_loans or []:
        due = l['due_date']
        if hasattr(due, 'date'):
            due = due.date()
        fine = float(l['fine_amount'])
        if l['status'] == 'Issued' and today > due:
            accrued = round((today - due).days * fine_per_day, 2)
            fine = max(fine, accrued)
            unpaid_fine += fine
        elif l['status'] == 'Returned' and not l['fine_paid']:
            unpaid_fine += fine

    return jsonify({
        'active_borrowed': active_res['total'] if active_res else 0,
        'overdue_count': overdue_res['total'] if overdue_res else 0,
        'books_read': history_res['total'] if history_res else 0,
        'unpaid_fines': round(unpaid_fine, 2),
        'settings': settings
    })

# -------------------------------------------------------------
# Frontend Static Files & Pages Serving
# -------------------------------------------------------------
@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), filename)

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/login')
def login_page():
    return send_from_directory(FRONTEND_DIR, 'login.html')

@app.route('/register')
def register_page():
    return send_from_directory(FRONTEND_DIR, 'register.html')

# Member pages (with server-side protection against unauthorized roles)
@app.route('/member/<page>')
def member_pages(page):
    if not page.endswith('.html'):
        page = f"{page}.html"
    
    # Check session: block non-members or unauthenticated visitors
    if 'user_id' not in session or session.get('role') != 'member':
        return redirect('/login?msg=Please login as a member to access this page.')

    target_file = os.path.join(FRONTEND_DIR, 'member', page)
    if os.path.isfile(target_file):
        return send_from_directory(os.path.join(FRONTEND_DIR, 'member'), page)
    return "Page not found", 404

# Admin pages (with server-side protection against unauthorized roles)
@app.route('/admin/<page>')
def admin_pages(page):
    if not page.endswith('.html'):
        page = f"{page}.html"

    # Check session: block non-admins or unauthenticated visitors
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login?msg=Access denied: Administrator login required.')

    target_file = os.path.join(FRONTEND_DIR, 'admin', page)
    if os.path.isfile(target_file):
        return send_from_directory(os.path.join(FRONTEND_DIR, 'admin'), page)
    return "Page not found", 404

# Fallback 404 handler
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'API endpoint not found.'}), 404
    return redirect('/')

# -------------------------------------------------------------
# Main Entry Point
# -------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("  College Library Management System Backend Starting")
    print(f"  Port: {Config.FLASK_PORT} | Debug: {Config.FLASK_DEBUG}")
    print(f"  Access URL: http://localhost:{Config.FLASK_PORT}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
