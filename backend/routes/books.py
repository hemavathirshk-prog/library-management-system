from flask import Blueprint, request, jsonify
from database import execute_query
from routes.auth import login_required

books_bp = Blueprint('books', __name__)

@books_bp.route('', methods=['GET'])
def get_books():
    """
    Get all books or filter by search query (title, author, category),
    category filter, or availability status.
    """
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()

    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if search:
        query += " AND (title LIKE %s OR author LIKE %s OR category LIKE %s OR isbn LIKE %s)"
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

    if category and category.lower() != 'all':
        query += " AND category = %s"
        params.append(category)

    if status and status.lower() != 'all':
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY title ASC"

    books, err = execute_query(query, tuple(params), fetch_all=True)
    if err:
        return jsonify({'error': 'Failed to retrieve books.'}), 500

    return jsonify({'books': books or []})

@books_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Return unique book categories for filtering.
    """
    query = "SELECT DISTINCT category FROM books ORDER BY category ASC"
    rows, err = execute_query(query, fetch_all=True)
    categories = [r['category'] for r in rows] if rows else []
    return jsonify({'categories': categories})

@books_bp.route('/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """
    Get a single book by ID.
    """
    query = "SELECT * FROM books WHERE book_id = %s LIMIT 1"
    book, err = execute_query(query, (book_id,), fetch_one=True)
    if not book:
        return jsonify({'error': 'Book not found.'}), 404

    return jsonify({'book': book})

@books_bp.route('', methods=['POST'])
@login_required(role='admin')
def add_book():
    """
    Add a new book (Admin only).
    """
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    author = data.get('author', '').strip()
    category = data.get('category', '').strip()
    isbn = data.get('isbn', '').strip()
    publisher = data.get('publisher', '').strip()
    quantity_raw = data.get('quantity')

    if not all([title, author, category, isbn, publisher, quantity_raw is not None]):
        return jsonify({'error': 'Please fill in all fields.'}), 400

    try:
        quantity = int(quantity_raw)
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be at least 1.'}), 400
    except ValueError:
        return jsonify({'error': 'Quantity must be a valid number.'}), 400

    # Check for duplicate ISBN
    check_query = "SELECT book_id FROM books WHERE isbn = %s LIMIT 1"
    existing, err = execute_query(check_query, (isbn,), fetch_one=True)
    if existing:
        return jsonify({'error': 'A book with this ISBN already exists.'}), 400

    status = 'Available'
    available_quantity = quantity

    insert_query = """
        INSERT INTO books (title, author, category, isbn, publisher, quantity, available_quantity, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    _, err = execute_query(insert_query, (title, author, category, isbn, publisher, quantity, available_quantity, status), commit=True)
    if err:
        return jsonify({'error': 'Failed to add book. Please try again.'}), 500

    return jsonify({'success': True, 'message': 'Book added successfully.'}), 201

@books_bp.route('/<int:book_id>', methods=['PUT'])
@login_required(role='admin')
def update_book(book_id):
    """
    Update book details (Admin only).
    Safely recalculates available_quantity and status based on currently issued copies.
    """
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    author = data.get('author', '').strip()
    category = data.get('category', '').strip()
    isbn = data.get('isbn', '').strip()
    publisher = data.get('publisher', '').strip()
    quantity_raw = data.get('quantity')

    if not all([title, author, category, isbn, publisher, quantity_raw is not None]):
        return jsonify({'error': 'Please fill in all fields.'}), 400

    try:
        new_quantity = int(quantity_raw)
        if new_quantity <= 0:
            return jsonify({'error': 'Quantity must be at least 1.'}), 400
    except ValueError:
        return jsonify({'error': 'Quantity must be a valid number.'}), 400

    # Fetch existing book
    existing_query = "SELECT * FROM books WHERE book_id = %s LIMIT 1"
    book, err = execute_query(existing_query, (book_id,), fetch_one=True)
    if not book:
        return jsonify({'error': 'Book not found.'}), 404

    # Check for ISBN collision with other books
    isbn_check_query = "SELECT book_id FROM books WHERE isbn = %s AND book_id != %s LIMIT 1"
    dup_isbn, err = execute_query(isbn_check_query, (isbn, book_id), fetch_one=True)
    if dup_isbn:
        return jsonify({'error': 'Another book already uses this ISBN.'}), 400

    # Calculate currently borrowed copies
    current_issued_copies = book['quantity'] - book['available_quantity']
    if new_quantity < current_issued_copies:
        return jsonify({
            'error': f'Cannot reduce total quantity below currently borrowed copies ({current_issued_copies}).'
        }), 400

    new_available_quantity = new_quantity - current_issued_copies
    new_status = 'Available' if new_available_quantity > 0 else 'Unavailable'

    update_query = """
        UPDATE books
        SET title = %s, author = %s, category = %s, isbn = %s, publisher = %s,
            quantity = %s, available_quantity = %s, status = %s
        WHERE book_id = %s
    """
    _, err = execute_query(update_query, (title, author, category, isbn, publisher, new_quantity, new_available_quantity, new_status, book_id), commit=True)
    if err:
        return jsonify({'error': 'Failed to update book.'}), 500

    return jsonify({'success': True, 'message': 'Book updated successfully.'})

@books_bp.route('/<int:book_id>', methods=['DELETE'])
@login_required(role='admin')
def delete_book(book_id):
    """
    Delete a book (Admin only).
    Enforces business rule: Prevent deleting a book that has active loans.
    """
    # 1. Check if book exists
    book_query = "SELECT title FROM books WHERE book_id = %s LIMIT 1"
    book, err = execute_query(book_query, (book_id,), fetch_one=True)
    if not book:
        return jsonify({'error': 'Book not found.'}), 404

    # 2. Check for active loans (Prevent deleting a book that has active loans)
    active_loans_query = "SELECT COUNT(*) AS count FROM loans WHERE book_id = %s AND status = 'Issued'"
    res, err = execute_query(active_loans_query, (book_id,), fetch_one=True)
    if res and res['count'] > 0:
        return jsonify({'error': 'Cannot delete book: Book currently has active loans.'}), 400

    # 3. Clean up returned loan history if any so foreign key constraint doesn't fail
    clean_history_query = "DELETE FROM loans WHERE book_id = %s AND status = 'Returned'"
    execute_query(clean_history_query, (book_id,), commit=True)

    # 4. Delete the book
    delete_query = "DELETE FROM books WHERE book_id = %s"
    _, err = execute_query(delete_query, (book_id,), commit=True)
    if err:
        return jsonify({'error': 'Failed to delete book. Please try again.'}), 500

    return jsonify({'success': True, 'message': f'Book "{book["title"]}" deleted successfully.'})
