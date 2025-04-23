import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
// Correct: Use default import for the api object
import api from '../api';

function RegisterPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    // Basic client-side validation
    if (!username.trim()) {
        setError("Username cannot be empty.");
        setLoading(false);
        return;
    }
     if (!password) { // Add password validation if needed (e.g., length)
        setError("Password cannot be empty.");
        setLoading(false);
        return;
    }


    try {
      // Correct: Call the register method on the imported api object
      // Pass username and password directly as arguments if api.register expects them that way
      // Or pass as an object if that's what api.register expects
      await api.register(username, password); // Assuming api.register takes (username, password)

      setSuccessMessage("Registration successful! You can now login.");
      setUsername(''); // Clear form on success
      setPassword('');
      // Redirect to login after a delay
      setTimeout(() => {
        setSuccessMessage(null);
        navigate('/login');
      }, 3000);
    } catch (err) {
       // Improved error handling
       const errorMsg = err.response?.data?.message || err.response?.data?.error || err.message || 'Registration failed. Please try again.';
       setError(errorMsg);
       console.error("Registration error:", err.response || err);
    } finally {
        setLoading(false);
    }
  };

  // Styles for basic layout and feedback
  const styles = {
    container: { maxWidth: '400px', margin: '40px auto', padding: '20px', border: '1px solid #ccc', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
    formGroup: { marginBottom: '15px' },
    label: { display: 'block', marginBottom: '5px' },
    input: { width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box' },
    button: { width: '100%', padding: '10px', border: 'none', borderRadius: '4px', backgroundColor: '#28a745', color: 'white', cursor: 'pointer', fontSize: '1em' },
    buttonDisabled: { backgroundColor: '#aaa', cursor: 'not-allowed' },
    message: { marginBottom: '15px', textAlign: 'center', padding: '10px', border: '1px solid', borderRadius: '4px' },
    errorMessage: { color: 'red', borderColor: 'red', backgroundColor: '#ffebee' },
    successMessage: { color: 'green', borderColor: 'green', backgroundColor: '#d4edda' },
  };


  return (
    <div style={styles.container}>
      <h1>Register</h1>
      {/* Display success or error messages */}
      {successMessage && <div style={{...styles.message, ...styles.successMessage}}>{successMessage}</div>}
      {error && <div style={{...styles.message, ...styles.errorMessage}}>{error}</div>}

      <form onSubmit={handleSubmit}>
        <div style={styles.formGroup}>
          <label htmlFor="username" style={styles.label}>Username:</label>
          <input
            type="text"
            id="username"
            style={styles.input}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={loading}
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
            required
            disabled={loading}
          />
        </div>

        <button
            type="submit"
            style={loading ? {...styles.button, ...styles.buttonDisabled} : styles.button}
            disabled={loading}
        >
            {loading ? 'Registering...' : 'Register'}
        </button>
      </form>
    </div>
  );
}

export default RegisterPage;
