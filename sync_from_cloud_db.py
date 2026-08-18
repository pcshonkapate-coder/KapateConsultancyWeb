import os
import sys
import sqlite3
import json

def pull_from_cloud(postgres_url=None):
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
        print("Error: Please provide a PostgreSQL Connection URL in config.json or as an argument.")
        print("Usage: python sync_from_cloud_db.py 'postgresql://user:password@host:5432/dbname'")
        return

    if postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql://", 1)

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        os.system("pip install psycopg2-binary")
        import psycopg2
        from psycopg2.extras import RealDictCursor

    print(f"Connecting to Cloud PostgreSQL Database...")
    pg_conn = psycopg2.connect(postgres_url, cursor_factory=RealDictCursor)
    pg_cur = pg_conn.cursor()

    sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inquiries.db')
    sq_conn = sqlite3.connect(sqlite_path)
    sq_cur = sq_conn.cursor()

    # Get all tables from PostgreSQL
    pg_cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = [r['table_name'] for r in pg_cur.fetchall()]

    print(f"Pulling live data from {len(tables)} tables to your laptop:")

    for table in tables:
        pg_cur.execute(f'SELECT * FROM "{table}"')
        rows = pg_cur.fetchall()
        if not rows:
            continue

        cols = list(rows[0].keys())
        cols_str = ", ".join(cols)
        placeholders = ", ".join(["?"] * len(cols))

        try:
            sq_cur.execute(f"DELETE FROM {table}")
            insert_sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})"
            for row in rows:
                sq_cur.execute(insert_sql, [row[c] for c in cols])
            sq_conn.commit()
            print(f"  - Synced '{table}': {len(rows)} records downloaded to local inquiries.db")
        except Exception as e:
            print(f"  - Warning syncing {table}: {e}")

    pg_conn.close()
    sq_conn.close()
    print("\nSUCCESS: All live production data has been synced to your laptop's local inquiries.db!")

if __name__ == '__main__':
    pull_from_cloud()
