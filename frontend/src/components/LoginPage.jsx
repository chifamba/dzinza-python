import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login, loading: authLoading, error: authError } = useAuth();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(username, password);
      // Navigation is handled within AuthContext on successful login
    } catch (err) {
      // Error handling from AuthContext login function is re-thrown
      const errorMsg = err.response?.data?.message || err.message || 'Login failed. Please check your credentials.';
      setError(errorMsg);
      console.error('Login failed:', err.response || err);
    } finally {
      setLoading(false);
    }
  };

  // Determine overall loading state (either local login attempt or initial auth check)
  const isLoading = loading || authLoading;

  return (
    // Use the form-container class for layout
    <div className="form-container">
      <h1>Login</h1>
      {/* Display either local or auth errors */}
      {(error || authError) && (
        <div className="message error-message">{error || authError}</div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Use form-group class */}
        <div className="form-group">
          <label htmlFor="username">Username:</label>
          <input
            type="text"
            id="username"
            // Input styles are now global via index.css
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={isLoading}
            autocomplete="username" // Added autocomplete attribute
          />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password:</label>
          <input
            type="password"
            id="password"
            // Input styles are now global via index.css
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
            autocomplete="current-password" // Added autocomplete attribute
          />
        </div>
        <button
            type="submit"
            // Button styles are now global via index.css
            disabled={isLoading}
            style={{ width: '100%' }} // Keep width 100% if needed specifically here
        >
          {isLoading ? 'Logging in...' : 'Login'}
        </button>
      </form>
      {/* Link styling is now global via index.css */}
      <Link to="/register" style={{ marginTop: '15px', textAlign: 'center', display: 'block' }}>
        Don't have an account? Register here.
      </Link>
       {/* Optional: Add password reset link */}
       {/* <Link to="/request-password-reset" style={{ marginTop: '10px', textAlign: 'center', display: 'block', fontSize: '0.9em' }}>
         Forgot Password?
       </Link> */}
    </div>
  );
}

export default LoginPage;
