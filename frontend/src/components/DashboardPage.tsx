import React, { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { ActivityEvent } from '@/lib/types';
import { ActivityFeed } from './ActivityFeed';
import { Button } from '@/components/ui/button';
import FamilyDisplay from '@/components/FamilyDisplay';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';

interface Tree {
  id: string;
  name: string;
}

export default function DashboardPage() {
  const { user, activeTreeId, selectActiveTree } = useAuth();
  const [userTrees, setUserTrees] = useState<Tree[]>([]);
  const [loadingTrees, setLoadingTrees] = useState(true);
  const [treesError, setTreesError] = useState<string | null>(null);
  const [creatingTree, setCreatingTree] = useState(false);
  const [newTreeName, setNewTreeName] = useState('');
  const [newTreeError, setNewTreeError] = useState<string | null>(null);
  const [activities, setActivities] = useState<ActivityEvent[]>([]);

  // Fetch user's trees
  useEffect(() => {
    let isMounted = true;
    const fetchUserTrees = async () => {
      if (!user) {
        setUserTrees([]);
        setLoadingTrees(false);
        return;
      }
      setLoadingTrees(true);
      setTreesError(null);
      try {
        const treesData = await api.getUserTrees();
        if (isMounted) {
          setUserTrees(Array.isArray(treesData) ? treesData : []);
        }
      } catch (err) {
        console.error("Failed to fetch user trees:", err);
        if (isMounted) {
          setTreesError("Failed to load your family trees.");
          setUserTrees([]);
        }
      } finally {
        if (isMounted) setLoadingTrees(false);
      }
    };

    fetchUserTrees();
    return () => { isMounted = false; };
  }, [user]);

  // Fetch activities for the current tree
  useEffect(() => {
    let isMounted = true;
    const fetchActivities = async () => {
      if (!activeTreeId) {
        setActivities([]);
        return;
      }
      try {
        const response = await api.getTreeActivities(activeTreeId);
        if (isMounted) {
          setActivities(response.activities || []);
        }
      } catch (err) {
        console.error("Failed to fetch activities:", err);
        if (isMounted) {
          setActivities([]);
        }
      }
    };

    fetchActivities();
    return () => { isMounted = false; };
  }, [activeTreeId]);

  const handleTreeSelect = async (treeId: string) => {
    if (treeId) {
      await selectActiveTree(treeId);
    }
  };

  const handleCreateTree = async () => {
    if (!newTreeName.trim()) {
      setNewTreeError("Tree name cannot be empty.");
      return;
    }
    setCreatingTree(true);
    setNewTreeError(null);
    try {
      const newTree = await api.createTree({ name: newTreeName });
      setUserTrees(prevTrees => [...prevTrees, newTree]);
      await selectActiveTree(newTree.id);
      setNewTreeName('');
    } catch (err) {
      console.error("Failed to create tree:", err);
      const errorMessage = err.response?.data?.message || err.message || "Failed to create tree.";
      setNewTreeError(errorMessage);
    } finally {
      setCreatingTree(false);
    }
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Family Trees</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {loadingTrees ? (
              <p>Loading trees...</p>
            ) : (
              <>
                {treesError && <p className="text-destructive">{treesError}</p>}
                <Select 
                  value={activeTreeId || undefined} 
                  onValueChange={handleTreeSelect}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a tree" />
                  </SelectTrigger>
                  <SelectContent>
                    {userTrees.map(tree => (
                      <SelectItem key={tree.id} value={tree.id}>
                        {tree.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="flex gap-2">
                  <Input
                    placeholder="New tree name"
                    value={newTreeName}
                    onChange={(e) => setNewTreeName(e.target.value)}
                  />
                  <Button onClick={handleCreateTree} disabled={creatingTree}>
                    {creatingTree ? 'Creating...' : 'Create'}
                  </Button>
                </div>
                {newTreeError && <p className="text-destructive">{newTreeError}</p>}
              </>
            )}
          </CardContent>
        </Card>

        {activeTreeId && (
          <FamilyDisplay treeId={activeTreeId} />
        )}

        <ActivityFeed activities={activities} />
      </div>
    </div>
  );
}
