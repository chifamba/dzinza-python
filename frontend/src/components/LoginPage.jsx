import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import * as api from '../api';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMessage(null)
    try {
        const response = await api.login(username, password);
        login(response.username);
        setSuccessMessage("Login successful!");
        setTimeout(() => {
            setSuccessMessage(null);
            navigate('/');
        }, 3000);
    } catch (err) {
        if (err.response && err.response.status === 401) {
            setError("Incorrect username or password");
        } else {
            setError(err.response?.data?.error || 'Login failed');
        }
    } finally {
        setLoading(false);
    }
  };
  
  const getErrorMessage = () => {
    if (!error) return null;
    return error;
  };
  
  const isLoading = () => {
    return loading;
  }

  return (
    <div>
      <h1>Login</h1>
      {error && <div className='error-message'>{error}</div>}
      {successMessage && <div className="success-message">{successMessage}</div>}
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
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <button type="submit" disabled={isLoading()}>Login</button>
      </form>
    </div>
  );
}

export default LoginPage;