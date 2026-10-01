from datetime import date
from flask import Blueprint, request, jsonify, session
from backend.database import execute_query, get_system_settings
from backend.routes.auth import login_required
fines_bp = Blueprint('fines', __name__)

@fines_bp.route('/member', methods=['GET'])
@login_required(role='member')
def get_member_fines():
    """
    Get all fine details for the logged-in member.
    Includes both returned loans with unpaid/paid fines and active overdue loans with accrued fines.
    Accurately reflects fine_paid status from the database.
    """
    member_id = session.get('user_id')
    settings = get_system_settings()
    fine_per_day = settings.get('fine_per_day', 5.0)

    query = """
        SELECT l.*, b.title, b.isbn
        FROM loans l
        JOIN books b ON l.book_id = b.book_id
        WHERE l.member_id = %s
        ORDER BY l.loan_id DESC
    """
    loans, _ = execute_query(query, (member_id,), fetch_all=True)

    today = date.today()
    fines_list = []
    total_unpaid = 0.0
    total_paid = 0.0

    for l in loans or []:
        due = l['due_date']
        if hasattr(due, 'date'):
            due = due.date()

        fine = float(l['fine_amount'])
        is_paid = bool(l['fine_paid'])

        # If active loan is overdue and fine_amount not recorded yet
        if l['status'] == 'Issued' and today > due:
            overdue_days = (today - due).days
            accrued = round(overdue_days * fine_per_day, 2)
            fine = max(fine, accrued)

        if fine > 0:
            if is_paid:
                total_paid += fine
            else:
                total_unpaid += fine

            fines_list.append({
                'loan_id': l['loan_id'],
                'book_title': l['title'],
                'isbn': l['isbn'],
                'issue_date': str(l['issue_date']),
                'due_date': str(due),
                'return_date': str(l['return_date']) if l['return_date'] else 'Not Returned',
                'fine_amount': fine,
                'fine_paid': is_paid,
                'status': l['status']
            })

    return jsonify({
        'fines': fines_list,
        'total_unpaid': round(total_unpaid, 2),
        'total_paid': round(total_paid, 2),
        'fine_per_day': fine_per_day
    })

@fines_bp.route('/all', methods=['GET'])
@login_required(role='admin')
def get_all_fines():
    """
    Get all fine records across the library (Admin only).
    Accurately reflects fine_paid status from the database.
    """
    query = """
        SELECT l.loan_id, l.fine_amount, l.fine_paid, l.status, l.issue_date, l.due_date, l.return_date,
               m.member_id, m.name AS member_name, m.username AS member_username,
               b.book_id, b.title AS book_title
        FROM loans l
        JOIN members m ON l.member_id = m.member_id
        JOIN books b ON l.book_id = b.book_id
        WHERE l.fine_amount > 0 OR (l.status = 'Issued' AND l.due_date < CURDATE())
        ORDER BY l.loan_id DESC
    """
    rows, _ = execute_query(query, fetch_all=True)

    today = date.today()
    settings = get_system_settings()
    fine_per_day = settings.get('fine_per_day', 5.0)

    fines = []
    total_unpaid = 0.0
    total_collected = 0.0

    for r in rows or []:
        due = r['due_date']
        if hasattr(due, 'date'):
            due = due.date()

        fine = float(r['fine_amount'])
        is_paid = bool(r['fine_paid'])

        if r['status'] == 'Issued' and today > due:
            overdue_days = (today - due).days
            accrued = round(overdue_days * fine_per_day, 2)
            fine = max(fine, accrued)

        if is_paid:
            total_collected += fine
        else:
            total_unpaid += fine

        fines.append({
            'loan_id': r['loan_id'],
            'member_id': r['member_id'],
            'member_name': r['member_name'],
            'member_username': r['member_username'],
            'book_title': r['book_title'],
            'issue_date': str(r['issue_date']),
            'due_date': str(due),
            'return_date': str(r['return_date']) if r['return_date'] else 'Not Returned',
            'fine_amount': fine,
            'fine_paid': is_paid,
            'status': r['status']
        })

    return jsonify({
        'fines': fines,
        'total_unpaid': round(total_unpaid, 2),
        'total_collected': round(total_collected, 2)
    })

@fines_bp.route('/pay/<int:loan_id>', methods=['POST'])
@login_required(role='admin')
def mark_fine_as_paid(loan_id):
    """
    Mark an overdue or returned loan fine as paid (Admin only).
    Updates fine_paid = TRUE and records fine_amount in database.
    """
    query = "SELECT loan_id, fine_amount, fine_paid, status, due_date FROM loans WHERE loan_id = %s LIMIT 1"
    loan, _ = execute_query(query, (loan_id,), fetch_one=True)
    if not loan:
        return jsonify({'error': 'Loan record not found.'}), 404

    # Calculate and store the actual fine if it was an active overdue loan
    settings = get_system_settings()
    fine_per_day = settings.get('fine_per_day', 5.0)
    today = date.today()
    due = loan['due_date']
    if hasattr(due, 'date'):
        due = due.date()

    fine_amount = float(loan['fine_amount'])
    if fine_amount == 0.0 and loan['status'] == 'Issued' and today > due:
        fine_amount = round((today - due).days * fine_per_day, 2)

    update_query = "UPDATE loans SET fine_paid = TRUE, fine_amount = %s WHERE loan_id = %s"
    _, err = execute_query(update_query, (fine_amount, loan_id), commit=True)
    if err:
        return jsonify({'error': 'Failed to update fine status.'}), 500

    return jsonify({'success': True, 'message': 'Fine marked as paid successfully.'})
