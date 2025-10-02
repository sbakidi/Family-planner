from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Default DATABASE_URL
DEFAULT_DATABASE_URL = "sqlite:///./family_planner.db"
# Test specific DATABASE_URL (in-memory)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Global engine and SessionLocal, can be reconfigured
engine = None
SessionLocal = None
Base = declarative_base()

def get_database_url():
    """Returns test DB URL if TEST_MODE_ENABLED env var is set, else default."""
    if os.environ.get("TEST_MODE_ENABLED") == "1":
        return TEST_DATABASE_URL
    return DEFAULT_DATABASE_URL

def initialize_database_for_application():
    """Initializes or re-initializes the global engine and SessionLocal."""
    global engine, SessionLocal

    current_db_url = get_database_url()

    if engine is None or str(engine.url) != current_db_url:
        # print(f"Initializing database with URL: {current_db_url}")
        connect_args = {}
        if current_db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False # Necessary for SQLite

        engine = create_engine(current_db_url, connect_args=connect_args)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Models need to be imported for Base.metadata to be populated before create_all
    # It's assumed they are imported by the time this is called in a real app,
    # or by tests before they call create_all.
    # Example: from . import user, shift, child, event # etc.

def create_tables():
    """Creates all tables based on Base.metadata."""
    global engine
    if not engine:
        initialize_database_for_application() # Ensure engine is initialized
    # Ensure badge model is imported so its table is registered
    try:
        from . import badge  # noqa: F401
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)
    # print("Database tables created (if they didn't exist).")

def drop_tables():
    """Drops all tables based on Base.metadata."""
    global engine
    if not engine:
        initialize_database_for_application() # Ensure engine is initialized
    Base.metadata.drop_all(bind=engine)
    # print("Database tables dropped.")


# This is the function that main.py currently calls as init_db()
# We'll keep it for compatibility but have it call the new functions.
def init_db():
    initialize_database_for_application()
    # The create_tables() call is often done explicitly at app startup or by tests.
    # For the CLI app, creating tables if they don't exist on each run via main.py is okay.
    create_tables()
    if os.environ.get("TEST_MODE_ENABLED") != "1":
        print("Database initialized (tables created if they didn't exist).")


if __name__ == "__main__":
    # This allows running `python src/database.py` to initialize the DB with default URL.
    # To initialize with test DB: TEST_MODE_ENABLED=1 python src/database.py
    print(f"Initializing database with URL: {get_database_url()}...")
    init_db()
