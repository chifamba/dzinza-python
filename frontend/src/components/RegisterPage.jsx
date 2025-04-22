import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';

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

    try {
      await api.register({username, password});
      setSuccessMessage("Registration successful! You can now login.");
      setUsername('');
      setPassword('');
      setTimeout(() => {
        setSuccessMessage(null);
        navigate('/login');
      }, 3000)
    } catch (err) {
      setError({
        type: "error",
        message: err.response?.data?.error || 'Registration failed',
      });
    } finally {
        setLoading(false);
    }
  };

  const getErrorMessage = () => {
    if (!error) return null;
  
    switch (error.type) {
      case 'network':
        return "Network error. Please check your connection.";
      case 'validation':
        return "Invalid input. Please check the fields.";
      default:
        return error.message || "An unexpected error occurred.";
    }
  };

  return (
    <div>
      <h1>Register Page</h1>
      {loading && <div className="loading-message">Loading...</div>}
      {successMessage && <div className="success-message">{successMessage}</div>}
      {error && <div className="error-message">{getErrorMessage()}</div>}
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="username">Username:</label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="password">Password:</label>
          <input type="password" id="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>

        <button type="submit" disabled={loading}>Register</button>
      </form>
    </div>
  );
}

export default RegisterPage;