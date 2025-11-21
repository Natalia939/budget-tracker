import sqlite3
import csv
from datetime import datetime

DB_FILE = "transactions.db"


def print_table(rows, headers):
    col_widths = [len(header) for header in headers]

    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    header_row = " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers))
    separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))

    print(header_row)
    print(separator)

    for row in rows:
        print(" | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))


def main():
    _init_db()
    print("\n=== Budget Tracker ===")
    while True:
        print("\nMenu:")
        print("1. Add Transaction")
        print("2. Generate Report")
        print("3. Manage Transactions")
        print("4. Export Transactions to CSV")
        print("5. Exit")
        choice = input("Enter your choice (1-5): ").strip()

        if choice == "1":
            add_transaction()
        elif choice == "2":
            generate_report()
        elif choice == "3":
            manage_transactions()
        elif choice == "4":
            export_to_csv()
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

def _init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_valid_date(prompt="Enter date (YYYY-MM-DD) or press Enter for today: "):
    while True:
        date_input = input(prompt).strip()
        if not date_input:
            return datetime.now().strftime("%Y-%m-%d")
        try:
            valid_date = datetime.strptime(date_input, "%Y-%m-%d")
            return valid_date.strftime("%Y-%m-%d")
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

def add_transaction():
    print("\n=== Add Transaction ===")
    while True:
        try:
            amount = float(input("Enter amount (positive for income, negative for expense): "))
            break
        except ValueError:
            print("Invalid amount. Please enter a number.")

    if amount >= 0:
        categories = ["Salary", "Bonus", "Gift", "Other Income"]
    else:
        categories = ["Food", "Rent", "Utilities", "Entertainment", "Other Expense"]

    print("\nSelect a category:")
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat}")
    print(f"{len(categories)+1}. Custom Category")

    while True:
        choice = input(f"Enter choice (1-{len(categories)+1}): ").strip()
        if choice.isdigit():
            choice = int(choice)
            if 1 <= choice <= len(categories):
                category = categories[choice-1]
                break
            elif choice == len(categories)+1:
                category = input("Enter custom category: ").strip()
                if category:
                    break
        print("Invalid choice. Please try again.")

    date = get_valid_date()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transactions (date, amount, category) VALUES (?, ?, ?)",
                (date, amount, category))
    conn.commit()
    conn.close()
    print("Transaction added successfully!")

def generate_report():
    print("\n=== Generate Report ===")
    start_date = input("Enter start date (YYYY-MM-DD) or press Enter to skip: ").strip()
    end_date = input("Enter end date (YYYY-MM-DD) or press Enter to skip: ").strip()
    filter_category = input("Enter a category to filter or press Enter to show all: ").strip()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    query = "SELECT date, amount, category FROM transactions WHERE 1=1"
    params = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if filter_category:
        query += " AND LOWER(category) = ?"
        params.append(filter_category.lower())

    cursor.execute(query, params)
    transactions = cursor.fetchall()
    conn.close()

    income_totals = {}
    expense_totals = {}
    total_income = 0
    total_expense = 0

    for date, amount, category in transactions:
        if not category.strip():
            category = "Uncategorized"
        if amount >= 0:
            income_totals[category] = income_totals.get(category, 0) + amount
            total_income += amount
        else:
            expense_totals[category] = expense_totals.get(category, 0) + abs(amount)
            total_expense += abs(amount)

    sort_option = input("Sort categories by (1) Name or (2) Amount? [1/2]: ").strip()
    sort_key = (lambda x: x[0].lower()) if sort_option == "1" else (lambda x: x[1])

    print("\n=== Income ===")
    if income_totals:
        rows = sorted([[cat, f"${total:.2f}"] for cat, total in income_totals.items()], key=lambda x: x[0])
        rows.append(["Total Income", f"${total_income:.2f}"])
        print_table(rows, ["Category", "Amount"])
    else:
        print("No income transactions found.")

    print("\n=== Expenses ===")
    if expense_totals:
        rows = sorted([[cat, f"${total:.2f}"] for cat, total in expense_totals.items()], key=lambda x: x[0])
        rows.append(["Total Expenses", f"${total_expense:.2f}"])
        print_table(rows, ["Category", "Amount"])
    else:
        print("No expense transactions found.")

    print(f"\nNet Balance: ${total_income - total_expense:.2f}")
    input("\nPress Enter to continue...")

def manage_transactions():
    print("\n=== Manage Transactions ===")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, amount, category FROM transactions")
    transactions = cursor.fetchall()
    conn.close()

    if not transactions:
        print("No transactions found.")
        return

    for idx, (tid, date, amount, category) in enumerate(transactions, 1):
        print(f"{idx}. {date} - ${amount} ({category}) [ID: {tid}]")

    choice = input("\nEnter transaction number to edit/delete or press Enter to cancel: ").strip()
    if not choice.isdigit():
        print("Cancelled.")
        return

    choice = int(choice) - 1
    if choice < 0 or choice >= len(transactions):
        print("Invalid selection.")
        return

    transaction_id = transactions[choice][0]
    action = input("Enter 'e' to edit or 'd' to delete: ").strip().lower()

    if action == 'e':
        edit_transaction(transaction_id)
    elif action == 'd':
        delete_transaction(transaction_id)
    else:
        print("Invalid action. Returning to menu.")

def edit_transaction(transaction_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT date, amount, category FROM transactions WHERE id = ?", (transaction_id,))
    date, amount, category = cursor.fetchone()

    new_date = input(f"Enter new date (YYYY-MM-DD) or press Enter to keep [{date}]: ").strip() or date

    while True:
        new_amount_input = input(f"Enter new amount or press Enter to keep [{amount}]: ").strip()
        if not new_amount_input:
            new_amount = amount
            break
        try:
            new_amount = float(new_amount_input)
            break
        except ValueError:
            print("Invalid amount. Please enter a number.")

    if new_amount >= 0:
        categories = ["Salary", "Bonus", "Gift", "Other Income"]
    else:
        categories = ["Food", "Rent", "Utilities", "Entertainment", "Other Expense"]

    print("\nSelect a category:")
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat}")
    print(f"{len(categories)+1}. Keep current [{category}]")
    print(f"{len(categories)+2}. Custom Category")

    while True:
        choice = input(f"Enter choice (1-{len(categories)+2}): ").strip()
        if choice.isdigit():
            choice = int(choice)
            if 1 <= choice <= len(categories):
                new_category = categories[choice-1]
                break
            elif choice == len(categories)+1:
                new_category = category
                break
            elif choice == len(categories)+2:
                new_category = input("Enter custom category: ").strip()
                if new_category:
                    break
        print("Invalid choice. Please try again.")

    cursor.execute("UPDATE transactions SET date = ?, amount = ?, category = ? WHERE id = ?",
                (new_date, new_amount, new_category, transaction_id))
    conn.commit()
    conn.close()
    print("Transaction updated successfully!")

def delete_transaction(transaction_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
    print("Transaction deleted successfully!")

def export_to_csv():
    print("\n=== Export Transactions to CSV ===")
    start_date = input("Enter start date (YYYY-MM-DD) or press Enter to skip: ").strip()
    end_date = input("Enter end date (YYYY-MM-DD) or press Enter to skip: ").strip()
    filter_category = input("Enter category to filter or press Enter to export all: ").strip()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    query = "SELECT date, amount, category FROM transactions WHERE 1=1"
    params = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if filter_category:
        query += " AND LOWER(category) = ?"
        params.append(filter_category.lower())

    cursor.execute(query, params)
    transactions = cursor.fetchall()
    conn.close()

    if not transactions:
        print("No transactions to export.")
        return

    income_totals = {}
    expense_totals = {}
    total_income = 0
    total_expense = 0

    for date, amount, category in transactions:
        if amount >= 0:
            income_totals[category] = income_totals.get(category, 0) + amount
            total_income += amount
        else:
            expense_totals[category] = expense_totals.get(category, 0) + abs(amount)
            total_expense += abs(amount)

    filename = "transactions_export.csv"
    with open(filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Type", "Category", "Amount"])
        for cat, total in income_totals.items():
            writer.writerow(["Income", cat, f"{total:.2f}"])
        writer.writerow(["Total Income", "", f"{total_income:.2f}"])
        for cat, total in expense_totals.items():
            writer.writerow(["Expense", cat, f"{total:.2f}"])
        writer.writerow(["Total Expenses", "", f"{total_expense:.2f}"])
        writer.writerow(["Net Balance", "", f"{total_income - total_expense:.2f}"])

    print(f"Transactions exported successfully to '{filename}'.")
    input("Press Enter to continue...")

if __name__ == "__main__":
    main()
