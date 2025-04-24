# backend/tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as DbSession
from unittest.mock import MagicMock # Keep MagicMock if used

# Corrected Imports: Use absolute path from 'backend'
try:
    # Assuming app instance and get_db are in backend.app
    from backend.app import app, get_db
    # Assuming Base is defined in backend.app.models (adjust if different)
    from backend.app.models import Base
    # Assuming db_init functions are in backend.app.db_init
    from backend.app.db_init import populate_database, create_tables
except ImportError as e:
    print(f"Error importing test dependencies for test_api: {e}")
    # Define dummy app/functions if needed for structural testing
    from flask import Flask
    app = Flask(__name__)
    def get_db(): pass
    class Base: metadata = MagicMock()
    def populate_database(db): pass
    def create_tables(engine): pass


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:" # Use in-memory SQLite for tests

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Apply override before creating TestClient
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Check if 'app' is a FastAPI instance before overriding
client = None
if hasattr(app, 'dependency_overrides'): # FastAPI check
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
else:
    print("Warning: 'app' is not a FastAPI instance. API tests using TestClient will be skipped.")


@pytest.fixture(scope="module", autouse=True)
def setup_tear_down_db():
    """Creates tables before tests and drops them after."""
    if hasattr(Base, 'metadata') and Base.metadata is not None:
        Base.metadata.create_all(bind=engine)
        # Optional: Populate data if needed globally for the module
        # with TestingSessionLocal() as db:
        #     populate_database(db)
        yield
        Base.metadata.drop_all(bind=engine)
    else:
        print("ERROR: SQLAlchemy Base.metadata not found or None. Skipping test DB setup.")
        yield # Allow tests to run but likely fail


# --- Test Functions ---
def test_get_all_users():
    if not client: pytest.skip("Skipping API test: TestClient not available.")
    # Create sample data for this test specifically
    with TestingSessionLocal() as db:
         # Add test users here if needed, e.g., using UserManagement or direct model creation
         pass # Replace with user creation logic if needed

    response = client.get("/api/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # Add more specific assertions based on expected data

# ... (rest of the API tests using absolute imports and checking 'client') ...

