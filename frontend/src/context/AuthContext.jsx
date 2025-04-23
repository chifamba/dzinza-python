import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api'; // Ensure path is correct

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // Start as true
  const navigate = useNavigate();

  // Check session status on initial load
  useEffect(() => {
    let isMounted = true; // Prevent state update if component unmounts quickly
    const checkAuthStatus = async () => {
      try {
        const sessionData = await api.getSession();
        if (isMounted && sessionData.isAuthenticated && sessionData.user) {
          setUser(sessionData.user);
        } else if (isMounted) {
          setUser(null); // Ensure user is null if not authenticated
        }
      } catch (error) {
        console.error('Failed to fetch session status:', error);
        if (isMounted) {
            setUser(null); // Assume logged out if session check fails
        }
      } finally {
        // *** CRITICAL FIX: Ensure loading is set to false even if there's an error ***
        if (isMounted) {
            setLoading(false);
        }
      }
    };

    // Set loading to true before starting the check
    // setLoading(true); // Already set initially
    checkAuthStatus();

    // Cleanup function
    return () => {
        isMounted = false;
    };
  }, []); // Empty dependency array means run once on mount

  const login = async (username, password) => {
    setLoading(true); // Indicate loading during login attempt
    try {
      const userData = await api.login(username, password);
      if (userData && userData.user) {
        setUser(userData.user);
        navigate('/dashboard'); // Redirect after successful login
      } else {
        throw new Error(userData.message || "Login failed: Invalid response from server.");
      }
    } catch (error) {
      console.error('Login failed in AuthContext:', error);
      setUser(null);
      throw error; // Re-throw for the component to handle
    } finally {
        setLoading(false); // Stop loading after attempt
    }
  };

  const logout = async () => {
     setLoading(true); // Indicate loading during logout
     try {
          await api.logout();
          setUser(null);
          navigate('/login');
     } catch (error) {
          console.error('API Logout failed:', error);
          setUser(null); // Clear local state even if API fails
          navigate('/login');
     } finally {
         setLoading(false); // Stop loading
     }
  };

  // Provide loading state along with user and functions
  const value = { user, loading, login, logout };

  // Render children immediately, let PrivateRoute/AdminRoute handle loading state
  // OR keep the loading check if you prefer showing nothing until auth is checked
  // return (
  //   <AuthContext.Provider value={value}>
  //     {!loading && children}
  //   </AuthContext.Provider>
  // );
  // Simpler approach: Render provider always, let routes manage loading display
   return (
     <AuthContext.Provider value={value}>
       {children}
     </AuthContext.Provider>
   );
};

export const useAuth = () => {
  return useContext(AuthContext);
};
