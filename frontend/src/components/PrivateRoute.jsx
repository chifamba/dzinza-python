import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const PrivateRoute = ({ children }) => {
  const { user, loading, error } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="main-content-area">
        <div className="loading-spinner">Loading authentication...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="main-content-area">
        <div className="message error-message">Error: {error}</div>
        <Link to="/login">Return to Login</Link>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

export default PrivateRoute;
//     setCreatingTree(true);