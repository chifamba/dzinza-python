import pytest
import uuid
from unittest.mock import patch, MagicMock
from flask import Flask, jsonify, g

# Assuming your Blueprint 'trees_bp' is in backend.blueprints.trees
from blueprints.trees import trees_bp 

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    # Register the blueprint
    app.register_blueprint(trees_bp, url_prefix='/api') # Match your actual prefix

    # Mock global 'g' object if needed by decorators or endpoint logic
    # For example, if @require_tree_access uses g.active_tree_id
    @app.before_request
    def set_globals():
        g.db = MagicMock() # Mock database session if needed
        g.active_tree_id = uuid.uuid4() # Mock active_tree_id

    return app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@patch('blueprints.trees.get_pagination_params')
@patch('blueprints.trees.get_tree_data_for_visualization_db')
def test_get_tree_data_endpoint_success(mock_get_tree_data_db, mock_get_pagination, client, app):
    """Test successful retrieval of tree data with pagination."""
    
    # Mock get_pagination_params
    page, per_page, sort_by, sort_order = 1, 10, "created_at", "asc"
    mock_get_pagination.return_value = (page, per_page, sort_by, sort_order)

    # Mock service function return value
    mock_service_response = {
        "nodes": [{"id": str(uuid.uuid4()), "label": "Node 1"}],
        "links": [{"id": str(uuid.uuid4()), "source": "node1", "target": "node2"}],
        "pagination": {"current_page": page, "per_page": per_page, "total_items": 1, "total_pages":1, "has_next_page": False}
    }
    mock_get_tree_data_db.return_value = mock_service_response
    
    active_tree_id_in_g = g.active_tree_id # Capture g.active_tree_id set by @app.before_request

    response = client.get(f'/api/tree_data?page={page}&per_page={per_page}') # Match your endpoint route

    assert response.status_code == 200
    json_data = response.get_json()
    
    assert json_data["nodes"] == mock_service_response["nodes"]
    assert json_data["links"] == mock_service_response["links"]
    assert json_data["pagination"] == mock_service_response["pagination"]

    # Verify service function was called correctly
    # g.active_tree_id is used directly by the endpoint from the global 'g'
    mock_get_tree_data_db.assert_called_once_with(g.db, active_tree_id_in_g, page, per_page, sort_by, sort_order)
    
    # Verify get_pagination_params was called
    mock_get_pagination.assert_called_once()


@patch('blueprints.trees.get_pagination_params')
@patch('blueprints.trees.get_tree_data_for_visualization_db')
def test_get_tree_data_endpoint_custom_pagination_params(mock_get_tree_data_db, mock_get_pagination, client, app):
    """Test with custom pagination parameters from query string."""
    custom_page, custom_per_page = 2, 5
    # sort_by and sort_order from get_pagination_params will be used by the endpoint
    default_sort_by, default_sort_order = "created_at", "asc" 
    mock_get_pagination.return_value = (custom_page, custom_per_page, default_sort_by, default_sort_order)

    mock_service_response = {
        "nodes": [], "links": [], 
        "pagination": {"current_page": custom_page, "per_page": custom_per_page, "total_items": 0, "total_pages":0, "has_next_page": False}
    }
    mock_get_tree_data_db.return_value = mock_service_response
    
    active_tree_id_in_g = g.active_tree_id

    # Make request with query parameters
    response = client.get(f'/api/tree_data?page={custom_page}&per_page={custom_per_page}')

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["pagination"]["current_page"] == custom_page
    assert json_data["pagination"]["per_page"] == custom_per_page
    
    mock_get_tree_data_db.assert_called_once_with(g.db, active_tree_id_in_g, custom_page, custom_per_page, default_sort_by, default_sort_order)
    mock_get_pagination.assert_called_once()


@patch('blueprints.trees.get_pagination_params')
@patch('blueprints.trees.get_tree_data_for_visualization_db')
def test_get_tree_data_endpoint_service_error(mock_get_tree_data_db, mock_get_pagination, client, app):
    """Test endpoint when the service layer raises an exception."""
    page, per_page, sort_by, sort_order = 1, 10, "name", "desc"
    mock_get_pagination.return_value = (page, per_page, sort_by, sort_order)

    # Simulate a generic exception from the service layer
    mock_get_tree_data_db.side_effect = Exception("Service layer error")
    
    active_tree_id_in_g = g.active_tree_id

    response = client.get(f'/api/tree_data?page={page}&per_page={per_page}')

    # Based on default Flask error handling, this should be a 500
    # The actual error message might be generic unless specific error handling is in place
    # that re-raises HTTPExceptions or converts others.
    # The blueprint currently aborts with 500 for non-HTTPExceptions.
    assert response.status_code == 500 
    json_data = response.get_json()
    assert "message" in json_data # Default Flask error JSON has 'message'
    # Check if the message is what your abort(500, "Error fetching tree data...") sets
    # This depends on how Flask serializes the HTTPException description.
    # For a generic Exception, Flask's default handler will take over.
    # If you have custom error handlers, this assertion might need to change.
    # Based on the blueprint's `if not isinstance(e, HTTPException): abort(500, "Error fetching tree data for visualization.")`
    # We expect the description to be part of the response.
    # However, Flask's default error handler for generic exceptions might just return a generic 500 message.
    # For more precise testing, one might want to ensure the custom abort message is returned.
    # This test assumes the abort(500, description) is correctly translated by Flask.
    # A simple check:
    assert "Error fetching tree data for visualization" in json_data.get("message", json_data.get("description", ""))


# Example of how to test if @require_tree_access decorator (or similar) is implicitly tested:
# If g.active_tree_id was not set, and the decorator relies on it, the request might fail
# earlier (e.g. with a 401 or 403 if the decorator handles missing g.active_tree_id by aborting).
# By setting g.active_tree_id in the app fixture, we ensure the decorator "passes" for this aspect.
# If the decorator itself needs more specific testing (e.g. different access levels),
# that would typically be done in dedicated tests for the decorator or by parameterizing these tests.

# Note: If your blueprint's @require_tree_access decorator uses g.db or other
# g properties, ensure they are mocked in the app fixture's @app.before_request.
# For instance, g.db = MagicMock() is good practice.
# g.user = MagicMock() if user authentication is part of the access check.
# The current setup with g.active_tree_id and g.db should cover basic needs.

# To run these tests:
# Ensure Flask and Pytest are installed.
# Navigate to the directory containing `backend` and run `python -m pytest`.
# Make sure __init__.py files are present in 'backend', 'tests', 'blueprints', 'services' folders
# to allow Python to recognize them as packages.
# PYTHONPATH might need to be set to the root of your project if running pytest from elsewhere.
# Example: PYTHONPATH=. python -m pytest backend/tests/blueprints
