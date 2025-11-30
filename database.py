import sqlite3
import csv
import shutil
from tkinter import messagebox, filedialog
from datetime import datetime

DB_FILE = 'expenses.db'
CSV_FILE = 'expenses.csv'

# --------------------- Database Setup ---------------------
def create_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS expenses
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL,
                      amount REAL NOT NULL,
                      category TEXT,
                      date TEXT,
                      notes TEXT,
                      payment_method TEXT,
                      location TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS budgets
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL UNIQUE,
                      monthly_budget REAL DEFAULT 0)''')
        conn.commit()

# --------------------- Utilities ---------------------

def export_db_to_csv(path=None):
    """Export current DB expenses table to CSV file. If path None, uses CSV_FILE."""
    path = path or CSV_FILE
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM expenses ORDER BY date ASC")
        rows = c.fetchall()
    if not rows:
        messagebox.showinfo("Export", "No data to export")
        return
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Name', 'Amount', 'Category', 'Date', 'Notes', 'Payment Method', 'Location'])
        writer.writerows(rows)
    messagebox.showinfo("Export", f"Exported {len(rows)} rows to {path}")


def backup_database():
    dest = filedialog.asksaveasfilename(defaultextension='.db', filetypes=[('SQLite DB','*.db'),('All files','*.*')])
    if not dest:
        return
    try:
        shutil.copyfile(DB_FILE, dest)
        messagebox.showinfo('Backup', f'Database backed up to {dest}')
    except Exception as e:
        messagebox.showerror('Backup Error', str(e))


def restore_database():
    src = filedialog.askopenfilename(filetypes=[('SQLite DB','*.db'),('All files','*.*')])
    if not src:
        return
    try:
        shutil.copyfile(src, DB_FILE)
        messagebox.showinfo('Restore', 'Database restored. Please restart the app to see changes.')
    except Exception as e:
        messagebox.showerror('Restore Error', str(e))
