import sqlite3
import json
import csv
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inquiries.db')
EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'local_database_exports')

def export_all_data():
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} does not exist.")
        return

    os.makedirs(EXPORT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]

    full_backup = {}

    print(f"Exporting local SQLite database from {DB_FILE}...")

    for table in tables:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        
        # JSON list of dicts
        table_data = [dict(row) for row in rows]
        full_backup[table] = table_data

        # Export individual CSV
        csv_path = os.path.join(EXPORT_DIR, f"{table}.csv")
        if table_data:
            keys = table_data[0].keys()
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                dict_writer = csv.DictWriter(f, fieldnames=keys)
                dict_writer.writeheader()
                dict_writer.writerows(table_data)
        else:
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write("")

        print(f"  - Table '{table}': {len(rows)} records exported to CSV")

    # Save Full JSON Export
    json_path = os.path.join(EXPORT_DIR, 'database_complete_backup.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(full_backup, f, indent=2, ensure_ascii=False)
    print(f"\nFull JSON backup saved to: {json_path}")

    # Generate SQL dump
    sql_dump_path = os.path.join(EXPORT_DIR, 'database_dump.sql')
    with open(sql_dump_path, 'w', encoding='utf-8') as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    print(f"Full SQL Dump saved to: {sql_dump_path}")

    conn.close()
    print("\nAll local database tables successfully exported!")

if __name__ == '__main__':
    export_all_data()
