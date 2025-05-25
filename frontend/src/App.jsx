import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import DashboardPage from './components/DashboardPage';
import EditPersonPage from './components/EditPersonPage';
import EditRelationshipPage from './components/EditRelationshipPage';
import AddPersonPage from './components/AddPersonPage';
import AddExistingPersonToTreePage from './components/AddExistingPersonToTreePage';
import AddRelationshipPage from './components/AddRelationshipPage';
import PrivateRoute from './components/PrivateRoute';
import AdminPage from './components/AdminPage';
import AdminRoute from './components/AdminRoute';

// Navigation Component
function Navigation() {
    const { user, logout } = useAuth();

    const handleLogout = async () => {
        try {
            await logout();
        } catch (error) {
            console.error('Logout failed from Navigation:', error);
        }
    };

    return (
        // Use app-nav class for styling
        <nav className="app-nav">
            <ul> {/* ul styles handled globally or via app-nav ul */}
                {/* Links use global 'a' styling */}
                {!user && <li><Link to="/login">Login</Link></li>}
                {!user && <li><Link to="/register">Register</Link></li>}

                {user && <li><Link to="/dashboard">Dashboard</Link></li>}
                {/* Add Person/Relationship links are now on the Dashboard page */}
                {/* {user && <li><Link to="/add-person">Add Person</Link></li>} */}
                {/* {user && <li><Link to="/add-relationship">Add Relationship</Link></li>} */}

                {user && user.role === 'admin' && (
                    <li><Link to="/admin">Admin Panel</Link></li>
                )}

                {user && (
                    // Use nav-user-info class for styling
                    <li className="nav-user-info">
                        <span>Welcome, {user.username}!</span>
                        {/* Button uses global styling */}
                        <button onClick={handleLogout}>Logout</button>
                    </li>
                )}
            </ul>
        </nav>
    );
}


// Main App Component
function App() {
    return (
        <Router>
            <AuthProvider>
                {/* Navigation is outside the main content area */}
                <Navigation />
                {/* Use main-content-area for padding and max-width */}
                <main className="main-content-area">
                    <Routes>
                        {/* Public Routes */}
                        <Route path="/login" element={<LoginPage />} />
                        <Route path="/register" element={<RegisterPage />} />
                        {/* Add Password Reset Routes here */}
                        {/* <Route path="/request-password-reset" element={<RequestPasswordResetPage />} /> */}
                        {/* <Route path="/reset-password/:token" element={<ResetPasswordPage />} /> */}


                        {/* Authenticated Routes */}
                        <Route path="/dashboard" element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
                        <Route path="/edit-person/:id" element={<PrivateRoute><EditPersonPage /></PrivateRoute>} />
                        <Route path="/edit-relationship/:id" element={<PrivateRoute><EditRelationshipPage /></PrivateRoute>} />
                        <Route path="/add-person" element={<PrivateRoute><AddPersonPage /></PrivateRoute>} />
                        <Route path="/add-existing-person" element={<PrivateRoute><AddExistingPersonToTreePage /></PrivateRoute>} />
                        <Route path="/add-relationship" element={<PrivateRoute><AddRelationshipPage /></PrivateRoute>} />

                         {/* Admin Only Route */}
                         <Route path="/admin" element={<AdminRoute><AdminPage /></AdminRoute>} />

                        {/* Default route - Redirect to dashboard if authenticated, otherwise login */}
                        <Route path="/" element={<Navigate to="/dashboard" replace />} />


                         {/* Catch-all */}
                         <Route path="*" element={
                             <div style={{ textAlign: 'center', marginTop: '50px' }}>
                                 <h2>404 Not Found</h2>
                                 <p>The page you requested does not exist.</p>
                                 <Link to="/dashboard">Go to Dashboard</Link>
                             </div>
                         } />
                    </Routes>
                </main>
            </AuthProvider>
        </Router>
    );
}

export default App;

