from datetime import date, timedelta
from flask import Blueprint, request, jsonify, session
from database import execute_query, get_system_settings
from routes.auth import login_required

loans_bp = Blueprint('loans', __name__)

@loans_bp.route('/issue', methods=['POST'])
@login_required()
def issue_book():
    """
    Issue/borrow a book.
    Admins can issue a book to any member (specifying member_id or username).
    Members can borrow a book for themselves.
    Enforces business rules:
      - Member exists
      - Book exists and has available_quantity > 0
      - Prevent borrowing the same book twice at once
      - Read loan_days from settings table
      - Decrement available_quantity and sync status
    """
    data = request.get_json() or {}
    book_id = data.get('book_id')
    user_role = session.get('role')

    if not book_id:
        return jsonify({'error': 'Please select a book to issue.'}), 400

    # Determine member_id
    if user_role == 'admin':
        member_id = data.get('member_id')
        member_username = data.get('member_username', '').strip()

        if not member_id and not member_username:
            return jsonify({'error': 'Please provide member ID or username.'}), 400

        if member_username:
            m_res, _ = execute_query("SELECT member_id FROM members WHERE username = %s LIMIT 1", (member_username,), fetch_one=True)
            if not m_res:
                return jsonify({'error': 'Member not found.'}), 404
            member_id = m_res['member_id']
    else:
        # Member borrowing for themselves
        member_id = session.get('user_id')

    # 1. Verify member exists
    member, _ = execute_query("SELECT member_id, name FROM members WHERE member_id = %s LIMIT 1", (member_id,), fetch_one=True)
    if not member:
        return jsonify({'error': 'Member not found.'}), 404

    # 2. Verify book exists and check availability
    book, _ = execute_query("SELECT book_id, title, available_quantity FROM books WHERE book_id = %s LIMIT 1", (book_id,), fetch_one=True)
    if not book:
        return jsonify({'error': 'Book not found.'}), 404

    if book['available_quantity'] <= 0:
        return jsonify({'error': 'Book is currently unavailable.'}), 400

    # 3. Prevent borrowing the same book twice at once
    dup_loan_query = "SELECT loan_id FROM loans WHERE member_id = %s AND book_id = %s AND status = 'Issued' LIMIT 1"
    active_dup, _ = execute_query(dup_loan_query, (member_id, book_id), fetch_one=True)
    if active_dup:
        return jsonify({'error': 'This member already has an active loan for this book.'}), 400

    # 4. Read system settings (loan_days)
    settings = get_system_settings()
    loan_days = settings.get('loan_days', 14)

    today = date.today()
    due_date = today + timedelta(days=loan_days)

    # 5. Insert new loan record
    insert_loan = """
        INSERT INTO loans (member_id, book_id, issue_date, due_date, renewal_count, fine_amount, fine_paid, status)
        VALUES (%s, %s, %s, %s, 0, 0.00, FALSE, 'Issued')
    """
    _, err = execute_query(insert_loan, (member_id, book_id, today, due_date), commit=True)
    if err:
        return jsonify({'error': 'Failed to issue book. Please try again.'}), 500

    # 6. Decrease available quantity and update book status
    new_avail = book['available_quantity'] - 1
    new_status = 'Available' if new_avail > 0 else 'Unavailable'
    update_book = "UPDATE books SET available_quantity = %s, status = %s WHERE book_id = %s"
    execute_query(update_book, (new_avail, new_status, book_id), commit=True)

    return jsonify({
        'success': True,
        'message': f'Book "{book["title"]}" issued successfully.',
        'issue_date': str(today),
        'due_date': str(due_date)
    }), 201

@loans_bp.route('/return/<int:loan_id>', methods=['POST'])
@login_required()
def return_book(loan_id):
    """
    Process book return.
    Calculates overdue days and fine based on settings table.
    Enforces business rules:
      - Active loan exists
      - If member role, only allow returning their own loan
      - overdue_days = max(0, return_date - due_date)
      - fine = overdue_days * fine_per_day
      - Restore book available_quantity and status
      - Return due_date, return_date, overdue_days, and fine_amount
    """
    # 1. Fetch active loan with book details
    query = """
        SELECT l.*, b.title, b.book_id, b.available_quantity
        FROM loans l
        JOIN books b ON l.book_id = b.book_id
        WHERE l.loan_id = %s AND l.status = 'Issued'
        LIMIT 1
    """
    loan, _ = execute_query(query, (loan_id,), fetch_one=True)
    if not loan:
        return jsonify({'error': 'Active loan not found.'}), 404

    # Member role check
    if session.get('role') == 'member' and loan['member_id'] != session.get('user_id'):
        return jsonify({'error': 'Access forbidden.'}), 403

    # 2. Calculate overdue and fine
    settings = get_system_settings()
    fine_per_day = settings.get('fine_per_day', 5.0)

    return_date = date.today()
    due_date = loan['due_date']
    if hasattr(due_date, 'date'):
        due_date = due_date.date()

    overdue_days = max(0, (return_date - due_date).days)
    fine_amount = round(overdue_days * fine_per_day, 2)
    fine_paid = True if fine_amount == 0 else False

    # 3. Update loan record
    update_loan = """
        UPDATE loans
        SET return_date = %s, fine_amount = %s, fine_paid = %s, status = 'Returned'
        WHERE loan_id = %s
    """
    _, err = execute_query(update_loan, (return_date, fine_amount, fine_paid, loan_id), commit=True)
    if err:
        return jsonify({'error': 'Failed to process return.'}), 500

    # 4. Increase book available quantity and set status to Available
    new_avail = loan['available_quantity'] + 1
    update_book = "UPDATE books SET available_quantity = %s, status = 'Available' WHERE book_id = %s"
    execute_query(update_book, (new_avail, loan['book_id']), commit=True)

    return jsonify({
        'success': True,
        'message': f'Book "{loan["title"]}" returned successfully.',
        'details': {
            'book_title': loan['title'],
            'due_date': str(due_date),
            'return_date': str(return_date),
            'overdue_days': overdue_days,
            'fine_per_day': fine_per_day,
            'fine_amount': fine_amount,
            'fine_paid': fine_paid
        }
    })

@loans_bp.route('/renew/<int:loan_id>', methods=['POST'])
@login_required()
def renew_book(loan_id):
    """
    Renew an active book loan.
    Enforces business rules:
      - Active loan only
      - If member role, ensure loan belongs to them
      - renewal_count < max_renewals (from settings table)
      - Extend due date by loan_days (from settings table)
      - Return new due date
    """
    # 1. Fetch active loan
    query = """
        SELECT l.*, b.title
        FROM loans l
        JOIN books b ON l.book_id = b.book_id
        WHERE l.loan_id = %s AND l.status = 'Issued'
        LIMIT 1
    """
    loan, _ = execute_query(query, (loan_id,), fetch_one=True)
    if not loan:
        return jsonify({'error': 'Active loan not found.'}), 404

    if session.get('role') == 'member' and loan['member_id'] != session.get('user_id'):
        return jsonify({'error': 'Access forbidden.'}), 403

    # 2. Check settings
    settings = get_system_settings()
    max_renewals = settings.get('max_renewals', 2)
    loan_days = settings.get('loan_days', 14)

    if loan['renewal_count'] >= max_renewals:
        return jsonify({
            'error': f'Maximum renewal limit ({max_renewals} times) reached for this loan.'
        }), 400

    # 3. Calculate new due date (extend from current due date or today if overdue)
    current_due = loan['due_date']
    if hasattr(current_due, 'date'):
        current_due = current_due.date()

    base_date = max(current_due, date.today())
    new_due_date = base_date + timedelta(days=loan_days)
    new_renewal_count = loan['renewal_count'] + 1

    # 4. Update loan
    update_query = """
        UPDATE loans
        SET due_date = %s, renewal_count = %s
        WHERE loan_id = %s
    """
    _, err = execute_query(update_query, (new_due_date, new_renewal_count, loan_id), commit=True)
    if err:
        return jsonify({'error': 'Failed to renew book.'}), 500

    return jsonify({
        'success': True,
        'message': f'Book "{loan["title"]}" renewed successfully.',
        'new_due_date': str(new_due_date),
        'renewal_count': new_renewal_count,
        'max_renewals': max_renewals
    })

@loans_bp.route('/my-loans', methods=['GET'])
@login_required(role='member')
def get_my_loans():
    """
    Get all active borrowed books for the logged-in member.
    Calculates live overdue status and accrued fines.
    """
    member_id = session.get('user_id')
    settings = get_system_settings()
    fine_per_day = settings.get('fine_per_day', 5.0)

    query = """
        SELECT l.*, b.title, b.author, b.category, b.isbn
        FROM loans l
        JOIN books b ON l.book_id = b.book_id
        WHERE l.member_id = %s AND l.status = 'Issued'
        ORDER BY l.due_date ASC
    """
    loans, _ = execute_query(query, (member_id,), fetch_all=True)

    today = date.today()
    result = []
    for l in loans or []:
        due = l['due_date']
        if hasattr(due, 'date'):
            due = due.date()
        
        is_overdue = today > due
        overdue_days = (today - due).days if is_overdue else 0
        current_fine = round(overdue_days * fine_per_day, 2)

        l_dict = dict(l)
        l_dict['issue_date'] = str(l['issue_date'])
        l_dict['due_date'] = str(due)
        l_dict['is_overdue'] = is_overdue
        l_dict['overdue_days'] = overdue_days
        l_dict['current_fine'] = current_fine
        result.append(l_dict)

    return jsonify({'loans': result})

@loans_bp.route('/history', methods=['GET'])
@login_required(role='member')
def get_my_history():
    """
    Get borrowing history (returned books) for the logged-in member.
    """
    member_id = session.get('user_id')
    query = """
        SELECT l.*, b.title, b.author, b.category, b.isbn
        FROM loans l
        JOIN books b ON l.book_id = b.book_id
        WHERE l.member_id = %s AND l.status = 'Returned'
        ORDER BY l.return_date DESC
    """
    loans, _ = execute_query(query, (member_id,), fetch_all=True)

    result = []
    for l in loans or []:
        l_dict = dict(l)
        l_dict['issue_date'] = str(l['issue_date'])
        l_dict['due_date'] = str(l['due_date'])
        l_dict['return_date'] = str(l['return_date']) if l['return_date'] else None
        l_dict['fine_amount'] = float(l['fine_amount'])
        result.append(l_dict)

    return jsonify({'history': result})

@loans_bp.route('/all', methods=['GET'])
@login_required(role='admin')
def get_all_transactions():
    """
    Get all transaction records (active & returned) for Admin.
    Supports filtering by status, search keyword.
    """
    status = request.args.get('status', '').strip()
    search = request.args.get('search', '').strip()

    query = """
        SELECT l.*, m.name AS member_name, m.username AS member_username,
               b.title AS book_title, b.isbn
        FROM loans l
        JOIN members m ON l.member_id = m.member_id
        JOIN books b ON l.book_id = b.book_id
        WHERE 1=1
    """
    params = []

    if status and status.lower() != 'all':
        normalized_status = 'Issued' if status.lower() == 'issued' else ('Returned' if status.lower() == 'returned' else status)
        query += " AND l.status = %s"
        params.append(normalized_status)

    if search:
        query += " AND (m.name LIKE %s OR m.username LIKE %s OR b.title LIKE %s OR b.isbn LIKE %s)"
        pat = f"%{search}%"
        params.extend([pat, pat, pat, pat])

    query += " ORDER BY l.loan_id DESC"

    loans, _ = execute_query(query, tuple(params), fetch_all=True)

    today = date.today()
    settings = get_system_settings()
    fine_per_day = settings.get('fine_per_day', 5.0)

    result = []
    for l in loans or []:
        due = l['due_date']
        if hasattr(due, 'date'):
            due = due.date()

        l_dict = dict(l)
        l_dict['issue_date'] = str(l['issue_date'])
        l_dict['due_date'] = str(due)
        l_dict['return_date'] = str(l['return_date']) if l['return_date'] else None
        l_dict['fine_amount'] = float(l['fine_amount'])

        if l['status'] == 'Issued':
            is_overdue = today > due
            l_dict['is_overdue'] = is_overdue
            l_dict['overdue_days'] = (today - due).days if is_overdue else 0
            if is_overdue and l_dict['fine_amount'] == 0:
                l_dict['fine_amount'] = round(l_dict['overdue_days'] * fine_per_day, 2)
        else:
            l_dict['is_overdue'] = False
            l_dict['overdue_days'] = 0

        result.append(l_dict)

    return jsonify({'transactions': result})
