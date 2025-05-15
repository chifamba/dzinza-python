import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api'; // Ensure path is correct

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [activeTreeId, setActiveTreeId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // Check session status on initial load
  useEffect(() => {
    let isMounted = true; // Prevent state update if component unmounts quickly
    const checkAuthStatus = async () => {
      try {
        setError(null);
        const sessionData = await api.getSession();
        if (isMounted && sessionData.isAuthenticated && sessionData.user) {
          setUser(sessionData.user);
          setActiveTreeId(sessionData.active_tree_id);
        } else if (isMounted) {
          setUser(null);
          setActiveTreeId(null);
        }
      } catch (error) {
        console.error('Failed to fetch session status:', error);
        if (isMounted) {
            setUser(null);
            setActiveTreeId(null);
            setError(error.response?.data?.message || error.message || 'Failed to get session status');
        }
      } finally {
        // Ensure loading is set to false even if there's an error
        if (isMounted) {
            setLoading(false);
        }
      }
    };

    checkAuthStatus();

    // Cleanup function
    return () => {
        isMounted = false;
    };
  }, []); // Empty dependency array means run once on mount

  const login = async (username, password) => {
    setLoading(true);
    setError(null);
    try {
      const userData = await api.login(username, password);
      if (userData && userData.user) {
        setUser(userData.user);
        setActiveTreeId(userData.user.active_tree_id || null);
        navigate('/dashboard');
      } else {
        throw new Error(userData.message || "Login failed: Invalid response from server.");
      }
    } catch (error) {
      console.error('Login failed in AuthContext:', error);
      setUser(null);
      setActiveTreeId(null);
      setError(error.response?.data?.message || error.message || 'Login failed');
      throw error;
    } finally {
        setLoading(false); // Stop loading after attempt
    }
  };

  const logout = async () => {
     setLoading(true);
     setError(null);
     try {
          await api.logout();
          setUser(null);
          setActiveTreeId(null);
          navigate('/login');
     } catch (error) {
          console.error('API Logout failed:', error);
          setUser(null);
          setActiveTreeId(null);
          setError(error.response?.data?.message || error.message || 'Logout failed');
          navigate('/login');
     } finally {
         setLoading(false); // Stop loading
     }
  };

   // Function to set the active tree
   const selectActiveTree = async (treeId) => {
       setLoading(true); // Indicate loading while setting tree
       setError(null); // Clear previous errors
       try {
           await api.setActiveTree(treeId);
           setActiveTreeId(treeId); // Update local state
       } catch (error) {
           console.error('Failed to set active tree:', error);
           const errorMessage = error.response?.data?.message || error.message || 'Failed to set active tree';
           setError(errorMessage);
           setActiveTreeId(null); // Clear active tree on error
           // Don't throw the error, handle it here
       } finally {
           setLoading(false); // Stop loading
       }
   };


  // Provide state and functions to context consumers
  const value = {
    user,
    activeTreeId,
    loading,
    error,
    login,
    logout,
    selectActiveTree,
    setError
  };

   return (
     <AuthContext.Provider value={value}>
       {children}
     </AuthContext.Provider>
   );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
