import { useState, useCallback } from 'react';
import { useToast } from "@/components/ui/use-toast";
import api from '@/api';

interface TreeSettings {
  privacy_setting: 'PUBLIC' | 'PRIVATE';
  description?: string;
}

export const useTreeSettings = (treeId: string | null) => {
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const updateTreeSettings = useCallback(async (settings: Partial<TreeSettings>) => {
    if (!treeId) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "No tree selected",
      });
      return;
    }

    setLoading(true);
    try {
      await api.updateTree(treeId, settings);
      toast({
        title: "Success",
        description: "Tree settings updated successfully",
      });
    } catch (error) {
      console.error('Failed to update tree settings:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to update tree settings. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  }, [treeId, toast]);

  return {
    loading,
    updateTreeSettings,
  };
};
