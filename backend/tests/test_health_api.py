import pytest
import json
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
import prometheus_client # Required for /metrics endpoint

# --- Test Health Check Endpoint ---
def test_health_check_success(client, db_session):
    """Test successful health check when DB is responsive."""
    # Ensure the DB session can execute a simple query
    db_session.execute(text("SELECT 1")) 
    db_session.commit()

    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert data['db_status'] == 'connected'
    assert 'version' in data # Assuming version is included

@patch('backend.blueprints.health.get_db_session')
def test_health_check_db_error(mock_get_db_session, client, caplog):
    """Test health check when the database is down or unresponsive."""
    # Configure the mock session to raise an error when execute is called
    mock_session_instance = MagicMock()
    mock_session_instance.execute.side_effect = SQLAlchemyError("Simulated DB connection error")
    mock_get_db_session.return_value.__enter__.return_value = mock_session_instance # For context manager

    response = client.get('/health')
    assert response.status_code == 503 # Service Unavailable
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['db_status'] == 'disconnected'
    assert 'Simulated DB connection error' in data['details']
    assert "Health check DB error" in caplog.text


@patch('backend.blueprints.health.get_session_factory', return_value=None)
def test_health_check_no_session_factory(mock_get_factory, client, caplog):
    """Test health check when session factory is None (DB not initialized)."""
    response = client.get('/health')
    assert response.status_code == 503
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['db_status'] == 'uninitialized'
    assert "Database session factory not initialized" in data['details']
    assert "Health check: Database session factory not initialized." in caplog.text


# --- Test Metrics Endpoint ---
def test_metrics_api_success(client):
    """Test successful retrieval of Prometheus metrics."""
    # This test assumes prometheus_client is installed and working.
    # It doesn't check specific metrics, just that the endpoint works.
    response = client.get('/metrics')
    assert response.status_code == 200
    assert response.content_type == prometheus_client.exposition.CONTENT_TYPE_LATEST
    # Content should be Prometheus metrics format
    assert b'python_info' in response.data # A common default metric

@patch('backend.blueprints.health.prometheus_client', None) # Simulate prometheus_client not being available
def test_metrics_api_prometheus_not_installed(client, caplog):
    """Test /metrics when prometheus_client is not available (simulated)."""
    response = client.get('/metrics')
    assert response.status_code == 501 # Not Implemented
    data = response.get_json()
    assert 'Prometheus client not installed or available' in data['error']
    assert "Prometheus client library is not installed" in caplog.text


@patch('backend.blueprints.health.generate_latest')
def test_metrics_api_generate_latest_error(mock_generate_latest, client, caplog):
    """Test /metrics when generate_latest raises an unexpected exception."""
    mock_generate_latest.side_effect = Exception("Simulated metrics generation error")
    response = client.get('/metrics')
    assert response.status_code == 500 # Internal Server Error
    data = response.get_json()
    assert 'Error generating Prometheus metrics' in data['error']
    assert 'Simulated metrics generation error' in data['details']
    assert "Error generating Prometheus metrics" in caplog.text

