"""
Run once to add the is_submitted column to the bracket table.
All existing brackets are treated as submitted (is_submitted = TRUE)
so the leaderboard is not disrupted.

Usage:
    python migrate_add_is_submitted.py
"""

import os
import psycopg

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://user:password@localhost/bracketdb"
)

# Render uses postgres://, psycopg needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# psycopg3 doesn't use +psycopg in the URL
DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")

def run():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Add column if it doesn't exist
            cur.execute("""
                ALTER TABLE bracket
                ADD COLUMN IF NOT EXISTS is_submitted BOOLEAN NOT NULL DEFAULT FALSE;
            """)
            # Mark all existing brackets as submitted so nothing breaks
            cur.execute("""
                UPDATE bracket SET is_submitted = TRUE WHERE is_submitted = FALSE;
            """)
            conn.commit()
            print("Migration complete. is_submitted column added and all existing brackets marked as submitted.")

if __name__ == "__main__":
    run()