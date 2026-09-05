import os
import re
import sqlite3
import logging

logger = logging.getLogger("agentos_database")

# Try to import psycopg2 and psycopg2.extras for PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False
    logger.warning("psycopg2-binary not installed. PostgreSQL support will be unavailable until installed.")

# Determine Database Configuration
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./agentos.db")
IS_POSTGRES = DB_URL.startswith("postgres://") or DB_URL.startswith("postgresql://")

# Calculate SQLite path if needed (fallback)
if DB_URL.startswith("sqlite:///"):
    db_path_part = DB_URL.replace("sqlite:///", "")
    # Note: DB_FILE is resolved relative to the backend root directory
    if db_path_part.startswith("./"):
        DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), db_path_part))
    else:
        DB_FILE = os.path.abspath(db_path_part)
else:
    DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "agentos.db"))


def pg_translate_sql(sql: str) -> str:
    """
    Translates SQLite-specific dialect SQL strings into PostgreSQL-compatible SQL.
    """
    if not sql:
        return sql

    # 1. Ignore SQLite PRAGMAs
    if "PRAGMA" in sql:
        return "SELECT 1;"

    # 2. Replace SQLite ? placeholder with PostgreSQL %s placeholder
    translated = sql.replace("?", "%s")

    # 3. Handle INSERT OR IGNORE INTO sessions
    if "INSERT OR IGNORE INTO sessions" in translated:
        translated = translated.replace("INSERT OR IGNORE INTO sessions", "INSERT INTO sessions")
        if "ON CONFLICT" not in translated:
            translated += " ON CONFLICT (id) DO NOTHING"

    # 4. Handle INSERT OR REPLACE INTO agent_registry
    if "INSERT OR REPLACE INTO agent_registry" in translated:
        if "tasks_completed" in translated:
            translated = """INSERT INTO agent_registry 
               (id, name, role, capabilities, tools, model, cubicle, status, enabled, tasks_completed, tokens_used, execution_time_sum) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'IDLE', 1, 0, 0, 0)
               ON CONFLICT (id) DO UPDATE SET 
               name = EXCLUDED.name,
               role = EXCLUDED.role,
               capabilities = EXCLUDED.capabilities,
               tools = EXCLUDED.tools,
               model = EXCLUDED.model,
               cubicle = EXCLUDED.cubicle
            """
        else:
            translated = """INSERT INTO agent_registry (id, name, role, capabilities, tools, model, cubicle) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET 
               name = EXCLUDED.name,
               role = EXCLUDED.role,
               capabilities = EXCLUDED.capabilities,
               tools = EXCLUDED.tools,
               model = EXCLUDED.model,
               cubicle = EXCLUDED.cubicle
            """

    # 5. Handle INSERT OR REPLACE INTO agents
    if "INSERT OR REPLACE INTO agents" in translated:
        translated = """INSERT INTO agents (id, session_id, role, model, model_override, system_prompt, status) 
           VALUES (%s, 'spark_default_session', %s, %s, %s, '', 'IDLE')
           ON CONFLICT (id) DO UPDATE SET 
           session_id = EXCLUDED.session_id,
           role = EXCLUDED.role,
           model = EXCLUDED.model,
           model_override = EXCLUDED.model_override
        """

    # 6. Handle test sessions INSERT OR REPLACE
    if "INSERT OR REPLACE INTO sessions" in translated:
        translated = re.sub(
            r"INSERT\s+OR\s+REPLACE\s+INTO\s+sessions\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
            r"INSERT INTO sessions (\1) VALUES (\2) ON CONFLICT (id) DO UPDATE SET description = EXCLUDED.description, status = EXCLUDED.status",
            translated,
            flags=re.IGNORECASE
        )

    # 7. Convert sqlite boolean values in update statements
    # e.g., compromise_allowed = 1 -> compromise_allowed = TRUE, and resolve int casts to boolean in queries
    # psycopg2 manages Python bools perfectly, so parameters don't require string replacement.

    return translated


class PostgresCursorWrapper:
    def __init__(self, pg_cursor):
        self._cursor = pg_cursor

    def execute(self, query: str, params: tuple = None):
        translated_query = pg_translate_sql(query)
        if params is None:
            self._cursor.execute(translated_query)
        else:
            # Convert any integer/string representations of bools if necessary,
            # but psycopg2 handles standard tuple params natively.
            self._cursor.execute(translated_query, params)
        return self

    def executemany(self, query: str, params_list: list):
        translated_query = pg_translate_sql(query)
        self._cursor.executemany(translated_query, params_list)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return row

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()


class PostgresConnectionWrapper:
    def __init__(self, pg_conn):
        self._conn = pg_conn
        self._row_factory = None

    def cursor(self):
        # DictCursor ensures dict(row) and row["col"] work natively, mirroring sqlite3.Row
        pg_cursor = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return PostgresCursorWrapper(pg_cursor)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def execute(self, query: str, params: tuple = None):
        cursor = self.cursor()
        cursor.execute(query, params)
        return cursor

    @property
    def row_factory(self):
        return self._row_factory

    @row_factory.setter
    def row_factory(self, val):
        self._row_factory = val


def get_db():
    """
    Initializes and returns a connection to either PostgreSQL or SQLite
    depending on the presence of a postgres connection string in DATABASE_URL.
    """
    if IS_POSTGRES:
        if not HAS_POSTGRES:
            raise ImportError(
                "DATABASE_URL is set to PostgreSQL, but psycopg2 is not installed. "
                "Please run `pip install psycopg2-binary` to enable PostgreSQL support."
            )
        # In Postgres, connection URLs starting with postgresql:// or postgres:// are supported
        conn = psycopg2.connect(DB_URL)
        return PostgresConnectionWrapper(conn)
    else:
        # Fall back to SQLite
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
        except Exception:
            pass
        return conn
