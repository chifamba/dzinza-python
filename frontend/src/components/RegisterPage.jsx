import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom'; // Import Link
// Correct: Use default import for the api object
import api from '../api';

function RegisterPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState(''); // Added email state
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState(''); // Added full name state
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
     if (!email.trim()) {
        setError("Email cannot be empty.");
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
      // Pass username, password, email, and fullName
      await api.register(username, password, email, fullName);

      setSuccessMessage("Registration successful! You can now login.");
      setUsername(''); // Clear form on success
      setEmail('');
      setPassword('');
      setFullName('');
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

  // Removed inline styles and rely on index.css classes
  // const styles = { ... };


  return (
    // Use form-container class
    <div className="form-container">
      <h1>Register</h1>
      {/* Display success or error messages */}
      {successMessage && <div className="message success-message">{successMessage}</div>}
      {error && <div className="message error-message">{error}</div>}

      <form onSubmit={handleSubmit}>
        {/* Use form-group class */}
        <div className="form-group">
          <label htmlFor="username">Username:</label>
          {/* Input uses global styles */}
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={loading}
          />
        </div>
         <div className="form-group">
          <label htmlFor="email">Email:</label>
          <input
            type="email" // Use type="email" for better mobile keyboards and basic validation
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password:</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={loading}
          />
        </div>
         <div className="form-group">
          <label htmlFor="fullName">Full Name (Optional):</label>
          <input
            type="text"
            id="fullName"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            disabled={loading}
          />
        </div>

        <button
            type="submit"
            disabled={loading}
            style={{ width: '100%' }} // Keep width 100% if needed specifically here
        >
            {loading ? 'Registering...' : 'Register'}
        </button>
      </form>
       {/* Link styling is now global */}
      <Link to="/login" style={{ marginTop: '15px', textAlign: 'center', display: 'block' }}>
        Already have an account? Login here.
      </Link>
    </div>
  );
}

export default RegisterPage;
