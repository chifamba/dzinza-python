import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login, loading: authLoading } = useAuth();
  const navigate = useNavigate(); // Keep navigate if needed

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(username, password);
      // Navigation is handled within AuthContext
    } catch (err) {
      const errorMsg = err.response?.data?.message || err.message || 'Login failed. Please check your credentials.';
      setError(errorMsg);
      console.error('Login failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const isLoading = loading || authLoading;

  return (
    // Use the form-container class for layout
    <div className="form-container">
      <h1>Login</h1>
      {/* Use message and error-message classes */}
      {error && <div className="message error-message">{error}</div>}

      <form onSubmit={handleSubmit}>
        {/* Use form-group class */}
        <div className="form-group">
          <label htmlFor="username">Username:</label>
          <input
            type="text"
            id="username"
            // Input styles are now global
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password:</label>
          <input
            type="password"
            id="password"
            // Input styles are now global
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>
        <button
            type="submit"
            // Button styles are now global
            disabled={isLoading}
            style={{ width: '100%' }} // Keep width 100% if needed specifically here
        >
          {isLoading ? 'Logging in...' : 'Login'}
        </button>
      </form>
      {/* Link styling is now global */}
      <Link to="/register" style={{ marginTop: '15px', textAlign: 'center', display: 'block' }}>
        Don't have an account? Register here.
      </Link>
    </div>
  );
}

export default LoginPage;
