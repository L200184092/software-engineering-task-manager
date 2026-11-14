import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "tasks.db"


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Create and safely migrate the SQLite schema without deleting data."""
    with get_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE (user_id, name)
            )
            """
        )

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
        }

        if "priority" not in columns:
            connection.execute(
                """
                ALTER TABLE tasks
                ADD COLUMN priority TEXT NOT NULL DEFAULT 'Medium'
                """
            )

        if "due_date" not in columns:
            connection.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")

        if "user_id" not in columns:
            connection.execute(
                """
                ALTER TABLE tasks
                ADD COLUMN user_id INTEGER REFERENCES users(id)
                """
            )

        if "category_id" not in columns:
            connection.execute(
                """
                ALTER TABLE tasks
                ADD COLUMN category_id INTEGER
                REFERENCES categories(id) ON DELETE SET NULL
                """
            )

        if "recurrence" not in columns:
            connection.execute(
                "ALTER TABLE tasks ADD COLUMN recurrence TEXT NOT NULL DEFAULT 'none'"
            )

        if "next_occurrence_created" not in columns:
            connection.execute(
                "ALTER TABLE tasks ADD COLUMN next_occurrence_created INTEGER NOT NULL DEFAULT 0"
            )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS subtasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_subtasks_task_user ON subtasks(task_id, user_id)"
        )
