import React from 'react'; // Import React
import { Navigate, useLocation } from 'react-router-dom';
// Import the custom hook instead of context directly
import { useAuth } from '../context/AuthContext';

const PrivateRoute = ({ children }) => {
  // Use the custom hook to get user and loading state
  const { user, loading } = useAuth();
  const location = useLocation(); // Get current location

  // Show loading indicator while authentication status is being checked
  if (loading) {
    // You can replace this with a more sophisticated loading spinner
    return <div style={{textAlign: 'center', padding: '50px'}}>Loading authentication...</div>;
  }

  // If not loading and no user exists, redirect to login
  if (!user) {
    // Redirect them to the /login page, but save the current location they were
    // trying to go to in the state property. This allows us to send them
    // along to that page after they login, which is a nicer user experience
    // than dropping them off on the home page.
    console.log("PrivateRoute: No user found, redirecting to login.");
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If user is authenticated, render the child components
  return children;
};

export default PrivateRoute;
