import React, { useState, useMemo } from 'react';
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ActivityEvent, ActivityType } from '@/lib/types';
import { ActivityFilters } from './ActivityFilters';

export interface ActivityFeedProps {
  activities: ActivityEvent[];
  className?: string;
}

export function ActivityFeed({ activities, className }: ActivityFeedProps) {
  const [selectedTypes, setSelectedTypes] = useState<ActivityType[]>([]);
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Filter activities based on selected criteria
  const filteredActivities = useMemo(() => {
    return activities.filter(activity => {
      // Filter by type
      if (selectedTypes.length > 0 && !selectedTypes.includes(activity.type)) {
        return false;
      }

      // Filter by date range
      const activityDate = new Date(activity.timestamp);
      if (startDate && activityDate < startDate) {
        return false;
      }
      if (endDate) {
        const endOfDay = new Date(endDate);
        endOfDay.setHours(23, 59, 59, 999);
        if (activityDate > endOfDay) {
          return false;
        }
      }

      // Filter by search term
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        const { details } = activity;
        
        // Search in person names
        if (details.name?.toLowerCase().includes(searchLower)) {
          return true;
        }
        if (details.person1Name?.toLowerCase().includes(searchLower)) {
          return true;
        }
        if (details.person2Name?.toLowerCase().includes(searchLower)) {
          return true;
        }
        
        // Search in tree names
        if (details.name?.toLowerCase().includes(searchLower)) {
          return true;
        }
        
        return false;
      }

      return true;
    });
  }, [activities, selectedTypes, startDate, endDate, searchTerm]);

  // Helper function to format the activity description
  const getActivityDescription = (activity: ActivityEvent): string => {
    const { type, details } = activity;
    
    switch (type) {
      case 'person_create':
        return `Added person ${details.name || 'Unknown'}`;
      case 'person_update':
        return `Updated person ${details.name || 'Unknown'}`;
      case 'person_delete':
        return `Deleted person ${details.name || 'Unknown'}`;
      case 'relationship_create':
        return `Added relationship between ${details.person1Name || 'Unknown'} and ${details.person2Name || 'Unknown'}`;
      case 'relationship_update':
        return `Updated relationship between ${details.person1Name || 'Unknown'} and ${details.person2Name || 'Unknown'}`;
      case 'relationship_delete':
        return `Deleted relationship between ${details.person1Name || 'Unknown'} and ${details.person2Name || 'Unknown'}`;
      case 'tree_create':
        return `Created tree "${details.name || 'Unknown'}"`;
      case 'tree_update':
        return `Updated tree "${details.name || 'Unknown'}"`;
      case 'tree_delete':
        return `Deleted tree "${details.name || 'Unknown'}"`;
      case 'tree_share':
        return `Shared tree "${details.name || 'Unknown'}" with ${details.sharedWith || 'someone'}`;
      case 'tree_settings':
        return `Updated settings for tree "${details.name || 'Unknown'}"`;
      default:
        return 'Unknown activity';
    }
  };

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>See what's happening in your family tree</CardDescription>
        <ActivityFilters 
          selectedTypes={selectedTypes}
          startDate={startDate}
          endDate={endDate}
          searchTerm={searchTerm}
          onTypeChange={setSelectedTypes}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          onSearchChange={setSearchTerm}
        />
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-4">
            {filteredActivities.map((activity, index) => (
              <div
                key={`${activity.timestamp}-${index}`}
                className="flex items-start gap-4 rounded-lg border p-4"
              >
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {getActivityDescription(activity)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {new Date(activity.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
            {filteredActivities.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-4">
                {activities.length === 0 ? 'No recent activity to show' : 'No activities match your filters'}
              </p>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
