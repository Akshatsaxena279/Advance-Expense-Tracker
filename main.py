import tkinter as tk
from ui import ExpenseTrackerApp
from database import create_db

if __name__ == '__main__':
    create_db()
    root = tk.Tk()
    app = ExpenseTrackerApp(root)
    root.mainloop()