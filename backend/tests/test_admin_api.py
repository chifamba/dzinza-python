import pytest
import json
import uuid
from backend.models import User, RoleOptions

# --- Test Get All Users Endpoint (Admin) ---
def test_get_all_users_as_admin(client, admin_auth_headers, test_user, other_user, admin_user):
    """Admin successfully retrieves all users with pagination and sorting."""
    # Ensure users exist (created by fixtures)
    response = client.get('/api/admin/users?page=1&per_page=2&sort_by=username&sort_order=asc', headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    
    assert 'users' in data
    assert 'pagination' in data
    assert len(data['users']) <= 2 # Could be 1 or 2 depending on total users and sorting
    assert data['pagination']['page'] == 1
    assert data['pagination']['per_page'] == 2
    # Add more specific checks based on expected order if data is predictable
    # For example, if admin_user, other_user, test_user are the only ones, and sorted by username asc
    if len(data['users']) > 0:
      assert data['users'][0]['username'] == admin_user.username # 'admin' usually comes first alphabetically

def test_get_all_users_as_non_admin(client, user_auth_headers):
    """Non-admin user attempts to access all users list."""
    response = client.get('/api/admin/users', headers=user_auth_headers)
    assert response.status_code == 403 # Forbidden

def test_get_all_users_no_auth(client):
    """Attempt to access all users list without authentication."""
    response = client.get('/api/admin/users')
    assert response.status_code == 401 # Unauthorized

def test_get_all_users_pagination_params(client, admin_auth_headers, db_session):
    # Create a few more users for robust pagination testing
    for i in range(5):
        u = User(username=f"pageuser{i}", email=f"page{i}@example.com", hashed_password="hashed", role=RoleOptions.USER)
        db_session.add(u)
    db_session.commit()

    response = client.get('/api/admin/users?page=2&per_page=3', headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data['pagination']['page'] == 2
    assert data['pagination']['per_page'] == 3
    # Check total_pages, total_items based on how many users are in the DB now.


# --- Test Delete User Endpoint (Admin) ---
def test_delete_user_as_admin_success(client, admin_auth_headers, other_user, db_session):
    """Admin successfully deletes another user."""
    user_to_delete_id = str(other_user.id)
    response = client.delete(f'/api/admin/users/{user_to_delete_id}', headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'User deleted successfully'
    assert db_session.query(User).get(user_to_delete_id) is None

def test_delete_non_existent_user_as_admin(client, admin_auth_headers):
    """Admin attempts to delete a non-existent user."""
    non_existent_uuid = str(uuid.uuid4())
    response = client.delete(f'/api/admin/users/{non_existent_uuid}', headers=admin_auth_headers)
    assert response.status_code == 404
    data = response.get_json()
    assert 'User not found' in data['error']

def test_admin_delete_self_forbidden(client, admin_auth_headers, admin_user):
    """Admin attempts to delete their own account."""
    admin_id = str(admin_user.id)
    response = client.delete(f'/api/admin/users/{admin_id}', headers=admin_auth_headers)
    assert response.status_code == 403
    data = response.get_json()
    assert 'Admin users cannot delete their own account' in data['error']

def test_delete_user_as_non_admin(client, user_auth_headers, other_user):
    """Non-admin attempts to delete a user."""
    response = client.delete(f'/api/admin/users/{str(other_user.id)}', headers=user_auth_headers)
    assert response.status_code == 403

# --- Test Set User Role Endpoint (Admin) ---
def test_set_user_role_as_admin_success(client, admin_auth_headers, other_user, db_session):
    """Admin successfully changes another user's role."""
    user_to_change_id = str(other_user.id)
    assert other_user.role == RoleOptions.USER # Initial state

    response = client.put(
        f'/api/admin/users/{user_to_change_id}/role',
        headers=admin_auth_headers,
        json={'role': 'admin'} # Change to admin
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'User role updated successfully'
    assert data['user']['role'] == RoleOptions.ADMIN.value
    
    updated_user = db_session.query(User).get(user_to_change_id)
    assert updated_user.role == RoleOptions.ADMIN

def test_set_user_role_non_existent_user(client, admin_auth_headers):
    """Admin attempts to set role for a non-existent user."""
    non_existent_uuid = str(uuid.uuid4())
    response = client.put(
        f'/api/admin/users/{non_existent_uuid}/role',
        headers=admin_auth_headers,
        json={'role': 'editor'}
    )
    assert response.status_code == 404

def test_set_user_role_missing_role_payload(client, admin_auth_headers, other_user):
    """Admin attempts to set role with missing 'role' in payload."""
    response = client.put(
        f'/api/admin/users/{str(other_user.id)}/role',
        headers=admin_auth_headers,
        json={} # Missing role
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "Missing 'role' in request body" in data['error']


def test_set_user_role_invalid_role_value(client, admin_auth_headers, other_user):
    """Admin attempts to set an invalid role value."""
    response = client.put(
        f'/api/admin/users/{str(other_user.id)}/role',
        headers=admin_auth_headers,
        json={'role': 'super_admin_hacker'} # Invalid role
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "Invalid role specified" in data['error']


def test_admin_set_own_role_forbidden(client, admin_auth_headers, admin_user):
    """Admin attempts to change their own role."""
    admin_id = str(admin_user.id)
    response = client.put(
        f'/api/admin/users/{admin_id}/role',
        headers=admin_auth_headers,
        json={'role': 'user'} # Attempt to demote self
    )
    assert response.status_code == 403
    data = response.get_json()
    assert 'Admin users cannot change their own role' in data['error']

def test_set_user_role_as_non_admin(client, user_auth_headers, other_user):
    """Non-admin attempts to change a user's role."""
    response = client.put(
        f'/api/admin/users/{str(other_user.id)}/role',
        headers=user_auth_headers,
        json={'role': 'admin'}
    )
    assert response.status_code == 403
