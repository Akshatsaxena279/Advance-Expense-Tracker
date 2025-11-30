# NOTE: This application requires the 'tkcalendar' and 'matplotlib' libraries.
# Install them using pip:
# pip install tkcalendar matplotlib

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import sqlite3 # Used in check_budget_alert
from tkcalendar import DateEntry # Import DateEntry widget

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import functions from our new database module
from . import database # Assuming ui.py and database.py are in the same directory

class ExpenseTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Expense Tracker')
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        self.root.geometry(f'{int(sw*0.7)}x{int(sh*0.7)}')

        self.style = ttk.Style()
        self.current_theme = 'clam'
        self.style.theme_use(self.current_theme)

        self._build_ui()
        database.create_db() # Use function from database module
        self.load_user_list()

    # --------------------- UI Build ---------------------
    def _build_ui(self):
        # Top controls
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill='x')

        ttk.Label(top, text='Filter - User:').grid(row=0, column=0, sticky='w')
        self.filter_user = ttk.Entry(top, width=20)
        self.filter_user.grid(row=0, column=1, padx=4)

        ttk.Label(top, text='Category:').grid(row=0, column=2, sticky='w')
        self.filter_category = ttk.Combobox(top, values=['', 'Food', 'Transport', 'Entertainment', 'Other'], state='readonly', width=15)
        self.filter_category.grid(row=0, column=3, padx=4)
        self.filter_category.set('')

        ttk.Label(top, text='Payment:').grid(row=0, column=4, sticky='w')
        self.filter_payment = ttk.Combobox(top, values=['', 'Cash', 'Card', 'Online'], state='readonly', width=12)
        self.filter_payment.grid(row=0, column=5, padx=4)
        self.filter_payment.set('')

        ttk.Label(top, text='From:').grid(row=1, column=0, sticky='w', pady=6)
        self.filter_from = DateEntry(top, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.filter_from.grid(row=1, column=1, padx=4)

        ttk.Label(top, text='To:').grid(row=1, column=2, sticky='w')
        self.filter_to = DateEntry(top, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.filter_to.grid(row=1, column=3, padx=4)

        ttk.Button(top, text='Apply Filters', command=self.apply_filters).grid(row=1, column=4, padx=6)
        ttk.Button(top, text='Clear Filters', command=self.clear_filters).grid(row=1, column=5)

        ttk.Separator(self.root, orient='horizontal').pack(fill='x', pady=8)

        # Middle: Left user list, Right: Expense table
        mid = ttk.Frame(self.root)
        mid.pack(fill='both', expand=True, padx=8, pady=4)

        # Left panel: user list + budget
        left = ttk.Frame(mid)
        left.pack(side='left', fill='y', padx=(0,8))

        ttk.Label(left, text='Users').pack(anchor='w')
        self.user_canvas = tk.Canvas(left, width=200, height=400)
        self.user_frame = ttk.Frame(self.user_canvas)
        vsb = ttk.Scrollbar(left, orient='vertical', command=self.user_canvas.yview)
        self.user_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        self.user_canvas.pack(side='left')
        self.user_canvas.create_window((0,0), window=self.user_frame, anchor='nw')
        self.user_frame.bind('<Configure>', lambda e: self.user_canvas.configure(scrollregion=self.user_canvas.bbox('all')))

        ttk.Button(left, text='Add Budget / Set', command=self.open_budget_window).pack(pady=6, fill='x')

        # Right panel: expenses table and controls
        right = ttk.Frame(mid)
        right.pack(side='left', fill='both', expand=True)

        controls = ttk.Frame(right)
        controls.pack(fill='x')
        ttk.Button(controls, text='Add Expense', command=self.open_add_window).pack(side='left', padx=4)
        ttk.Button(controls, text='Edit Selected', command=self.open_edit_selected).pack(side='left', padx=4)
        ttk.Button(controls, text='Delete Selected', command=self.delete_selected).pack(side='left', padx=4)
        ttk.Button(controls, text='Export CSV', command=lambda: database.export_db_to_csv()).pack(side='left', padx=4) # Use function from database module
        ttk.Button(controls, text='Backup DB', command=database.backup_database).pack(side='left', padx=4) # Use function from database module
        ttk.Button(controls, text='Restore DB', command=database.restore_database).pack(side='left', padx=4) # Use function from database module
        ttk.Button(controls, text='Show Category Chart', command=self.show_category_chart).pack(side='left', padx=4)
        ttk.Button(controls, text='Toggle Theme', command=self.toggle_theme).pack(side='right', padx=4)

        # Treeview for expenses
        cols = ('id','name','amount','category','date','notes','payment_method','location')
        self.tree = ttk.Treeview(right, columns=cols, show='headings')
        for col in cols:
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=100, anchor='center')
        self.tree.pack(side='left', fill='both', expand=True)

        # scrollbars
        ysb = ttk.Scrollbar(right, orient='vertical', command=self.tree.yview)
        xsb = ttk.Scrollbar(right, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscroll=ysb.set, xscroll=xsb.set)
        ysb.pack(side='right', fill='y')
        xsb.pack(side='bottom', fill='x')

        # Bind double click to edit
        self.tree.bind('<Double-1>', lambda e: self.open_edit_selected())

        # Status bar
        self.status = ttk.Label(self.root, text='Ready', relief='sunken', anchor='w')
        self.status.pack(fill='x', side='bottom')

    # --------------------- User + List Management ---------------------
    def load_user_list(self):
        # Clear current
        for w in self.user_frame.winfo_children():
            w.destroy()

        with sqlite3.connect(database.DB_FILE) as conn: # Use DB_FILE from database module
            c = conn.cursor()
            c.execute("SELECT DISTINCT name FROM expenses ORDER BY name COLLATE NOCASE ASC")
            users = [r[0] for r in c.fetchall()]

        # show unique once
        for name in users:
            b = ttk.Button(self.user_frame, text=name, width=25, command=lambda n=name: self.show_user(n))
            b.pack(pady=2)

    def show_user(self, name):
        self.filter_user.delete(0, 'end')
        self.filter_user.insert(0, name)
        self.apply_filters()

    # --------------------- Filters ---------------------
    def apply_filters(self):
        user = self.filter_user.get().strip()
        category = self.filter_category.get().strip()
        payment = self.filter_payment.get().strip()
        ffrom = self.filter_from.get_date().strftime('%Y-%m-%d') if self.filter_from.get_date() else ''
        fto = self.filter_to.get_date().strftime('%Y-%m-%d') if self.filter_to.get_date() else ''

        query = "SELECT * FROM expenses WHERE 1=1"
        params = []
        if user:
            query += " AND name LIKE ?"
            params.append(f"%{user}%")
        if category:
            query += " AND category = ?"
            params.append(category)
        if payment:
            query += " AND payment_method = ?"
            params.append(payment)
        if ffrom:
            query += " AND date >= ?"
            params.append(ffrom)
        if fto:
            query += " AND date <= ?"
            params.append(fto)

        query += " ORDER BY date ASC"
        with sqlite3.connect(database.DB_FILE) as conn: # Use DB_FILE from database module
            c = conn.cursor()
            c.execute(query, params)
            rows = c.fetchall()

        # populate tree
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert('', 'end', values=r)

        self.status.config(text=f'Showing {len(rows)} record(s)')
        # check budget warnings for current user filter
        if user:
            self.check_budget_alert(user)

    def clear_filters(self):
        self.filter_user.delete(0,'end')
        self.filter_category.set('')
        self.filter_payment.set('')
        self.filter_from.set_date('')
        self.filter_to.set_date('')
        self.apply_filters()

    # --------------------- Add / Edit / Delete ---------------------
    def open_add_window(self):
        self._open_expense_window(mode='add')

    def open_edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Edit', 'Select a record first')
            return
        item = self.tree.item(sel[0])['values']
        self._open_expense_window(mode='edit', data=item)

    def _open_expense_window(self, mode='add', data=None):
        win = tk.Toplevel(self.root)
        win.title('Add Expense' if mode=='add' else 'Edit Expense')
        win.geometry('400x450')

        fields = {}
        labels = [('Name','name'),('Amount','amount'),('Date (YYYY-MM-DD)','date'),('Category','category'),('Payment Method','payment'),('Location','location'),('Notes','notes')]
        for lab, key in labels:
            ttk.Label(win, text=lab).pack(anchor='w', padx=8, pady=(8,2))
            if key == 'category':
                fields[key] = ttk.Combobox(win, values=['Food','Transport','Entertainment','Other'], state='readonly')
                fields[key].set('Other')
            elif key == 'payment':
                fields[key] = ttk.Combobox(win, values=['Cash','Card','Online'], state='readonly')
                fields[key].set('Cash')
            elif key == 'date': # New condition for DateEntry
                fields[key] = DateEntry(win, width=18, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
                fields[key].set_date(datetime.now()) # Set default to today
            else:
                fields[key] = ttk.Entry(win)
            fields[key].pack(fill='x', padx=8)

        # prefill for edit
        if mode=='edit' and data:
            # data order: id,name,amount,category,date,notes,payment_method,location
            fields['name'].insert(0, data[1])
            fields['amount'].insert(0, str(data[2]))
            fields['category'].set(data[3])
            fields['date'].set_date(data[4]) # Use set_date for DateEntry
            fields['notes'].insert(0, data[5] or '')
            fields['payment'].set(data[6] or 'Cash')
            fields['location'].insert(0, data[7] or '')

        def save():
            name = fields['name'].get().strip()
            amt_s = fields['amount'].get().strip()
            cat = fields['category'].get().strip()
            pay = fields['payment'].get().strip()
            dat = fields['date'].get_date().strftime('%Y-%m-%d') # Get date from DateEntry and format
            loc = fields['location'].get().strip()
            notes = fields['notes'].get().strip()

            # validations
            if not name:
                messagebox.showerror('Validation', 'Name is required')
                return
            try:
                amt = float(amt_s)
                if amt <= 0:
                    raise ValueError
            except Exception:
                messagebox.showerror('Validation', 'Amount must be a positive number')
                return

            with sqlite3.connect(database.DB_FILE) as conn: # Use DB_FILE from database module
                c = conn.cursor()
                if mode=='add':
                    c.execute('''INSERT INTO expenses (name, amount, category, date, notes, payment_method, location)\
                                 VALUES (?,?,?,?,?,?,?)''', (name, amt, cat, dat, notes, pay, loc))\
                else:
                    rec_id = data[0]
                    c.execute('''UPDATE expenses SET name=?, amount=?, category=?, date=?, notes=?, payment_method=?, location=? WHERE id=?''',\
                              (name, amt, cat, dat, notes, pay, loc, rec_id))
                conn.commit()

            win.destroy()\
            self.load_user_list()\
            self.apply_filters()\
            messagebox.showinfo('Saved', 'Record saved successfully')\
            # check budget for this user\
            self.check_budget_alert(name)

        ttk.Button(win, text='Save', command=save).pack(pady=12)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Delete', 'Select a record first')
            return
        if not messagebox.askyesno('Confirm', 'Delete selected record(s)?'):
            return
        ids = [self.tree.item(s)['values'][0] for s in sel]
        with sqlite3.connect(database.DB_FILE) as conn: # Use DB_FILE from database module
            c = conn.cursor()
            c.executemany('DELETE FROM expenses WHERE id=?', [(i,) for i in ids])
            conn.commit()
        self.apply_filters()
        self.load_user_list()
        messagebox.showinfo('Deleted', f'Deleted {len(ids)} record(s)')

    # --------------------- Budget ---------------------
    def open_budget_window(self):
        win = tk.Toplevel(self.root)
        win.title('Set Monthly Budget')
        win.geometry('350x200')

        ttk.Label(win, text='User Name').pack(anchor='w', padx=8, pady=(8,2))
        name_ent = ttk.Entry(win)
        name_ent.pack(fill='x', padx=8)

        ttk.Label(win, text='Monthly Budget (number)').pack(anchor='w', padx=8, pady=(8,2))
        bud_ent = ttk.Entry(win)
        bud_ent.pack(fill='x', padx=8)

        def save_budget():
            n = name_ent.get().strip()
            try:
                b = float(bud_ent.get().strip())
                if b < 0:
                    raise ValueError
            except Exception:
                messagebox.showerror('Validation', 'Budget must be a non-negative number')
                return
            if not n:
                messagebox.showerror('Validation', 'User name required')
                return
            with sqlite3.connect(database.DB_FILE) as conn: # Use DB_FILE from database module
                c = conn.cursor()
                c.execute('INSERT OR REPLACE INTO budgets (id, name, monthly_budget) VALUES ((SELECT id FROM budgets WHERE name=?), ?, ?)', (n, n, b))
                conn.commit()
            messagebox.showinfo('Saved', 'Budget saved')
            win.destroy()

        ttk.Button(win, text='Save Budget', command=save_budget).pack(pady=12)

    def check_budget_alert(self, name):
        # calculate current month's spending for the user
        today = date.today()
        first = today.replace(day=1).strftime('%Y-%m-%d')
        last = today.strftime('%Y-%m-%d')
        with sqlite3.connect(database.DB_FILE) as conn: # Use DB_FILE from database module
            c = conn.cursor()
            c.execute('SELECT SUM(amount) FROM expenses WHERE name=? AND date BETWEEN ? AND ?', (name, first, last))
            total = c.fetchone()[0] or 0
            c.execute('SELECT monthly_budget FROM budgets WHERE name=?', (name,))
            row = c.fetchone()
            budget = row[0] if row else None
        if budget is not None and budget > 0:
            if total > budget:
                messagebox.showwarning('Budget Exceeded', f"{name} has spent {total:.2f} this month which exceeds budget {budget:.2f}")
            else:
                self.status.config(text=f"{name} spent {total:.2f} of {budget:.2f} this month")

    # --------------------- Theme ---------------------
    def toggle_theme(self):
        self.current_theme = 'alt' if self.current_theme=='clam' else 'clam'
        try:
            self.style.theme_use(self.current_theme)
        except Exception:
            pass

    def show_category_chart(self):
        # Create a new Toplevel window for the chart
        chart_win = tk.Toplevel(self.root)
        chart_win.title("Expense Category Distribution")
        chart_win.geometry("600x500")

        fig, ax = plt.subplots(figsize=(6, 5))
        canvas = FigureCanvasTkAgg(fig, master=chart_win)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.update_category_chart(ax, canvas)

        # Bind closing event to properly destroy the matplotlib figure
        chart_win.protocol("WM_DELETE_WINDOW", lambda: self._on_chart_close(chart_win, fig))

    def _on_chart_close(self, chart_win, fig):
        plt.close(fig) # Close the matplotlib figure to free memory
        chart_win.destroy()

    def update_category_chart(self, ax, canvas):
        # Clear previous plot
        ax.clear()

        # Fetch data
        with sqlite3.connect(database.DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
            data = c.fetchall()

        if not data:
            ax.text(0.5, 0.5, "No expense data to display chart.", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            canvas.draw()
            return

        categories = [row[0] for row in data]
        amounts = [row[1] for row in data]

        # Create pie chart
        ax.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90)
        ax.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
        ax.set_title('Expense Distribution by Category')

        canvas.draw()