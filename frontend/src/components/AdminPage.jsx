import React, { useState, useEffect } from 'react';
import api from '../api'; // Ensure path is correct
import { useAuth } from '../context/AuthContext'; // To check admin role locally

function AdminPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [savingUserId, setSavingUserId] = useState(null); // Track which user is being saved/deleted
  const { user } = useAuth(); // Get current user info from context

  // Define valid roles for the dropdown (should match backend's UserRole enum)
  const validRoles = ['user', 'admin', 'researcher', 'guest']; // Match roles defined in backend/main.py

  // Fetch users when component mounts or user context changes
  useEffect(() => {
    let isMounted = true;
    const fetchUsers = async () => {
      // Double-check if the user is an admin before fetching
      if (user?.role !== 'admin') {
          if (isMounted) {
              setError("Access Denied: You do not have permission to view this page.");
              setLoading(false);
          }
          return;
      }
      setLoading(true);
      setError(null);
      try {
        const fetchedUsers = await api.getAllUsers();
        if (isMounted) {
            // Ensure users is an array and sort alphabetically by username
            const sortedUsers = Array.isArray(fetchedUsers)
                ? fetchedUsers.sort((a, b) => a.username.localeCompare(b.username))
                : [];
            setUsers(sortedUsers);
        }
      } catch (err) {
        console.error("Error fetching users:", err.response || err);
        if (isMounted) {
            const errorMsg = err.response?.data?.message || err.message || "Failed to load users.";
            setError(errorMsg);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchUsers();
    return () => { isMounted = false; };
  }, [user]); // Re-fetch if user context changes (e.g., on login/logout)

  // Handler for deleting a user
  const handleDeleteUser = async (userIdToDelete, usernameToDelete) => {
    // Prevent admin from deleting themselves via UI
    if (user?.id === userIdToDelete) { // Use user.id from context
        alert("Admins cannot delete their own account through this interface.");
        return;
    }

    if (window.confirm(`Are you sure you want to delete user "${usernameToDelete}"? This action cannot be undone.`)) {
      setSavingUserId(userIdToDelete); // Indicate saving/deleting state for this user
      setError(null); // Clear previous errors specific to other operations
      try {
        await api.deleteUser(userIdToDelete);
        // Refresh user list after deletion
        setUsers(prevUsers => prevUsers.filter(u => u.id !== userIdToDelete)); // Filter by user.id
        alert(`User "${usernameToDelete}" deleted successfully.`);
      } catch (err) {
        console.error("Error deleting user:", err.response || err);
        const errorMsg = err.response?.data?.message || err.message || "Failed to delete user.";
        // Display error specific to this operation
        setError(`Error deleting user "${usernameToDelete}": ${errorMsg}`);
      } finally {
          setSavingUserId(null); // Clear saving state
      }
    }
  };

  // Handler for changing a user's role
  const handleRoleChange = async (userIdToChange, usernameToChange, newRole) => {
     // Prevent admin from changing their own role via UI
     if (user?.id === userIdToChange) { // Use user.id from context
         alert("Admins cannot change their own role through this interface.");
         // Revert the dropdown visually by finding the original role
         const originalRole = users.find(u => u.id === userIdToChange)?.role;
         if (originalRole) {
             const selectElement = document.getElementById(`role-select-${userIdToChange}`);
             if (selectElement) selectElement.value = originalRole;
         }
         return;
     }

     // Validate new role
     if (!validRoles.includes(newRole)) {
         setError(`Invalid role selected: ${newRole}`);
         // Optionally revert the dropdown visually
         return;
     }

    setSavingUserId(userIdToChange); // Indicate saving state for this user
    setError(null); // Clear previous errors

    try {
      // api.setUserRole expects userId and role
      await api.setUserRole(userIdToChange, newRole);
      // Update local state to reflect the change immediately
      setUsers(prevUsers =>
        prevUsers.map(u =>
          u.id === userIdToChange ? { ...u, role: newRole } : u // Update user.id and role
        )
      );
      alert(`Role for user "${usernameToChange}" updated to "${newRole}".`);
    } catch (err) {
      console.error("Error updating role:", err.response || err);
      const errorMsg = err.response?.data?.message || err.message || "Failed to update role.";
      setError(`Error updating role for user "${usernameToChange}": ${errorMsg}`);
       // Revert the dropdown visually on error
       const originalRole = users.find(u => u.id === userIdToChange)?.role;
       if (originalRole) {
            const selectElement = document.getElementById(`role-select-${userIdToChange}`);
            if (selectElement) selectElement.value = originalRole;
       }
    } finally {
        setSavingUserId(null); // Clear saving state
    }
  };


  // Render loading state
  if (loading) {
    return <div className="main-content-area card">Loading users...</div>;
  }

  // Render general error state (e.g., access denied or initial fetch failed)
  if (error && users.length === 0) {
    return <div className="main-content-area message error-message">Error: {error}</div>;
  }

  // Render Admin Page content
  return (
    // Use main-content-area padding and card for container style
    <div className="main-content-area card">
      <h1>Admin - User Management</h1>
      {/* Display specific operation errors here */}
      {error && <div className="message error-message" style={{ marginBottom: '1rem' }}>{error}</div>}

      {users.length === 0 && !loading ? (
        <p>No users found.</p>
      ) : (
        <div className="admin-table-container"> {/* Added container for responsiveness */}
            <table> {/* Use global table styles */}
              <thead>
                <tr>
                  <th>User ID</th>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}> {/* Use u.id */}
                    <td data-label="User ID">{u.id}</td> {/* Display u.id */}
                    <td data-label="Username">{u.username}</td>
                    <td data-label="Email">{u.email}</td>
                    <td data-label="Role">
                      {/* Role changer dropdown */}
                      <select
                        id={`role-select-${u.id}`} // Unique ID for each select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, u.username, e.target.value)} // Pass u.id
                        // Disable changing own role or while saving this specific user
                        disabled={user?.id === u.id || savingUserId === u.id}
                        aria-label={`Change role for user ${u.username}`}
                      >
                        {validRoles.map(roleOption => (
                          <option key={roleOption} value={roleOption}>
                            {roleOption.charAt(0).toUpperCase() + roleOption.slice(1)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td data-label="Actions">
                      {/* Delete button - disable deleting self or while saving this specific user */}
                      <button
                        onClick={() => handleDeleteUser(u.id, u.username)} // Pass u.id
                        disabled={user?.id === u.id || savingUserId === u.id}
                        style={{ color: (user?.id === u.id) ? 'grey' : 'var(--color-error-text)', cursor: (user?.id === u.id) ? 'not-allowed' : 'pointer' }}
                        className="secondary-button" // Use secondary button style
                        aria-label={`Delete user ${u.username}`}
                      >
                        {savingUserId === u.id ? '...' : 'Delete'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
        </div>
      )}
    </div>
  );
}

export default AdminPage;
