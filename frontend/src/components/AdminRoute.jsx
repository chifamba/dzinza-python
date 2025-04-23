import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext'; // Import useAuth hook

// This component protects routes that require admin privileges
const AdminRoute = ({ children }) => {
    const { user, loading } = useAuth(); // Get user and loading state from context
    const location = useLocation(); // Get current location

    // Show a loading indicator while authentication status is being checked
    if (loading) {
        // You can replace this with a more sophisticated loading spinner component
        return <div style={{textAlign: 'center', padding: '50px'}}>Checking permissions...</div>;
    }

    // If not loading, check if user exists and is an admin
    if (!user) {
        // Not logged in, redirect to login page, preserving the intended destination
        console.log("AdminRoute: No user found, redirecting to login.");
        return <Navigate to="/login" state={{ from: location }} replace />;
    } else if (user.role !== 'admin') {
        // Logged in but not an admin, redirect to the main dashboard
        console.warn(`AdminRoute: Access denied for user '${user.username}' (role: ${user.role}). Redirecting to dashboard.`);
        return <Navigate to="/dashboard" replace />;
        // Alternatively, you could show a dedicated "Forbidden" component:
        // return <div><h2>Access Denied</h2><p>You do not have permission to view this page.</p></div>;
    }

    // User is logged in and is an admin, render the child component(s)
    return children;
};

export default AdminRoute;
