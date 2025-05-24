import { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import api from '@/api';
import { toast } from '@/components/ui/use-toast';

interface Tree {
  id: string;
  name: string;
  description?: string;
  cover_image_url?: string;
  privacy_settings: {
    visibility: 'public' | 'private' | 'shared';
    shared_with?: string[];
  };
}

interface TreeContextType {
  trees: Tree[];
  activeTree: Tree | null;
  loading: boolean;
  setActiveTree: (treeId: string) => Promise<void>;
  createTree: (data: { name: string; description?: string }) => Promise<void>;
  refreshTrees: () => Promise<void>;
}

const TreeContext = createContext<TreeContextType | undefined>(undefined);

export function TreeProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [trees, setTrees] = useState<Tree[]>([]);
  const [activeTree, setActiveTreeState] = useState<Tree | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshTrees = async () => {
    try {
      const fetchedTrees = await api.getUserTrees();
      setTrees(fetchedTrees);
      
      // Update active tree if it exists in the new tree list
      if (user?.active_tree_id) {
        const active = fetchedTrees.find(t => t.id === user.active_tree_id);
        setActiveTreeState(active || null);
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load trees",
      });
    }
  };

  useEffect(() => {
    if (user) {
      refreshTrees();
    }
    setLoading(false);
  }, [user]);

  const setActiveTree = async (treeId: string) => {
    try {
      await api.setActiveTree(treeId);
      const tree = trees.find(t => t.id === treeId);
      if (tree) {
        setActiveTreeState(tree);
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to set active tree",
      });
    }
  };

  const createTree = async (data: { name: string; description?: string }) => {
    try {
      const newTree = await api.createTree(data);
      await refreshTrees();
      await setActiveTree(newTree.id);
      toast({
        title: "Success",
        description: "Tree created successfully",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to create tree",
      });
    }
  };

  return (
    <TreeContext.Provider
      value={{
        trees,
        activeTree,
        loading,
        setActiveTree,
        createTree,
        refreshTrees,
      }}
    >
      {children}
    </TreeContext.Provider>
  );
}

export function useTree() {
  const context = useContext(TreeContext);
  if (context === undefined) {
    throw new Error('useTree must be used within a TreeProvider');
  }
  return context;
}
