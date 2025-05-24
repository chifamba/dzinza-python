import { ActivityEvent, ActivityType } from '@/lib/types';
import api from '@/lib/api';

class EventTracker {
  private static instance: EventTracker;
  private eventBuffer: ActivityEvent[] = [];
  private bufferTimeout: NodeJS.Timeout | null = null;
  private currentTreeId: string | null = null;

  private constructor() {
    // Private constructor to enforce singleton
  }

  public static getInstance(): EventTracker {
    if (!EventTracker.instance) {
      EventTracker.instance = new EventTracker();
    }
    return EventTracker.instance;
  }

  public setTreeId(treeId: string | null) {
    this.currentTreeId = treeId;
  }

  public async trackActivity(
    type: ActivityType,
    entityId: string,
    details: Record<string, any>
  ) {
    if (!this.currentTreeId) {
      console.error('No active tree set in EventTracker');
      return;
    }

    const activity: ActivityEvent = {
      type,
      entityId,
      details,
      timestamp: new Date().toISOString()
    };

    // Add to buffer
    this.eventBuffer.push(activity);

    // Debounce the flush to avoid too many API calls
    if (this.bufferTimeout) {
      clearTimeout(this.bufferTimeout);
    }

    this.bufferTimeout = setTimeout(() => {
      this.flushBuffer();
    }, 1000); // Flush after 1 second of inactivity

    // Also emit event for real-time updates
    this.emitActivity(activity);
  }

  private async flushBuffer() {
    if (!this.currentTreeId || this.eventBuffer.length === 0) return;

    const eventsToSend = [...this.eventBuffer];
    this.eventBuffer = [];

    try {
      // Send events in batch to the server
      await Promise.all(
        eventsToSend.map(event =>
          api.addActivity(this.currentTreeId!, event)
        )
      );
    } catch (error) {
      console.error('Failed to send activities to server:', error);
      // Put failed events back in the buffer
      this.eventBuffer.unshift(...eventsToSend);
    }
  }

  private emitActivity(activity: ActivityEvent) {
    // Dispatch custom event for real-time updates
    const event = new CustomEvent('familyTreeActivity', {
      detail: activity
    });
    window.dispatchEvent(event);
  }

  // Helper methods for common activities
  public trackPersonCreated(personId: string, name: string) {
    this.trackActivity('person_create', personId, { name });
  }

  public trackPersonUpdated(personId: string, name: string) {
    this.trackActivity('person_update', personId, { name });
  }

  public trackPersonDeleted(personId: string, name: string) {
    this.trackActivity('person_delete', personId, { name });
  }

  public trackRelationshipCreated(
    relationshipId: string,
    person1Name: string,
    person2Name: string
  ) {
    this.trackActivity('relationship_create', relationshipId, {
      person1Name,
      person2Name
    });
  }

  public trackRelationshipUpdated(
    relationshipId: string,
    person1Name: string,
    person2Name: string
  ) {
    this.trackActivity('relationship_update', relationshipId, {
      person1Name,
      person2Name
    });
  }

  public trackRelationshipDeleted(
    relationshipId: string,
    person1Name: string,
    person2Name: string
  ) {
    this.trackActivity('relationship_delete', relationshipId, {
      person1Name,
      person2Name
    });
  }

  public trackTreeCreated(treeId: string, name: string) {
    this.trackActivity('tree_create', treeId, { name });
  }

  public trackTreeUpdated(treeId: string, name: string) {
    this.trackActivity('tree_update', treeId, { name });
  }

  public trackTreeDeleted(treeId: string, name: string) {
    this.trackActivity('tree_delete', treeId, { name });
  }

  public trackTreeShared(treeId: string, name: string, sharedWith: string) {
    this.trackActivity('tree_share', treeId, { name, sharedWith });
  }

  public trackTreeSettings(treeId: string, name: string) {
    this.trackActivity('tree_settings', treeId, { name });
  }

  public destroy(): void {
    if (this.bufferTimeout) {
      clearTimeout(this.bufferTimeout);
    }
    this.flushBuffer();
  }
}

export default EventTracker;
