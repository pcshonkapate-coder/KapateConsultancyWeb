import os
import sys
import sqlite3
import json

def migrate_local_to_cloud(postgres_url=None):
    if not postgres_url:
        if len(sys.argv) > 1:
            postgres_url = sys.argv[1]
        else:
            try:
                with open('config.json', 'r') as f:
                    cfg = json.load(f)
                    postgres_url = cfg.get('DATABASE_URL', '')
            except Exception:
                pass

    if not postgres_url:
        print("Error: Please provide a PostgreSQL Connection URL.")
        print("Usage: python migrate_to_cloud_db.py 'postgresql://user:password@host:5432/dbname'")
        return

    if postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql://", 1)

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        print("Installing psycopg2-binary...")
        os.system("pip install psycopg2-binary")
        import psycopg2
        from psycopg2.extras import RealDictCursor

    print(f"Connecting to Cloud PostgreSQL Database...")
    pg_conn = psycopg2.connect(postgres_url)
    pg_cur = pg_conn.cursor()

    sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inquiries.db')
    if not os.path.exists(sqlite_path):
        print(f"Local database {sqlite_path} not found.")
        return

    sq_conn = sqlite3.connect(sqlite_path)
    sq_conn.row_factory = sqlite3.Row
    sq_cur = sq_conn.cursor()

    # Get tables from SQLite
    sq_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in sq_cur.fetchall()]

    print(f"Found {len(tables)} tables to migrate from laptop SQLite to Cloud PostgreSQL:")

    # Import server schema init
    os.environ['DATABASE_URL'] = postgres_url
    from server import init_database
    init_database()
    print("Cloud database schema verified and initialized.")

    # Transfer data table by table
    for table in tables:
        sq_cur.execute(f"SELECT * FROM {table}")
        rows = sq_cur.fetchall()
        if not rows:
            print(f"  - Table '{table}': 0 records (skipped)")
            continue

        dict_rows = [dict(r) for r in rows]
        cols = list(dict_rows[0].keys())
        cols_str = ", ".join([f'"{c}"' for c in cols])
        placeholders = ", ".join(["%s"] * len(cols))

        # Clear existing table data in PG to prevent duplicates during initial sync
        pg_cur.execute(f'TRUNCATE TABLE "{table}" CASCADE;')
        
        insert_sql = f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders})'
        for row in dict_rows:
            vals = [row[c] for c in cols]
            pg_cur.execute(insert_sql, vals)

        pg_conn.commit()
        print(f"  - Table '{table}': {len(rows)} records successfully migrated to Cloud SQL.")

    pg_conn.close()
    sq_conn.close()
    print("\nSUCCESS: All local laptop database tables have been migrated to your Cloud SQL Database!")
    print("Now both your live deployed site and laptop can connect to the same live database.")

if __name__ == '__main__':
    migrate_local_to_cloud()
