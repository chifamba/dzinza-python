'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '@/lib/api';
import { EventTracker } from '@/services/EventTracker';

interface User {
  id: string;
  username: string;
  email: string;
  role: 'user' | 'admin' | 'researcher' | 'guest';
}

interface AuthContextType {
  user: User | null;
  activeTreeId: string | null;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  selectActiveTree: (treeId: string | null) => Promise<void>;
  setError: (error: string | null) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [user, setUser] = useState<User | null>(null);
  const [activeTreeId, setActiveTreeId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const checkAuthStatus = async () => {
      try {
        setError(null);
        const sessionData = await api.getSession();
        if (isMounted && sessionData.isAuthenticated && sessionData.user) {
          setUser(sessionData.user);
          setActiveTreeId(sessionData.active_tree_id);
          // Initialize EventTracker with the active tree
          EventTracker.getInstance().setTreeId(sessionData.active_tree_id);
        } else if (isMounted) {
          setUser(null);
          setActiveTreeId(null);
          EventTracker.getInstance().setTreeId(null);
        }
      } catch (error: any) {
        console.error('Failed to fetch session status:', error);
        if (isMounted) {
          setUser(null);
          setActiveTreeId(null);
          EventTracker.getInstance().setTreeId(null);
          setError(error.response?.data?.message || error.message || 'Failed to get session status');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    checkAuthStatus();
    return () => { isMounted = false; };
  }, []);

  const login = async (username: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const userData = await api.login(username, password);
      if (userData && userData.user) {
        setUser(userData.user);
        setActiveTreeId(userData.user.active_tree_id || null);
        // Initialize EventTracker with the active tree
        EventTracker.getInstance().setTreeId(userData.user.active_tree_id || null);
      } else {
        throw new Error(userData.message || "Login failed: Invalid response from server.");
      }
    } catch (error: any) {
      setUser(null);
      setActiveTreeId(null);
      EventTracker.getInstance().setTreeId(null);
      setError(error.response?.data?.message || error.message || 'Login failed');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    setError(null);
    try {
      await api.logout();
      setUser(null);
      setActiveTreeId(null);
      EventTracker.getInstance().setTreeId(null);
    } catch (error: any) {
      console.error('API Logout failed:', error);
      setUser(null);
      setActiveTreeId(null);
      EventTracker.getInstance().setTreeId(null);
      setError(error.response?.data?.message || error.message || 'Logout failed');
    } finally {
      setLoading(false);
    }
  };

  const selectActiveTree = async (treeId: string | null) => {
    setLoading(true);
    setError(null);
    try {
      if (treeId) {
        await api.setActiveTree(treeId);
      }
      setActiveTreeId(treeId);
      // Update EventTracker with the new tree ID
      EventTracker.getInstance().setTreeId(treeId);
    } catch (error: any) {
      console.error('Failed to set active tree:', error);
      const errorMessage = error.response?.data?.message || error.message || 'Failed to set active tree';
      setError(errorMessage);
      setActiveTreeId(null);
      EventTracker.getInstance().setTreeId(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      activeTreeId,
      loading,
      error,
      login,
      logout,
      selectActiveTree,
      setError
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
