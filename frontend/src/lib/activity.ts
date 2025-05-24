import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import api from '@/lib/api';
import { ActivityEvent } from '@/lib/types';

interface ActivityContextType {
  activities: ActivityEvent[];
  loading: boolean;
  error: string | null;
  addActivity: (activity: ActivityEvent) => void;
}

const ActivityContext = createContext<ActivityContextType | null>(null);

export function ActivityProvider({ children }: { children: React.ReactNode }) {
  const { activeTreeId } = useAuth();
  const [activities, setActivities] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load initial activities
  useEffect(() => {
    let isMounted = true;

    const loadActivities = async () => {
      if (!activeTreeId) {
        if (isMounted) {
          setActivities([]);
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response = await api.getTreeActivities(activeTreeId);
        if (isMounted) {
          setActivities(response.activities || []);
        }
      } catch (error: any) {
        console.error('Failed to load activities:', error);
        if (isMounted) {
          setError(error.response?.data?.message || error.message || 'Failed to load activities');
          setActivities([]);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadActivities();

    return () => { isMounted = false; };
  }, [activeTreeId]);

  // Listen for real-time activity updates
  useEffect(() => {
    const handleActivity = (event: CustomEvent<ActivityEvent>) => {
      setActivities(prev => [event.detail, ...prev].slice(0, 100)); // Keep last 100 activities
    };

    window.addEventListener('familyTreeActivity', handleActivity as EventListener);

    return () => {
      window.removeEventListener('familyTreeActivity', handleActivity as EventListener);
    };
  }, []);

  const addActivity = (activity: ActivityEvent) => {
    setActivities(prev => [activity, ...prev].slice(0, 100)); // Keep last 100 activities
  };

  return (
    <ActivityContext.Provider value={{
      activities,
      loading,
      error,
      addActivity
    }}>
      {children}
    </ActivityContext.Provider>
  );
}

export function useActivity() {
  const context = useContext(ActivityContext);
  if (!context) {
    throw new Error('useActivity must be used within an ActivityProvider');
  }
  return context;
}
