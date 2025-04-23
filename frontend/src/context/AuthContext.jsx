import React, { createContext, useState, useContext, useEffect } from 'react'; // Added React and useEffect
import { useNavigate } from 'react-router-dom';
import api from '../api'; // Assuming api.js is in the parent directory

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // Add loading state
  const navigate = useNavigate();

  // Check session on initial load
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const sessionData = await api.getSession();
        if (sessionData.isAuthenticated && sessionData.user) {
          setUser(sessionData.user);
        }
      } catch (error) {
        console.error('Failed to fetch session status:', error);
        setUser(null); // Assume logged out if session check fails
      } finally {
        setLoading(false); // Done loading
      }
    };
    checkAuthStatus();
  }, []); // Empty dependency array means run once on mount

  const login = async (username, password) => {
    // Added async/await and API call
    try {
      const userData = await api.login(username, password);
      if (userData && userData.user) {
        setUser(userData.user);
        navigate('/dashboard'); // Redirect after successful login
      } else {
           // Handle cases where API returns success but no user data (unexpected)
           throw new Error(userData.message || "Login failed: Invalid response from server.");
      }
    } catch (error) {
      console.error('Login failed in AuthContext:', error);
      setUser(null); // Ensure user is null on login failure
      // Re-throw the error so the component can handle it (e.g., show message)
      throw error;
    }
  };

  const logout = async () => {
     try {
          await api.logout(); // Call API to logout server-side session
          setUser(null);
          navigate('/login'); // Redirect after logout
     } catch (error) {
          console.error('API Logout failed:', error);
          // Still clear local state even if API fails? Decide based on desired UX.
          setUser(null);
          navigate('/login');
     }
  };

  // Provide loading state along with user and functions
  const value = { user, loading, login, logout };

  // Render children only when not loading, or handle loading state within components
  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};