import { ActivityEvent, ActivityType } from '@/lib/types';
import api from '@/lib/api';

/**
 * Handles retrying failed operations with exponential backoff
 */
class RetryManager {
  constructor(
    public readonly maxRetries = 5,
    private readonly baseDelay = 1000,
    private readonly maxDelay = 30000
  ) {}

  calculateDelay(attempt: number): number {
    // Exponential backoff with jitter
    const exponentialDelay = Math.min(
      this.maxDelay,
      this.baseDelay * Math.pow(2, attempt - 1)
    );
    // Add random jitter of up to 25% of the delay
    const jitter = Math.random() * (exponentialDelay * 0.25);
    return exponentialDelay + jitter;
  }
}

class EventTracker {
  private static instance: EventTracker;
  private eventBuffer: ActivityEvent[] = [];
  private bufferTimeout: NodeJS.Timeout | null = null;
  private currentTreeId: string | null = null;
  private retryManager: RetryManager;
  private retryAttempts: Map<string, number> = new Map();
  private maxBufferSize = 1000; // Maximum number of events to store in buffer

  private constructor() {
    this.retryManager = new RetryManager();
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

    // If buffer is too large, remove oldest events
    if (this.eventBuffer.length >= this.maxBufferSize) {
      this.eventBuffer = this.eventBuffer.slice(-Math.floor(this.maxBufferSize * 0.9));
      console.warn('Event buffer was pruned due to size limit');
    }

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
      // Process events in smaller batches to improve reliability
      const batchSize = 50;
      for (let i = 0; i < eventsToSend.length; i += batchSize) {
        const batch = eventsToSend.slice(i, i + batchSize);
        await this.sendEventBatch(batch);

        // Clear retry attempts for successful events
        batch.forEach((event: ActivityEvent) => {
          const eventKey = this.getEventKey(event);
          this.retryAttempts.delete(eventKey);
        });
      }
    } catch (error) {
      console.error('Error in flushBuffer:', error);
      this.handleFailedEvents(eventsToSend);
    }
  }

  private async sendEventBatch(events: ActivityEvent[]) {
    // Try to send each event with individual retry tracking
    await Promise.all(
      events.map(async (event) => {
        const eventKey = this.getEventKey(event);
        const attempts = this.retryAttempts.get(eventKey) || 0;

        try {
          await api.addActivity(this.currentTreeId!, event);
        } catch (error) {
          // Increment retry attempts
          this.retryAttempts.set(eventKey, attempts + 1);
          throw error; // Re-throw to be caught by the caller
        }
      })
    );
  }

  private handleFailedEvents(events: ActivityEvent[]) {
    // Split events into retriable and permanently failed
    const retriableEvents = events.filter(event => {
      const eventKey = this.getEventKey(event);
      const attempts = this.retryAttempts.get(eventKey) || 0;
      return attempts < this.retryManager.maxRetries;
    });

    const failedEvents = events.filter(event => {
      const eventKey = this.getEventKey(event);
      const attempts = this.retryAttempts.get(eventKey) || 0;
      return attempts >= this.retryManager.maxRetries;
    });

    if (failedEvents.length > 0) {
      console.error(
        `Permanently failed to send ${failedEvents.length} events after max retries:`, 
        failedEvents
      );
    }

    if (retriableEvents.length > 0) {
      // Put retriable events back at the start of the buffer
      this.eventBuffer.unshift(...retriableEvents);

      // Schedule retry with exponential backoff
      const maxAttempts = Math.max(
        ...retriableEvents.map(event => this.retryAttempts.get(this.getEventKey(event)) || 0)
      );
      const delay = this.retryManager.calculateDelay(maxAttempts);

      setTimeout(() => this.flushBuffer(), delay);
    }
  }

  private getEventKey(event: ActivityEvent): string {
    return `${event.type}-${event.entityId}-${event.timestamp}`;
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
