import React, { useState, useEffect } from 'react';
import api from '../api'; // Ensure path is correct
import { useAuth } from '../context/AuthContext'; // To check admin role locally

function AdminPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { user } = useAuth(); // Get current user info from context

  // Define valid roles for the dropdown
  const validRoles = ['basic', 'admin']; // Match roles defined in backend/user.py

  // Fetch users when component mounts
  useEffect(() => {
    const fetchUsers = async () => {
      // Double-check if the user is an admin before fetching
      if (user?.role !== 'admin') {
          setError("Access Denied: You do not have permission to view this page.");
          setLoading(false);
          return;
      }
      setLoading(true);
      setError(null);
      try {
        const fetchedUsers = await api.getAllUsers();
        setUsers(fetchedUsers || []); // Ensure users is an array
      } catch (err) {
        const errorMsg = err.response?.data?.message || err.message || "Failed to load users.";
        setError(errorMsg);
        console.error("Error fetching users:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, [user]); // Re-fetch if user context changes (e.g., on login/logout)

  // Handler for deleting a user
  const handleDeleteUser = async (userIdToDelete, usernameToDelete) => {
    // Prevent admin from deleting themselves via UI
    if (user?.user_id === userIdToDelete) {
        alert("Admins cannot delete their own account through this interface.");
        return;
    }

    if (window.confirm(`Are you sure you want to delete user "${usernameToDelete}"? This action cannot be undone.`)) {
      try {
        await api.deleteUser(userIdToDelete);
        // Refresh user list after deletion
        setUsers(prevUsers => prevUsers.filter(u => u.user_id !== userIdToDelete));
        alert(`User "${usernameToDelete}" deleted successfully.`);
      } catch (err) {
        const errorMsg = err.response?.data?.message || err.message || "Failed to delete user.";
        setError(`Error deleting user "${usernameToDelete}": ${errorMsg}`);
        console.error("Error deleting user:", err);
      }
    }
  };

  // Handler for changing a user's role
  const handleRoleChange = async (userIdToChange, usernameToChange, newRole) => {
     // Prevent admin from changing their own role via UI
     if (user?.user_id === userIdToChange) {
         alert("Admins cannot change their own role through this interface.");
         // Optionally revert the dropdown visually if needed
         return;
     }

    try {
      await api.setUserRole(userIdToChange, newRole);
      // Update local state to reflect the change immediately
      setUsers(prevUsers =>
        prevUsers.map(u =>
          u.user_id === userIdToChange ? { ...u, role: newRole } : u
        )
      );
      alert(`Role for user "${usernameToChange}" updated to "${newRole}".`);
    } catch (err) {
      const errorMsg = err.response?.data?.message || err.message || "Failed to update role.";
      setError(`Error updating role for user "${usernameToChange}": ${errorMsg}`);
      console.error("Error updating role:", err);
       // Optionally revert the dropdown visually on error
       // You might need to store the original role temporarily or refetch users
    }
  };


  // Render loading state
  if (loading) {
    return <div>Loading users...</div>;
  }

  // Render error state
  if (error) {
    return <div style={{ color: 'red' }}>Error: {error}</div>;
  }

  // Render Admin Page content
  return (
    <div>
      <h1>Admin - User Management</h1>
      {users.length === 0 ? (
        <p>No users found.</p>
      ) : (
        <table border="1" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th>User ID</th>
              <th>Username</th>
              <th>Role</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id}>
                <td>{u.user_id}</td>
                <td>{u.username}</td>
                <td>
                  {/* Role changer dropdown */}
                  <select
                    value={u.role}
                    onChange={(e) => handleRoleChange(u.user_id, u.username, e.target.value)}
                    disabled={user?.user_id === u.user_id} // Disable changing own role
                  >
                    {validRoles.map(roleOption => (
                      <option key={roleOption} value={roleOption}>
                        {roleOption.charAt(0).toUpperCase() + roleOption.slice(1)}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  {/* Delete button - disable deleting self */}
                  <button
                    onClick={() => handleDeleteUser(u.user_id, u.username)}
                    disabled={user?.user_id === u.user_id}
                    style={{ color: user?.user_id === u.user_id ? 'grey' : 'red' }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default AdminPage;
