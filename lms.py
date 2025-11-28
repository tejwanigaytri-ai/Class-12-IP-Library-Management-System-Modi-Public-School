#!/usr/bin/env python3
"""
Library Management System - Corrected
CBSE Class 12 - Informatics Practices (Ready-to-run single-file project)

This cleaned version fixes syntax errors, duplicated functions and integrates
all previously added analytics and admin reset features.

Run: python3 project_lib.py
Dependencies (optional): matplotlib, tabulate
"""

import os
import sqlite3
import hashlib
import getpass
import datetime
import shutil
import sys

# Optional niceties
try:
    from tabulate import tabulate
except Exception:
    tabulate = None

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None

DB_FILE = 'library.db'
BACKUP_DIR = 'backups'
DATEFMT = '%Y-%m-%d'

# ---------------------- Utility Functions ----------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def input_nonempty(prompt: str) -> str:
    while True:
        v = input(prompt).strip()
        if v:
            return v
        print('Input cannot be blank. Please try again.')


def pause():
    input('Press Enter to continue...')


# ---------------------- Database Initialization ----------------------

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','user')),
        created_at TEXT NOT NULL
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        category TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Available','Issued')) DEFAULT 'Available'
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        return_date TEXT NOT NULL,
        returned INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(book_id) REFERENCES books(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')
    conn.commit()


def seed_demo_data(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    user_count = c.fetchone()[0]
    if user_count == 0:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        users = [
            ('admin', hash_password('admin123'), 'admin', now),
            ('user1', hash_password('pass1'), 'user', now),
            ('user2', hash_password('pass2'), 'user', now),
            ('user3', hash_password('pass3'), 'user', now),
            ('user4', hash_password('pass4'), 'user', now),
            ('user5', hash_password('pass5'), 'user', now),
        ]
        c.executemany('INSERT INTO users (username,password,role,created_at) VALUES (?,?,?,?)', users)
        conn.commit()
        print('Seeded users (including default admin: admin/admin123)')

    c.execute('SELECT COUNT(*) FROM books')
    book_count = c.fetchone()[0]
    if book_count == 0:
        sample_books = [
            ('To Kill a Mockingbird', 'Harper Lee', 'Fiction'),
            ('1984', 'George Orwell', 'Fiction'),
            ('A Brief History of Time', 'Stephen Hawking', 'Science'),
            ('The Selfish Gene', 'Richard Dawkins', 'Science'),
            ('The Alchemist', 'Paulo Coelho', 'Fiction'),
            ('Clean Code', 'Robert C. Martin', 'Programming'),
            ('Introduction to Algorithms', 'Cormen et al.', 'Programming'),
            ('Principles of Economics', 'Mankiw', 'Economics'),
            ('Indian Polity', 'Laxmikanth', 'Political Science'),
            ('Art of War', 'Sun Tzu', 'Philosophy'),
            ('The Odyssey', 'Homer', 'Classic'),
            ('Hamlet', 'William Shakespeare', 'Classic'),
            ('The Great Gatsby', 'F. Scott Fitzgerald', 'Fiction'),
            ('Sapiens', 'Yuval Noah Harari', 'History'),
            ('Guns, Germs, and Steel', 'Jared Diamond', 'History'),
            ('The Pragmatic Programmer', 'Andrew Hunt', 'Programming'),
            ('Computer Networks', 'Tanenbaum', 'Programming'),
            ('Data Science from Scratch', 'Joel Grus', 'Programming'),
            ('The Road', 'Cormac McCarthy', 'Fiction'),
            ('The Catcher in the Rye', 'J.D. Salinger', 'Fiction'),
        ]
        c.executemany('INSERT INTO books (title,author,category,status) VALUES (?,?,?,?)', [(t,a,cate,'Available') for (t,a,cate) in sample_books])
        conn.commit()
        print('Seeded 20 sample books')

    c.execute('SELECT COUNT(*) FROM issues')
    issue_count = c.fetchone()[0]
    if issue_count == 0:
        c.execute('SELECT id FROM books LIMIT 9')
        book_ids = [row['id'] for row in c.fetchall()]
        c.execute("SELECT id FROM users WHERE role='user'")
        user_ids = [row['id'] for row in c.fetchall()]
        if len(user_ids) > 0 and len(book_ids) > 0:
            today = datetime.date.today()
            issues = []
            for i, book_id in enumerate(book_ids):
                user_id = user_ids[i % len(user_ids)]
                issue_date = (today - datetime.timedelta(days=2 + i)).strftime(DATEFMT)
                return_date = (today + datetime.timedelta(days=14 - i)).strftime(DATEFMT)
                issues.append((book_id, user_id, issue_date, return_date, 0))
            c.executemany('INSERT INTO issues (book_id,user_id,issue_date,return_date,returned) VALUES (?,?,?,?,?)', issues)
            c.executemany('UPDATE books SET status="Issued" WHERE id=?', [(bid,) for bid in book_ids])
            conn.commit()
            print('Seeded 9 issued books')


def initialize_database():
    first_time = not os.path.exists(DB_FILE)
    conn = get_connection()
    create_tables(conn)
    seed_demo_data(conn)
    conn.close()
    if first_time:
        print('Database created: {}'.format(DB_FILE))


# ---------------------- User Management ----------------------

def reset_admin_password(conn):
    """Reset admin password to admin123 (hashed)."""
    c = conn.cursor()
    new_pass = "admin123"
    hashed = hash_password(new_pass)
    c.execute("UPDATE users SET password=? WHERE username='admin'", (hashed,))
    conn.commit()
    print("Admin password has been reset to: admin123 (SHA-256 protected)")


def reset_user_password(conn):
    """Admin can reset ANY user's password to a new chosen password."""
    c = conn.cursor()
    username = input_nonempty("Enter the username to reset password: ")
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    if not user:
        print("User does not exist.")
        return
    new_pass = input_nonempty("Enter new password for user: ")
    hashed = hash_password(new_pass)
    c.execute("UPDATE users SET password=? WHERE username=?", (hashed, username))
    conn.commit()
    print(f"Password for user '{username}' has been reset successfully.")


def create_user(conn: sqlite3.Connection, username: str, password: str, role: str = 'user'):
    try:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c = conn.cursor()
        c.execute('INSERT INTO users (username,password,role,created_at) VALUES (?,?,?,?)', (username, hash_password(password), role, now))
        conn.commit()
        print('User created:', username)
    except sqlite3.IntegrityError:
        print('Error: Username already exists.')


def update_user(conn: sqlite3.Connection, user_id: int, new_username: str = None, new_role: str = None):
    c = conn.cursor()
    updates = []
    params = []
    if new_username:
        updates.append('username=?')
        params.append(new_username)
    if new_role:
        updates.append('role=?')
        params.append(new_role)
    if not updates:
        print('Nothing to update.')
        return
    params.append(user_id)
    sql = 'UPDATE users SET ' + ','.join(updates) + ' WHERE id=?'
    try:
        c.execute(sql, params)
        conn.commit()
        print('User updated.')
    except sqlite3.IntegrityError:
        print('Error: Username may already exist.')


def delete_user(conn: sqlite3.Connection, user_id: int):
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    print('User deleted (if existed).')


def change_password(conn: sqlite3.Connection, user_id: int):
    c = conn.cursor()
    while True:
        pwd = getpass.getpass('Enter new password: ').strip()
        if not pwd:
            print('Password cannot be blank.')
            continue
        pwd2 = getpass.getpass('Confirm new password: ').strip()
        if pwd != pwd2:
            print('Passwords do not match.')
            continue
        c.execute('UPDATE users SET password=? WHERE id=?', (hash_password(pwd), user_id))
        conn.commit()
        print('Password changed successfully.')
        break


# ---------------------- Book Management ----------------------

def add_book(conn: sqlite3.Connection):
    title = input_nonempty('Title: ')
    author = input_nonempty('Author: ')
    category = input_nonempty('Category: ')
    c = conn.cursor()
    c.execute('INSERT INTO books (title,author,category,status) VALUES (?,?,?,"Available")', (title, author, category))
    conn.commit()
    print('Book added.')


def update_book(conn: sqlite3.Connection):
    book_id = input_nonempty('Book ID to update: ')
    if not book_id.isdigit():
        print('Invalid ID.')
        return
    book_id = int(book_id)
    c = conn.cursor()
    c.execute('SELECT * FROM books WHERE id=?', (book_id,))
    row = c.fetchone()
    if not row:
        print('Book not found.')
        return
    print('Leave blank to keep existing value.')
    title = input('Title [{}]: '.format(row['title'])).strip() or row['title']
    author = input('Author [{}]: '.format(row['author'])).strip() or row['author']
    category = input('Category [{}]: '.format(row['category'])).strip() or row['category']
    status = input('Status (Available/Issued) [{}]: '.format(row['status'])).strip() or row['status']
    if status not in ('Available', 'Issued'):
        print('Invalid status. Keeping existing.')
        status = row['status']
    c.execute('UPDATE books SET title=?,author=?,category=?,status=? WHERE id=?', (title,author,category,status,book_id))
    conn.commit()
    print('Book updated.')


def delete_book(conn: sqlite3.Connection):
    book_id = input_nonempty('Book ID to delete: ')
    if not book_id.isdigit():
        print('Invalid ID.')
        return
    book_id = int(book_id)
    c = conn.cursor()
    c.execute('DELETE FROM books WHERE id=?', (book_id,))
    conn.commit()
    print('Book deleted (if existed).')


# ---------------------- Issue & Return ----------------------

def issue_book(conn: sqlite3.Connection):
    book_id = input_nonempty('Book ID to issue: ')
    if not book_id.isdigit():
        print('Invalid ID.')
        return
    book_id = int(book_id)
    c = conn.cursor()
    c.execute('SELECT * FROM books WHERE id=?', (book_id,))
    book = c.fetchone()
    if not book:
        print('Book not found.')
        return
    if book['status'] == 'Issued':
        print('Book is already issued.')
        return
    user_id = input_nonempty('Issue to User ID: ')
    if not user_id.isdigit():
        print('Invalid user ID.')
        return
    user_id = int(user_id)
    c.execute('SELECT * FROM users WHERE id=?', (user_id,))
    user = c.fetchone()
    if not user:
        print('User not found.')
        return
    issue_date = input('Issue Date (YYYY-MM-DD) [today]: ').strip() or datetime.date.today().strftime(DATEFMT)
    return_date = input('Return Date (YYYY-MM-DD) [2 weeks from issue]: ').strip()
    if not return_date:
        dt_issue = datetime.datetime.strptime(issue_date, DATEFMT).date()
        return_date = (dt_issue + datetime.timedelta(days=14)).strftime(DATEFMT)
    c.execute('INSERT INTO issues (book_id,user_id,issue_date,return_date,returned) VALUES (?,?,?,?,0)', (book_id, user_id, issue_date, return_date))
    c.execute('UPDATE books SET status="Issued" WHERE id=?', (book_id,))
    conn.commit()
    print('Book issued successfully.')


def return_book(conn: sqlite3.Connection):
    issue_id = input_nonempty('Issue ID to return: ')
    if not issue_id.isdigit():
        print('Invalid issue ID.')
        return
    issue_id = int(issue_id)
    c = conn.cursor()
    c.execute('SELECT * FROM issues WHERE id=?', (issue_id,))
    issue = c.fetchone()
    if not issue:
        print('Issue record not found.')
        return
    if issue['returned']:
        print('Book already returned.')
        return
    c.execute('UPDATE issues SET returned=1 WHERE id=?', (issue_id,))
    c.execute('UPDATE books SET status="Available" WHERE id=?', (issue['book_id'],))
    conn.commit()
    print('Book returned successfully.')


def list_issued_books(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute('''
    SELECT issues.id as issue_id, books.id as book_id, books.title, users.username, issues.issue_date, issues.return_date, issues.returned
    FROM issues
    JOIN books ON books.id = issues.book_id
    JOIN users ON users.id = issues.user_id
    WHERE issues.returned=0
    ORDER BY issues.issue_date DESC
    ''')
    rows = c.fetchall()
    if not rows:
        print('No currently issued books.')
        return
    headers = ['IssueID','BookID','Title','IssuedTo','IssueDate','ReturnDate','Returned']
    data = [[r['issue_id'], r['book_id'], r['title'], r['username'], r['issue_date'], r['return_date'], r['returned']] for r in rows]
    print_table(data, headers)


# ---------------------- Search & Filter ----------------------

def search_books(conn: sqlite3.Connection):
    print('Search by: 1) Title 2) Author 3) Category 4) Show All')
    choice = input_nonempty('Choice: ')
    c = conn.cursor()
    if choice == '1':
        q = input_nonempty('Title contains: ')
        c.execute('SELECT * FROM books WHERE title LIKE ?', ('%'+q+'%',))
    elif choice == '2':
        q = input_nonempty('Author contains: ')
        c.execute('SELECT * FROM books WHERE author LIKE ?', ('%'+q+'%',))
    elif choice == '3':
        q = input_nonempty('Category: ')
        c.execute('SELECT * FROM books WHERE category LIKE ?', ('%'+q+'%',))
    elif choice == '4':
        c.execute('SELECT * FROM books')
    else:
        print('Invalid choice.')
        return
    rows = c.fetchall()
    if not rows:
        print('No books found.')
        return
    headers = ['ID','Title','Author','Category','Status']
    data = [[r['id'], r['title'], r['author'], r['category'], r['status']] for r in rows]
    print_table(data, headers)


def filter_by_status(conn: sqlite3.Connection):
    print('Filter by: 1) Available 2) Issued')
    choice = input_nonempty('Choice: ')
    if choice == '1':
        status = 'Available'
    elif choice == '2':
        status = 'Issued'
    else:
        print('Invalid choice.')
        return
    c = conn.cursor()
    c.execute('SELECT * FROM books WHERE status=?', (status,))
    rows = c.fetchall()
    if not rows:
        print('No books found for status', status)
        return
    headers = ['ID','Title','Author','Category','Status']
    data = [[r['id'], r['title'], r['author'], r['category'], r['status']] for r in rows]
    print_table(data, headers)


# ---------------------- Dashboard & Analytics ----------------------

def analytics_menu(conn):
    while True:
        print('===== ADVANCED ANALYTICS MENU =====')
        print('1) Monthly Issues Trend (Line Chart)')
        print('2) Monthly Returns Trend (Line Chart)')
        print('3) Category-wise Availability (Bar Chart)')
        print('4) User-wise Issue Frequency (Histogram)')
        print('5) Issued vs Returned Comparative Trend (Double Line Chart)')
        print('6) Back to Dashboard')
        choice = input_nonempty('Enter choice: ')
        if choice == '1':
            show_monthly_issues(conn)
        elif choice == '2':
            show_monthly_returns(conn)
        elif choice == '3':
            show_category_availability(conn)
        elif choice == '4':
            show_user_issue_histogram(conn)
        elif choice == '5':
            show_issue_return_comparison(conn)
        elif choice == '6':
            return
        else:
            print('Invalid choice!')


def show_monthly_issues(conn):
    if plt is None:
        print('matplotlib not installed.')
        return
    c = conn.cursor()
    c.execute("SELECT substr(issue_date,1,7) AS month, COUNT(*) FROM issues GROUP BY month ORDER BY month")
    rows = c.fetchall()
    if not rows:
        print('No issue data available.')
        return
    months = [r[0] for r in rows]
    counts = [r[1] for r in rows]
    plt.figure()
    plt.plot(months, counts, marker='o')
    plt.title('Monthly Issues Trend')
    plt.xlabel('Month')
    plt.ylabel('Books Issued')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def show_monthly_returns(conn):
    if plt is None:
        print('matplotlib not installed.')
        return
    c = conn.cursor()
    c.execute("SELECT substr(return_date,1,7) AS month, COUNT(*) FROM issues WHERE return_date IS NOT NULL GROUP BY month ORDER BY month")
    rows = c.fetchall()
    if not rows:
        print('No returns data available.')
        return
    months = [r[0] for r in rows]
    counts = [r[1] for r in rows]
    plt.figure()
    plt.plot(months, counts, marker='o')
    plt.title('Monthly Returns Trend')
    plt.xlabel('Month')
    plt.ylabel('Books Returned')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def show_category_availability(conn):
    if plt is None:
        print('matplotlib not installed.')
        return
    c = conn.cursor()
    c.execute("SELECT category, COUNT(*) FROM books WHERE status='Available' GROUP BY category")
    rows = c.fetchall()
    if not rows:
        print('No availability data available.')
        return
    categories = [r[0] for r in rows]
    counts = [r[1] for r in rows]
    plt.figure()
    plt.bar(categories, counts)
    plt.title('Category-wise Available Books')
    plt.xlabel('Category')
    plt.ylabel('Available Count')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def show_user_issue_histogram(conn):
    if plt is None:
        print('matplotlib not installed.')
        return
    c = conn.cursor()
    # user names for histogram
    c.execute('''
        SELECT users.username, COUNT(issues.id) as cnt
        FROM users LEFT JOIN issues ON users.id = issues.user_id
        GROUP BY users.username
        HAVING cnt>0
    ''')
    rows = c.fetchall()
    if not rows:
        print('No user issue data available.')
        return
    users = [r[0] for r in rows]
    counts = [r[1] for r in rows]
    plt.figure()
    plt.bar(users, counts)
    plt.title('User-wise Issue Frequency')
    plt.xlabel('User')
    plt.ylabel('Books Issued')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def show_issue_return_comparison(conn):
    if plt is None:
        print('matplotlib not installed.')
        return
    c = conn.cursor()
    c.execute("SELECT substr(issue_date,1,7) as m, COUNT(*) FROM issues GROUP BY m ORDER BY m")
    issue_rows = c.fetchall()
    c.execute("SELECT substr(return_date,1,7) as m, COUNT(*) FROM issues WHERE return_date IS NOT NULL GROUP BY m ORDER BY m")
    return_rows = c.fetchall()
    months = sorted(list({r[0] for r in issue_rows} | {r[0] for r in return_rows}))
    issue_map = {r[0]: r[1] for r in issue_rows}
    return_map = {r[0]: r[1] for r in return_rows}
    issues_counts = [issue_map.get(m, 0) for m in months]
    returns_counts = [return_map.get(m, 0) for m in months]
    plt.figure()
    plt.plot(months, issues_counts, marker='o', label='Issued Books')
    plt.plot(months, returns_counts, marker='o', label='Returned Books')
    plt.title('Issued vs Returned Books Trend')
    plt.xlabel('Month')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.show()


def show_graphical_analytics(conn):
    # convenience function that opens analytics menu
    analytics_menu(conn)


def show_dashboard(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM books')
    total_books = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM books WHERE status='Issued'")
    issued_books = c.fetchone()[0]
    available_books = total_books - issued_books
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]

    print('Summary Statistics:')
    print('Total Books:', total_books)
    print('Issued Books:', issued_books)
    print('Available Books:', available_books)
    print('Total Users:', total_users)

    c.execute('''
    SELECT books.id, books.title, books.author, COUNT(issues.id) as times_issued
    FROM books LEFT JOIN issues ON books.id = issues.book_id
    GROUP BY books.id
    ORDER BY times_issued DESC
    LIMIT 5
    ''')
    top5 = c.fetchall()
    print('Top 5 Most Issued Books:')
    if top5:
        headers = ['BookID','Title','Author','TimesIssued']
        data = [[r['id'], r['title'], r['author'], r['times_issued']] for r in top5]
        print_table(data, headers)
    else:
        print('No data')

    c.execute('''
    SELECT books.category, COUNT(issues.id) as issued_count
    FROM books JOIN issues ON books.id = issues.book_id
    GROUP BY books.category
    ''')
    category_counts = c.fetchall()

    if plt is None:
        print('matplotlib not installed -> Charts unavailable. To view charts, install matplotlib (pip install matplotlib)')
        return

    categories = [r['category'] for r in category_counts]
    counts = [r['issued_count'] for r in category_counts]

    fig1 = plt.figure(figsize=(10,4))
    ax1 = fig1.add_subplot(1,2,1)
    if categories:
        ax1.bar(categories, counts)
        ax1.set_title('Number of issues per Category')
        ax1.set_xlabel('Category')
        ax1.set_ylabel('Issues')
        plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')
    else:
        ax1.text(0.5,0.5,'No issue data', horizontalalignment='center')

    ax2 = fig1.add_subplot(1,2,2)
    ax2.pie([available_books, issued_books], labels=['Available','Issued'], autopct='%1.1f%%')
    ax2.set_title('Available vs Issued')

    plt.tight_layout()
    plt.show()


# ---------------------- Backup & Restore ----------------------

def backup_database():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(BACKUP_DIR, f'library_backup_{ts}.db')
    shutil.copy2(DB_FILE, dest)
    print('Backup created at', dest)


def list_backups():
    if not os.path.exists(BACKUP_DIR):
        print('No backups found.')
        return []
    items = sorted(os.listdir(BACKUP_DIR))
    for i, name in enumerate(items, start=1):
        print(f'{i}) {name}')
    return items


def restore_database():
    items = list_backups()
    if not items:
        return
    choice = input_nonempty('Choose backup number to restore: ')
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(items):
        print('Invalid choice.')
        return
    src = os.path.join(BACKUP_DIR, items[int(choice)-1])
    shutil.copy2(src, DB_FILE)
    print('Database restored from', src)


# ---------------------- Helpers ----------------------

def print_table(data, headers=None):
    if tabulate:
        print(tabulate(data, headers=headers, tablefmt='psql'))
    else:
        if headers:
            print(' | '.join(headers))
            print('-' * 40)
        for row in data:
            print(' | '.join(str(x) for x in row))


# ---------------------- Authentication & CLI ----------------------

def authenticate(conn: sqlite3.Connection):
    print('Login')
    username = input_nonempty('Username: ')
    pwd = getpass.getpass('Password: ').strip()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=?', (username,))
    user = c.fetchone()
    if not user:
        print('Invalid username or password.')
        return None
    if user['password'] != hash_password(pwd):
        print('Invalid username or password.')
        return None
    return dict(user)


def admin_menu(conn: sqlite3.Connection, user: dict):
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Logged in as ADMIN: {user['username']}")
        print('1) User Management')
        print('2) Book Management')
        print('3) Issue / Return')
        print('4) Search & Filter')
        print('5) Dashboard & Analytics')
        print('6) Advanced Analytics')
        print('7) Backup / Restore')
        print('8) Reset ANY User Password')
        print('9) Change My Password')
        print('0) Logout')
        choice = input_nonempty('Choice: ')
        if choice == '1':
            admin_user_management(conn)
        elif choice == '2':
            admin_book_management(conn)
        elif choice == '3':
            issue_return_menu(conn)
        elif choice == '4':
            search_filter_menu(conn)
        elif choice == '5':
            show_dashboard(conn)
            pause()
        elif choice == '6':
            analytics_menu(conn)
        elif choice == '7':
            print('1) Backup database  2) Restore database')
            c = input_nonempty('Choice: ')
            if c == '1':
                backup_database()
            elif c == '2':
                restore_database()
            else:
                print('Invalid.')
            pause()
        elif choice == '8':
            reset_user_password(conn)
            pause()
        elif choice == '9':
            change_password(conn, user['id'])
            pause()
        elif choice == '0':
            break
        else:
            print('Invalid choice.')
            pause()


def user_menu(conn: sqlite3.Connection, user: dict):
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Logged in as USER: {user['username']}")
        print('1) View Books (Search)')
        print('2) View My Issued Books')
        print('3) Return Book')
        print('4) Change My Password')
        print('0) Logout')
        choice = input_nonempty('Choice: ')
        if choice == '1':
            search_books(conn)
            pause()
        elif choice == '2':
            list_my_issued_books(conn, user['id'])
            pause()
        elif choice == '3':
            return_book(conn)
            pause()
        elif choice == '4':
            change_password(conn, user['id'])
            pause()
        elif choice == '0':
            break
        else:
            print('Invalid choice.')
            pause()


# Admin sub-menus

def admin_user_management(conn: sqlite3.Connection):
    while True:
        print('User Management')
        print('1) Create user')
        print('2) Update user')
        print('3) Delete user')
        print('4) List users')
        print('0) Back')
        c = input_nonempty('Choice: ')
        if c == '1':
            username = input_nonempty('Username: ')
            pwd = getpass.getpass('Password: ').strip()
            role = input_nonempty('Role (admin/user): ')
            if role not in ('admin','user'):
                print('Invalid role.')
                continue
            create_user(conn, username, pwd, role)
        elif c == '2':
            uid = input_nonempty('User ID to update: ')
            if not uid.isdigit():
                print('Invalid ID.')
                continue
            uid = int(uid)
            new_username = input('New username (leave blank to keep): ').strip() or None
            new_role = input('New role (admin/user) (leave blank to keep): ').strip() or None
            if new_role and new_role not in ('admin','user'):
                print('Invalid role.')
                continue
            update_user(conn, uid, new_username, new_role)
        elif c == '3':
            uid = input_nonempty('User ID to delete: ')
            if not uid.isdigit():
                print('Invalid ID.')
                continue
            delete_user(conn, int(uid))
        elif c == '4':
            c = conn.cursor()
            c.execute('SELECT id,username,role,created_at FROM users')
            rows = c.fetchall()
            data = [[r['id'], r['username'], r['role'], r['created_at']] for r in rows]
            print_table(data, ['ID','Username','Role','CreatedAt'])
        elif c == '0':
            break
        else:
            print('Invalid choice.')


def admin_book_management(conn: sqlite3.Connection):
    while True:
        print('Book Management')
        print('1) Add Book')
        print('2) Update Book')
        print('3) Delete Book')
        print('4) List All Books')
        print('0) Back')
        c = input_nonempty('Choice: ')
        if c == '1':
            add_book(conn)
        elif c == '2':
            update_book(conn)
        elif c == '3':
            delete_book(conn)
        elif c == '4':
            c = conn.cursor()
            c.execute('SELECT * FROM books')
            rows = c.fetchall()
            data = [[r['id'], r['title'], r['author'], r['category'], r['status']] for r in rows]
            print_table(data, ['ID','Title','Author','Category','Status'])
        elif c == '0':
            break
        else:
            print('Invalid choice.')


def issue_return_menu(conn: sqlite3.Connection):
    while True:
        print('Issue & Return')
        print('1) Issue Book')
        print('2) Return Book')
        print('3) List Currently Issued Books')
        print('0) Back')
        c = input_nonempty('Choice: ')
        if c == '1':
            issue_book(conn)
        elif c == '2':
            return_book(conn)
        elif c == '3':
            list_issued_books(conn)
        elif c == '0':
            break
        else:
            print('Invalid choice.')


def search_filter_menu(conn: sqlite3.Connection):
    while True:
        print('Search & Filter')
        print('1) Search Books')
        print('2) Filter by Status')
        print('0) Back')
        c = input_nonempty('Choice: ')
        if c == '1':
            search_books(conn)
        elif c == '2':
            filter_by_status(conn)
        elif c == '0':
            break
        else:
            print('Invalid choice.')


def list_my_issued_books(conn: sqlite3.Connection, user_id: int):
    c = conn.cursor()
    c.execute('''
    SELECT issues.id as issue_id, books.id as book_id, books.title, issues.issue_date, issues.return_date, issues.returned
    FROM issues JOIN books ON books.id = issues.book_id
    WHERE issues.user_id=? ORDER BY issues.issue_date DESC
    ''', (user_id,))
    rows = c.fetchall()
    if not rows:
        print('No issued books for you.')
        return
    data = [[r['issue_id'], r['book_id'], r['title'], r['issue_date'], r['return_date'], r['returned']] for r in rows]
    print_table(data, ['IssueID','BookID','Title','IssueDate','ReturnDate','Returned'])


# ---------------------- Main ----------------------

def main():
    initialize_database()
    conn = get_connection()
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print('=== Library Management System (CBSE Class 12 IP) ===')
        print('1) Login')
        print('2) Exit')
        choice = input_nonempty('Choice: ')
        if choice == '1':
            user = authenticate(conn)
            if user:
                if user['role'] == 'admin':
                    admin_menu(conn, user)
                else:
                    user_menu(conn, user)
        elif choice == '2':
            print('Goodbye!')
            conn.close()
            sys.exit(0)
        else:
            print('Invalid choice.')
            pause()


if __name__ == '__main__':
    main()
