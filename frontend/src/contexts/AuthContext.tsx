import { createContext, useContext, useState, useEffect } from 'react';
import api from '@/api';

interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  active_tree_id?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  hasRole: (requiredRole: string | string[]) => boolean;
  checkTreePermission: (treeId: string, requiredPermission: 'view' | 'edit' | 'admin') => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Check session on mount
  useEffect(() => {
    checkSession();
  }, []);

  const checkSession = async () => {
    setLoading(true);
    try {
      const session = await api.getSession();
      if (session && session.user) {
        setUser(session.user);
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error('Session check failed:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    setLoading(true);
    try {
      const response = await api.login(username, password);
      if (response && response.user) {
        setUser(response.user);
      } else {
        throw new Error('Login failed: Invalid response');
      }
    } catch (error) {
      console.error('Login failed:', error);
      setUser(null);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await api.logout();
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
      // Still clear the session on the client side
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const refresh = async () => {
    return checkSession();
  };

  // Check if user has the required role(s)
  const hasRole = (requiredRole: string | string[]) => {
    if (!user) return false;

    if (Array.isArray(requiredRole)) {
      return requiredRole.includes(user.role);
    }
    
    return user.role === requiredRole;
  };

  // Check tree permissions
  const checkTreePermission = async (treeId: string, requiredPermission: 'view' | 'edit' | 'admin'): Promise<boolean> => {
    if (!user) return false;
    
    // Admin users have all permissions
    if (user.role === 'admin') return true;
    
    try {
      const permissions = await api.getTreePermissions(treeId);
      
      if (requiredPermission === 'view') {
        return ['view', 'edit', 'admin'].includes(permissions.permission);
      } else if (requiredPermission === 'edit') {
        return ['edit', 'admin'].includes(permissions.permission);
      } else if (requiredPermission === 'admin') {
        return permissions.permission === 'admin';
      }
      
      return false;
    } catch (error) {
      console.error('Failed to check tree permissions:', error);
      return false;
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      login,
      logout,
      refresh,
      hasRole,
      checkTreePermission
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
