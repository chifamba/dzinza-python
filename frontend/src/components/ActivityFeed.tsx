import React from 'react';
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ActivityEvent } from '@/lib/types';

export interface ActivityFeedProps {
  activities: ActivityEvent[];
  className?: string;
}

export function ActivityFeed({ activities, className }: ActivityFeedProps) {
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
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-4">
            {activities.map((activity, index) => (
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
            {activities.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-4">
                No recent activity to show
              </p>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
