import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api'; // Ensure path is correct

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [activeTreeId, setActiveTreeId] = useState(null); // State for active tree ID
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
          // Set active tree ID from session data
          setActiveTreeId(sessionData.active_tree_id);
        } else if (isMounted) {
          setUser(null); // Ensure user is null if not authenticated
          setActiveTreeId(null); // Clear active tree if not authenticated
        }
      } catch (error) {
        console.error('Failed to fetch session status:', error);
        if (isMounted) {
            setUser(null); // Assume logged out if session check fails
            setActiveTreeId(null); // Clear active tree on error
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
    setLoading(true); // Indicate loading during login attempt
    try {
      const userData = await api.login(username, password);
      if (userData && userData.user) {
        setUser(userData.user);
        // Set active tree ID from login response if available
        setActiveTreeId(userData.user.active_tree_id || null); // Assuming login response includes active_tree_id
        navigate('/dashboard'); // Redirect after successful login
      } else {
        throw new Error(userData.message || "Login failed: Invalid response from server.");
      }
    } catch (error) {
      console.error('Login failed in AuthContext:', error);
      setUser(null);
      setActiveTreeId(null); // Clear active tree on login failure
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
          setActiveTreeId(null); // Clear active tree on logout
          navigate('/login');
     } catch (error) {
          console.error('API Logout failed:', error);
          setUser(null); // Clear local state even if API fails
          setActiveTreeId(null); // Clear active tree on logout error
          navigate('/login'); // Still navigate to login
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
           // Optionally navigate or refresh data here if needed
           // navigate('/dashboard'); // Example: stay on dashboard but trigger data refresh
       } catch (error) {
           console.error('Failed to set active tree:', error);
           // Decide how to handle this error - maybe clear active tree or show message
           // setActiveTreeId(null); // Option: clear active tree on error
           throw error; // Re-throw for component handling
       } finally {
           setLoading(false); // Stop loading
       }
   };


  // Provide loading state, user, activeTreeId, and functions
  const value = { user, activeTreeId, loading, login, logout, selectActiveTree };

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
