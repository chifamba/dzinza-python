import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom'; // Added Link
import { AuthContext } from '../context/AuthContext';
// Removed direct api import if login is handled by AuthContext
// import api from '../api';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false); // Use context loading state if preferred
  const { login } = useContext(AuthContext); // Get login function from context
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
        // Call login function from context
        await login(username, password);
        // Navigation is now handled within AuthContext's login function on success
        // No need for success message here as user is redirected
    } catch (err) {
        // Handle errors thrown by the login function in AuthContext
        const errorMsg = err.response?.data?.message || err.message || 'Login failed. Please check your credentials.';
        setError(errorMsg);
        console.error('Login failed:', err);
    } finally {
        setLoading(false);
    }
  };

  // Style object for basic layout (consider using CSS classes)
  const styles = {
    container: {
        maxWidth: '400px',
        margin: '40px auto',
        padding: '20px',
        border: '1px solid #ccc',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    },
    formGroup: {
        marginBottom: '15px',
    },
    label: {
        display: 'block',
        marginBottom: '5px',
    },
    input: {
        width: '100%',
        padding: '8px',
        border: '1px solid #ccc',
        borderRadius: '4px',
        boxSizing: 'border-box', // Include padding in width
    },
    button: {
        width: '100%',
        padding: '10px',
        border: 'none',
        borderRadius: '4px',
        backgroundColor: '#007bff',
        color: 'white',
        cursor: 'pointer',
        fontSize: '1em',
    },
    buttonDisabled: {
        backgroundColor: '#aaa',
        cursor: 'not-allowed',
    },
    errorMessage: {
        color: 'red',
        marginBottom: '15px',
        textAlign: 'center',
        padding: '10px',
        border: '1px solid red',
        borderRadius: '4px',
        backgroundColor: '#ffebee',
    },
     registerLink: {
         marginTop: '15px',
         textAlign: 'center',
         display: 'block',
     }
  };

  return (
    <div style={styles.container}>
      <h1>Login</h1>
      {/* Display error message prominently */}
      {error && <div style={styles.errorMessage}>{error}</div>}

      <form onSubmit={handleSubmit}>
        <div style={styles.formGroup}>
          <label htmlFor="username" style={styles.label}>Username:</label>
          <input
            type="text"
            id="username"
            style={styles.input}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required // Add basic HTML validation
            disabled={loading} // Disable input while loading
          />
        </div>
        <div style={styles.formGroup}>
          <label htmlFor="password" style={styles.label}>Password:</label>
          <input
            type="password"
            id="password"
            style={styles.input}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required // Add basic HTML validation
            disabled={loading} // Disable input while loading
          />
        </div>
        <button
            type="submit"
            style={loading ? {...styles.button, ...styles.buttonDisabled} : styles.button}
            disabled={loading} // Disable button while loading
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
        {/* Link to Register Page */}
        <Link to="/register" style={styles.registerLink}>
            Don't have an account? Register here.
        </Link>
    </div>
  );
}

export default LoginPage;
