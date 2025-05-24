// @/components/auth/TreeOwnerRoute.tsx
import { useAuth } from '@/lib/auth';
import { Navigate, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '@/api';

interface TreeOwnerRouteProps {
  children: React.ReactNode;
  treeId: string;
  requiredPermission: 'view' | 'edit' | 'admin';
}

export function TreeOwnerRoute({ 
  children, 
  treeId, 
  requiredPermission = 'view' 
}: TreeOwnerRouteProps) {
  const { user, loading } = useAuth();
  const location = useLocation();
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [permissionLoading, setPermissionLoading] = useState(true);

  useEffect(() => {
    async function checkTreePermission() {
      if (!user || !treeId) {
        setHasPermission(false);
        setPermissionLoading(false);
        return;
      }

      try {
        // Get tree permissions from API
        const treeData = await api.getTreePermissions(treeId);
        
        // Check if user has required permission level
        if (requiredPermission === 'view' && 
            ['view', 'edit', 'admin'].includes(treeData.permission)) {
          setHasPermission(true);
        } else if (requiredPermission === 'edit' && 
            ['edit', 'admin'].includes(treeData.permission)) {
          setHasPermission(true);
        } else if (requiredPermission === 'admin' && 
            treeData.permission === 'admin') {
          setHasPermission(true);
        } else {
          setHasPermission(false);
        }
      } catch (error) {
        console.error('Failed to check tree permission:', error);
        setHasPermission(false);
      } finally {
        setPermissionLoading(false);
      }
    }

    if (!loading && user) {
      checkTreePermission();
    }
  }, [loading, user, treeId, requiredPermission]);

  if (loading || permissionLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  // If not logged in, redirect to login with return path
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  // If no permission, redirect to dashboard
  if (!hasPermission) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}
