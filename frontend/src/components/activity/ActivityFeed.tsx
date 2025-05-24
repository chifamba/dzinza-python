import React, { useState, useEffect } from 'react';
import { Calendar, Filter, Download, Search, Activity, Users, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { format } from 'date-fns';
import api from '@/api';
import { ActivityType } from '@/lib/types';

interface ActivityItem {
  id: string;
  type: ActivityType;
  entityId: string;
  details: Record<string, any>;
  userId: string;
  userName: string;
  timestamp: string;
  relatedEntities?: {
    name: string;
    id: string;
    type: 'person' | 'relationship' | 'tree';
  }[];
}

const ACTIVITY_TYPE_LABELS: Record<ActivityType, string> = {
  person_create: 'Person Created',
  person_update: 'Person Updated',
  person_delete: 'Person Deleted',
  relationship_create: 'Relationship Created',
  relationship_update: 'Relationship Updated',
  relationship_delete: 'Relationship Deleted',
  tree_create: 'Tree Created',
  tree_update: 'Tree Updated',
  tree_delete: 'Tree Deleted',
  tree_share: 'Tree Shared',
  tree_settings: 'Tree Settings Updated',
};

export function ActivityFeed({ treeId }: { treeId: string }) {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'feed' | 'timeline'>('feed');
  
  // Filter states
  const [search, setSearch] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<ActivityType[]>([]);
  const [dateRange, setDateRange] = useState<{
    from: Date | undefined;
    to: Date | undefined;
  }>({
    from: undefined,
    to: undefined,
  });
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);
  
  // Pagination
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  
  const fetchActivities = async (reset = false) => {
    if (reset) {
      setPage(1);
    }
    
    setLoading(true);
    try {
      // Build filter parameters
      const params: Record<string, any> = {
        page: reset ? 1 : page,
        limit: 20,
      };
      
      if (search) {
        params.search = search;
      }
      
      if (selectedTypes.length > 0) {
        params.types = selectedTypes.join(',');
      }
      
      if (dateRange.from) {
        params.fromDate = format(dateRange.from, 'yyyy-MM-dd');
      }
      
      if (dateRange.to) {
        params.toDate = format(dateRange.to, 'yyyy-MM-dd');
      }
      
      if (selectedPersonId) {
        params.personId = selectedPersonId;
      }
      
      const response = await api.getTreeActivities(treeId, params);
      
      if (reset) {
        setActivities(response.activities || []);
      } else {
        setActivities(prev => [...prev, ...(response.activities || [])]);
      }
      
      setHasMore(response.hasMore || false);
    } catch (error) {
      console.error('Failed to fetch activities:', error);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    if (treeId) {
      fetchActivities(true);
    }
  }, [treeId]);
  
  const loadMore = () => {
    setPage(prev => prev + 1);
    fetchActivities();
  };
  
  const resetFilters = () => {
    setSearch('');
    setSelectedTypes([]);
    setDateRange({ from: undefined, to: undefined });
    setSelectedPersonId(null);
    fetchActivities(true);
  };
  
  const exportActivities = async () => {
    try {
      // Build export parameters (similar to filter parameters)
      const params: Record<string, any> = {};
      
      if (search) {
        params.search = search;
      }
      
      if (selectedTypes.length > 0) {
        params.types = selectedTypes.join(',');
      }
      
      if (dateRange.from) {
        params.fromDate = format(dateRange.from, 'yyyy-MM-dd');
      }
      
      if (dateRange.to) {
        params.toDate = format(dateRange.to, 'yyyy-MM-dd');
      }
      
      if (selectedPersonId) {
        params.personId = selectedPersonId;
      }
      
      // Generate and download the export file
      const response = await api.exportTreeActivities(treeId, params);
      
      // Create a download link for the received blob or data
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `tree-${treeId}-activities.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Failed to export activities:', error);
    }
  };
  
  // Render activity content based on type
  const renderActivityContent = (activity: ActivityItem) => {
    const { type, details, userName, timestamp } = activity;
    const time = new Date(timestamp).toLocaleString();
    
    let entityName = details.entityName || 'Unknown';
    let actionText = '';
    
    switch (type) {
      case 'person_create':
        actionText = `created a new person: ${entityName}`;
        break;
      case 'person_update':
        actionText = `updated ${entityName}`;
        break;
      case 'person_delete':
        actionText = `deleted ${entityName}`;
        break;
      case 'relationship_create':
        if (details.person1Name && details.person2Name && details.relationshipType) {
          actionText = `created a relationship: ${details.person1Name} is ${details.relationshipType.replace('_', ' ')} of ${details.person2Name}`;
        } else {
          actionText = 'created a new relationship';
        }
        break;
      case 'relationship_update':
        if (details.person1Name && details.person2Name) {
          actionText = `updated the relationship between ${details.person1Name} and ${details.person2Name}`;
        } else {
          actionText = 'updated a relationship';
        }
        break;
      case 'relationship_delete':
        if (details.person1Name && details.person2Name) {
          actionText = `deleted the relationship between ${details.person1Name} and ${details.person2Name}`;
        } else {
          actionText = 'deleted a relationship';
        }
        break;
      case 'tree_create':
        actionText = `created a new tree: ${details.treeName || 'Unnamed tree'}`;
        break;
      case 'tree_update':
        actionText = `updated tree settings for ${details.treeName || 'this tree'}`;
        break;
      case 'tree_share':
        if (details.sharedWithName) {
          actionText = `shared the tree with ${details.sharedWithName}`;
        } else {
          actionText = 'shared the tree with someone';
        }
        break;
      default:
        actionText = `performed action: ${ACTIVITY_TYPE_LABELS[type] || type}`;
    }
    
    return (
      <div className="flex space-x-4 p-4 border-b border-gray-100">
        <div className="flex-shrink-0">
          <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
            <Activity className="h-5 w-5 text-primary-600" />
          </div>
        </div>
        <div className="flex-grow">
          <p>
            <span className="font-semibold">{userName}</span> {actionText}
          </p>
          <p className="text-sm text-muted-foreground">{time}</p>
          
          {activity.relatedEntities && activity.relatedEntities.length > 0 && (
            <div className="mt-2">
              <p className="text-sm font-medium">Related:</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {activity.relatedEntities.map((entity) => (
                  <span 
                    key={entity.id}
                    className="text-xs bg-gray-100 px-2 py-1 rounded-full"
                  >
                    {entity.name}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {/* Show changed fields for update activities */}
          {(type === 'person_update' || type === 'relationship_update' || type === 'tree_update') && 
            details.changedFields && (
              <div className="mt-2">
                <p className="text-sm font-medium">Changed fields:</p>
                <div className="flex flex-wrap gap-1 mt-1">
                  {details.changedFields.map((field: string) => (
                    <span 
                      key={field}
                      className="text-xs bg-gray-100 px-2 py-1 rounded-full"
                    >
                      {field}
                    </span>
                  ))}
                </div>
              </div>
            )}
        </div>
      </div>
    );
  };
  
  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
        <h2 className="text-2xl font-bold">Activity History</h2>
        <div className="flex space-x-2">
          <Tabs 
            value={viewMode} 
            onValueChange={(value) => setViewMode(value as 'feed' | 'timeline')}
          >
            <TabsList>
              <TabsTrigger value="feed">
                <Activity className="h-4 w-4 mr-2" />
                Feed
              </TabsTrigger>
              <TabsTrigger value="timeline">
                <Clock className="h-4 w-4 mr-2" />
                Timeline
              </TabsTrigger>
            </TabsList>
          </Tabs>
          
          <Button variant="outline" onClick={exportActivities}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>
      
      {/* Filters */}
      <div className="bg-gray-50 p-4 rounded-md space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="font-medium flex items-center">
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </h3>
          <Button variant="ghost" size="sm" onClick={resetFilters}>
            Reset
          </Button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="flex space-x-2">
              <div className="flex-grow">
                <Input
                  placeholder="Search activities..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full"
                  prefix={<Search className="h-4 w-4" />}
                />
              </div>
              <Button 
                variant="secondary" 
                onClick={() => fetchActivities(true)}
              >
                Search
              </Button>
            </div>
          </div>
          
          <div>
            <Select 
              value={selectedTypes.length ? selectedTypes.join(',') : undefined}
              onValueChange={(value) => {
                if (value) {
                  setSelectedTypes(value.split(',') as ActivityType[]);
                } else {
                  setSelectedTypes([]);
                }
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Filter by activity type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All activity types</SelectItem>
                <SelectItem value="person_create,person_update,person_delete">Person activities</SelectItem>
                <SelectItem value="relationship_create,relationship_update,relationship_delete">Relationship activities</SelectItem>
                <SelectItem value="tree_create,tree_update,tree_delete,tree_share,tree_settings">Tree activities</SelectItem>
                {Object.entries(ACTIVITY_TYPE_LABELS).map(([type, label]) => (
                  <SelectItem key={type} value={type}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="w-full justify-start">
                  <Calendar className="mr-2 h-4 w-4" />
                  {dateRange.from ? (
                    dateRange.to ? (
                      <>
                        {format(dateRange.from, 'LLL dd, y')} -{' '}
                        {format(dateRange.to, 'LLL dd, y')}
                      </>
                    ) : (
                      format(dateRange.from, 'LLL dd, y')
                    )
                  ) : (
                    <span>Pick a date range</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <CalendarComponent
                  initialFocus
                  mode="range"
                  defaultMonth={dateRange.from}
                  selected={dateRange}
                  onSelect={(range) => {
                    setDateRange(range || { from: undefined, to: undefined });
                  }}
                  numberOfMonths={2}
                />
                <div className="flex items-center justify-end gap-2 p-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setDateRange({ from: undefined, to: undefined })}
                  >
                    Clear
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => fetchActivities(true)}
                  >
                    Apply
                  </Button>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </div>
      </div>
      
      {/* Activity List or Timeline */}
      <TabsContent value="feed" className="mt-0">
        <div className="bg-white rounded-md shadow">
          {loading && activities.length === 0 ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="mt-2 text-muted-foreground">Loading activities...</p>
            </div>
          ) : activities.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-muted-foreground">No activities found</p>
            </div>
          ) : (
            <div>
              {activities.map((activity) => (
                <div key={activity.id}>
                  {renderActivityContent(activity)}
                </div>
              ))}
              
              {hasMore && (
                <div className="p-4 text-center">
                  <Button
                    variant="outline"
                    onClick={loadMore}
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary mr-2"></div>
                        Loading...
                      </>
                    ) : (
                      'Load More'
                    )}
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </TabsContent>
      
      <TabsContent value="timeline" className="mt-0">
        <div className="bg-white rounded-md shadow p-4">
          {loading && activities.length === 0 ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="mt-2 text-muted-foreground">Loading timeline...</p>
            </div>
          ) : activities.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-muted-foreground">No activities found</p>
            </div>
          ) : (
            <div className="relative">
              {/* Timeline with date grouping */}
              <div className="ml-4 pl-8 border-l-2 border-gray-200">
                {groupActivitiesByDate(activities).map((group) => (
                  <div key={group.date} className="mb-8">
                    <div className="flex items-center mb-4">
                      <div className="absolute -left-2 w-4 h-4 bg-primary rounded-full"></div>
                      <h3 className="font-bold text-lg">{group.date}</h3>
                    </div>
                    <div className="space-y-4">
                      {group.activities.map((activity) => (
                        <div 
                          key={activity.id} 
                          className="bg-gray-50 rounded-md p-4"
                        >
                          {renderActivityContent(activity)}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              
              {hasMore && (
                <div className="text-center mt-4">
                  <Button
                    variant="outline"
                    onClick={loadMore}
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary mr-2"></div>
                        Loading...
                      </>
                    ) : (
                      'Load More'
                    )}
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </TabsContent>
    </div>
  );
}

// Helper function to group activities by date
function groupActivitiesByDate(activities: ActivityItem[]) {
  const groups: { date: string; activities: ActivityItem[] }[] = [];
  
  activities.forEach((activity) => {
    const date = new Date(activity.timestamp).toLocaleDateString(undefined, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
    
    const existingGroup = groups.find((group) => group.date === date);
    
    if (existingGroup) {
      existingGroup.activities.push(activity);
    } else {
      groups.push({
        date,
        activities: [activity],
      });
    }
  });
  
  return groups;
}
