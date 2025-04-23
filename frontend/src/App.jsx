import React from 'react'; // Import React
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import DashboardPage from './components/DashboardPage';
import EditPersonPage from './components/EditPersonPage';
import EditRelationshipPage from './components/EditRelationshipPage';
import AddPersonPage from './components/AddPersonPage';
import AddRelationshipPage from './components/AddRelationshipPage';
import PrivateRoute from './components/PrivateRoute';
import AdminPage from './components/AdminPage'; // Import AdminPage

// Navigation Component
function Navigation() {
    const { user, logout } = useAuth();

    const handleLogout = async () => {
        try {
            await logout();
            // Navigation to login page is handled within logout function in AuthContext
        } catch (error) {
            console.error('Logout failed from Navigation:', error);
            // Handle logout error display if needed
        }
    };

    return (
        <nav style={{ marginBottom: '20px', paddingBottom: '10px', borderBottom: '1px solid #ccc' }}>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', gap: '15px' }}>
                {/* Public Links */}
                {!user && <li><Link to="/login">Login</Link></li>}
                {!user && <li><Link to="/register">Register</Link></li>}

                {/* Authenticated User Links */}
                {user && <li><Link to="/dashboard">Dashboard</Link></li>}
                {user && <li><Link to="/add-person">Add Person</Link></li>}
                {user && <li><Link to="/add-relationship">Add Relationship</Link></li>}

                {/* Admin Only Link */}
                {user && user.role === 'admin' && (
                    <li><Link to="/admin">Admin Panel</Link></li>
                )}

                {/* Logout Button */}
                {user && (
                    <li style={{ marginLeft: 'auto' }}> {/* Pushes logout to the right */}
                        <span style={{ marginRight: '10px' }}>Welcome, {user.username}!</span>
                        <button onClick={handleLogout}>Logout</button>
                    </li>
                )}
            </ul>
        </nav>
    );
}

// Admin Route Guard Component
function AdminRoute({ children }) {
    const { user, loading } = useAuth();

    if (loading) {
        return <div>Loading authentication...</div>; // Or a spinner
    }

    if (!user) {
        // Not logged in, redirect to login
        return <Navigate to="/login" replace />;
    }

    if (user.role !== 'admin') {
        // Logged in but not admin, redirect to dashboard or show forbidden message
        console.warn("AdminRoute: Access denied for non-admin user.");
        // Option 1: Redirect
         return <Navigate to="/dashboard" replace />;
        // Option 2: Show Forbidden message (less user-friendly)
        // return <div>Access Denied: Administrator privileges required.</div>;
    }

    // User is logged in and is an admin
    return children;
}


// Main App Component
function App() {
    return (
        <AuthProvider>
            <Router>
                <Navigation /> {/* Render navigation */}
                <div style={{ padding: '20px' }}> {/* Add some padding around content */}
                    <Routes>
                        {/* Public Routes */}
                        <Route path="/login" element={<LoginPage />} />
                        <Route path="/register" element={<RegisterPage />} />

                        {/* Authenticated Routes (using PrivateRoute) */}
                        <Route path="/dashboard" element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
                        <Route path="/edit-person/:id" element={<PrivateRoute><EditPersonPage /></PrivateRoute>} />
                        <Route path="/edit-relationship/:id" element={<PrivateRoute><EditRelationshipPage /></PrivateRoute>} />
                        <Route path="/add-person" element={<PrivateRoute><AddPersonPage /></PrivateRoute>} />
                        <Route path="/add-relationship" element={<PrivateRoute><AddRelationshipPage /></PrivateRoute>} />

                         {/* Admin Only Route (using AdminRoute guard) */}
                         <Route path="/admin" element={<AdminRoute><AdminPage /></AdminRoute>} />

                        {/* Default route for authenticated users */}
                        <Route path="/" element={<PrivateRoute><DashboardPage /></PrivateRoute>} />

                         {/* Catch-all for unknown routes (optional) */}
                         <Route path="*" element={<div><h2>404 Not Found</h2><p>The page you requested does not exist.</p><Link to="/dashboard">Go to Dashboard</Link></div>} />

                    </Routes>
                </div>
            </Router>
        </AuthProvider>
    );
}

export default App;
