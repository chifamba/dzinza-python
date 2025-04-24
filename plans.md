## Development Plan for Dzinza Family Tree Application

This document outlines the development plan for the Dzinza Family Tree application, focusing on the backend architecture, database implementation, and key features.

### Key Technologies

*   **Backend:** Python 3.11
*   **Database:** PostgreSQL 
*   **ORM:** SQLAlchemy
*   **Caching:** Redis
*.  **Dev solution will be based on running with docker-compose, the final production solution will use docker with kubernetes

## PostgreSQL Database Implementation

This section details the plan for implementing PostgreSQL as the primary database for the Dzinza Family Tree application.
### Rationale

*   **Relational Model:** PostgreSQL's relational model is well-suited for the complex relationships in family tree data.
*   **Data Integrity:** Constraints, triggers, and other features will ensure data consistency.
*   **Performance:** Indexes, connection pooling, and query optimization will be used to enhance performance.
*   **Scalability:** Techniques like database replication will improve performance and availability.
*   **Data Backup:** Robust backup and restore strategies will be implemented.

### Database Schema

The database schema will consist of the following tables:

*   **Users:** (id, username, password_hash, role, created_at, last_login)
*   **People:** (id, first_name, last_name, nickname, gender, birth_date, death_date, place_of_birth, place_of_death, notes, created_by, created_at, updated_at)
*   **PersonAttributes:** (id, person_id, key, value) - for extensible custom attributes
*   **Relationships:** (id, person1_id, person2_id, rel_type, created_at, updated_at)
*   **RelationshipAttributes:** (id, relationship_id, key, value) - for extensible custom attributes
*   **Media:** (id, person_id, media_type, file_path, title, description, uploaded_at)
*   **Events:** (id, person_id, event_type, date, place, description, created_at)
*   **Sources:** (id, title, author, publication_info, url, notes, created_at)
*   **Citations:** (id, source_id, person_id, event_id, citation_text, page_number, created_at)

### PostgreSQL Configuration

*   We will use a Docker image for our database.
*   We will use 10GB of PVC to store the data.
*   The data will be replicated in another database for improved performance.

## Backend Development

### High-Performance Data Architecture

#### PostgreSQL Optimization

*   Implement connection pooling using pgBouncer with three pools:
    *   20 connections for CRUD operations
    *   50 connections for read-heavy tree traversals
    *   10 connections for admin operations
*   Database schema with advanced indexing:

    


Database Tables

Users table (id, username, password_hash, role, created_at, last_login)
People table (id, first_name, last_name, nickname, gender, birth_date, death_date, place_of_birth, place_of_death, notes, created_by, created_at, updated_at)
PersonAttributes table (id, person_id, key, value) - for extensible custom attributes
Relationships table (id, person1_id, person2_id, rel_type, created_at, updated_at)
RelationshipAttributes table (id, relationship_id, key, value) - for extensible custom attributes
Media table (id, person_id, media_type, file_path, title, description, uploaded_at)
Events table (id, person_id, event_type, date, place, description, created_at)
Sources table (id, title, author, publication_info, url, notes, created_at)
Citations table (id, source_id, person_id, event_id, citation_text, page_number, created_at)


Caching Layer Implementation

Implement Redis for caching frequent queries
Cache common view data (tree data for specific starting points and depths)
Implement TTL (Time-To-Live) based cache invalidation
Create cache refresh triggers on data updates


Data Access Optimization

Implement database connection pooling
Create appropriate database indexes for relationship queries
Optimize query patterns for traversing family trees
Add pagination for all list endpoints



1.2 Tree Traversal and Dynamic View Enhancement

Implement Advanced Tree Traversal

Create core traversal algorithms:

Ancestors traversal (person → ancestors)
Descendants traversal (person → descendants)
Extended family traversal (person → siblings → cousins)
Lateral traversal (in-laws, step-relations)


Implement depth control parameters for all traversals
Add direction-specific traversal (up/down/left/right)


Partial Tree Loading API

Enhance /api/tree_data endpoint to fully implement start_node and depth parameters
Create viewport-based loading with relative coordinates
Implement "fetch more" capability for boundary nodes
Add proximity loading parameters (load n-levels of depth around focus node)


Tree Layout Calculation

Move layout calculation to backend for consistency
Implement horizontal and vertical layout algorithms
Create layout caching for frequently accessed views
Add layout preferences and configurations per user


Performance Metrics & Monitoring

Add instrumentation for query performance
Implement dynamic query optimization based on tree size
Create monitoring endpoints for system health
Add performance logging for analysis



1.3 Genealogy-Specific Features (Ancestry.com parity)

Advanced Person Management

Add fields for military service, education, occupation
Implement life event timeline tracking (beyond birth/death)
Create person merging capability for duplicate detection
Add confidence levels for biographical data


Relationship Enhancement

Add relationship qualifiers (adoptive, step, half, biological)
Implement relationship timeline (marriage date, divorce date)
Create complex relationship detection (cousin calculator)
Add relationship verification status


Source Citation System

Implement source management for genealogical data
Create citation linking to people, events, and relationships
Add support for document uploads and citation
Implement verification levels based on sources


GEDCOM Support

Add GEDCOM import capability
Implement GEDCOM export functionality
Create merge strategy for imported data
Add validation for GEDCOM format compliance


Media Management

Implement media upload functionality
Add storage for photos, documents, audio
Create association between media and people/events
Implement media metadata extraction


Advanced Search & Filtering

Implement soundex and fuzzy name matching
Create advanced search with multiple criteria
Add support for date range searches
Implement location-based searches



1.4 User Experience & Collaboration

User Profiles & Preferences

Implement user profile management
Create user preferences for visualization
Add favorite/recent people tracking
Implement notification system for changes


Tree Sharing & Collaboration

Add granular permissions system
Implement invitation system for tree sharing
Create collaborative editing capability
Add change tracking and history


Activity Tracking

Create activity feed for tree changes
Implement user activity dashboard
Add email notifications for important changes
Create activity reports and analytics


Data Export & Backup

Implement PDF generation for family trees
Add custom report generation
Create automatic backup scheduling
Implement data export in multiple formats



1.5 API Enhancements & Integration

API Versioning & Documentation

Implement proper API versioning (/api/v1/...)
Create OpenAPI/Swagger documentation
Add rate limiting and throttling
Implement proper error response structure


Integration Capabilities

Create webhooks for external system integration
Add OAuth support for third-party authentication
Implement public API for approved partners
Create data sync capabilities


Security Enhancements

Implement JWT for API authentication
Add two-factor authentication
Create security audit logging
Implement data access audit trail


Testing & Reliability

Create comprehensive test suite with high coverage
Implement load testing scripts
Add automated integration testing
Create stress testing for large tree handling



2. Frontend Development Plan
2.1 Core Application Architecture

State Management Enhancement

Replace Context API with Redux/Redux Toolkit
Implement selectors for optimized state access
Create proper action creators and reducers
Add middleware for async operations


Routing & Navigation

Enhance route protection system
Implement route-based code splitting
Create breadcrumb navigation
Add URL-based state persistence


API Communication Layer

Create axios interceptors for auth and error handling
Implement request queuing and batching
Add offline support with request caching
Create retry logic for failed requests


Performance Optimization

Implement React.memo for complex components
Add virtualization for long lists
Create component lazy loading
Implement worker threads for heavy calculations



### Database Implementation (PostgreSQL)

We will be using PostgreSQL as the primary database for our application.

#### Key Features:

*   **Relational Model:** Leverage PostgreSQL's robust relational model to manage our family tree data effectively.
*   **Data Integrity:** Utilize constraints, triggers, and other features to ensure data consistency and accuracy.
*   **Performance:** Optimize database performance with indexes, connection pooling, and query optimization.
* **Scalability:** use techniques to increase the performance of the database, like database replication.
*   **Data Backup:** Implement robust backup and restore strategies to protect against data loss.
*   **Data Migration:** Use a tool like Alembic to manage database schema migrations.
#### PostgreSQL Configuration

* we will use a docker image for our database.
* we will use 10Gb of PVC to store the data.
* The data will be replicated in other database for improved performance.


Backend Implementation Plan (Python 3.11)
1. High-Performance Data Architecture
PostgreSQL Optimization

Implement connection pooling using pgBouncer with 3 pools:

20 connections for CRUD operations




2.2 Family Tree Visualization

React Flow Enhancement

Create custom node types for different person types
Implement custom edge types for relationship types
Add minimap with navigation capability
Create zoom presets and focus functions


Dynamic Loading & Viewport Management

Implement viewport boundary detection
Create "load more" functionality for boundary nodes
Add loading indicators for partial loads
Implement smooth transitions for new data


Layout Options

Create multiple layout views (vertical, horizontal, radial)
Implement collapsible branches
Add focus mode for specific individuals
Create generational visualization


Interactive Elements

Implement hover previews for additional info
Create contextual menus for node actions
Add drag-and-drop relationship creation
Implement pin/favorite for important nodes



2.3 User Interface Components

Dashboard Redesign

Create personalized dashboard with recent activity
Implement quick access to favorites
Add research suggestions
Create statistics and tree health overview


Person Detail View

Implement tabbed interface for person details
Create timeline visualization
Add media gallery with lightbox
Implement relationship view from person perspective


Form Components

Create form validation library
Implement stepped forms for complex data entry
Add autosave functionality
Create reusable form components


Search & Filter Interface

Implement advanced search form
Create filter panels for tree view
Add saved searches functionality
Implement search suggestions and autocomplete



2.4 Advanced Features

Media Management Interface

Create drag-and-drop upload capability
Implement media organization tools
Add face recognition suggestion interface
Create media tagging system


Collaboration Tools

Implement real-time editing indicators
Create comment/discussion system
Add notification center
Implement change review interface


Reports & Printing

Create report builder interface
Implement print layouts for trees
Add PDF export options
Create sharing options for reports


Mobile Optimization

Implement responsive design for all views
Create touch-friendly controls for tree navigation
Add gesture support for common actions
Implement offline capability for mobile



2.5 User Experience Enhancements

Onboarding & Help

Create guided tours for new users
Implement contextual help system
Add tooltips for complex features
Create knowledge base and FAQ


Accessibility

Implement proper ARIA attributes
Create keyboard navigation support
Add high contrast mode
Implement screen reader optimization


Internationalization

Create translation system
Implement locale-specific formatting
Add RTL support for applicable languages
Create culture-specific relationship terms


Theme & Customization

Implement theme system (light/dark/custom)
Create color customization options
Add layout preference persistence
Implement font size adjustments



3. Implementation Phases
Phase 1: Foundation & Performance (Weeks 1-4)

Database migration and schema design
Caching implementation
Tree traversal core algorithms
Partial tree loading API
Frontend state management refactoring
API communication layer enhancement

Phase 2: Core Genealogy Features (Weeks 5-8)

Advanced person management
Relationship enhancements
Dynamic loading & viewport management
Person detail view implementation
Search & filter interface

Phase 3: Collaboration & Media (Weeks 9-12)

Media management system
Source citation implementation
Tree sharing & collaboration
Activity tracking
Collaboration tools in frontend

Phase 4: Advanced Features & Polish (Weeks 13-16)

GEDCOM support
Reports & exports
Mobile optimization
Accessibility implementation
Performance tuning and optimization

4. Testing Strategy
Backend Testing

Unit tests for all service classes
Integration tests for API endpoints
Load testing with simulated large trees
Security penetration testing
Database performance benchmarking

Frontend Testing

Component unit tests with React Testing Library
End-to-end tests with Cypress
Visual regression testing
Performance testing for large trees
Cross-browser compatibility testing

5. Deployment Strategy
Development Environment

Docker containers for backend and frontend
CI/CD pipeline for automated testing
Feature branch deployments
Review apps for PR testing

Production Environment

Scalable cloud hosting (AWS/Azure/GCP)
Database replication for read performance
CDN for static assets
Monitoring and alerting setup
Automated backup system



Backend Implementation Plan (Python 3.11)
1. High-Performance Data Architecture
PostgreSQL Optimization

Implement connection pooling using pgBouncer with 3 pools:

20 connections for CRUD operations

50 connections for read-heavy tree traversals

10 connections for admin operations

Database schema with advanced indexing:

sql
CREATE INDEX idx_people_ancestry ON people USING GIN (ancestry_path gin_btree_ops);
CREATE INDEX idx_relationships_dual ON relationships USING btree (least(person1_id, person2_id), greatest(person1_id, person2_id));
Implement materialized views for common ancestor/descendant paths refreshed every 15 minutes

Caching Strategy

Redis cache layers:

L1: Node cache (LRU, 10k entries, 5min TTL)

L2: Relationship cache (LFU, 50k entries, 1hr TTL)

L3: Tree path cache (ARC, 1k complex queries, 24hr TTL)

Cache invalidation triggers using PostgreSQL NOTIFY/LISTEN

2. Advanced Tree Traversal System
Panning View API

text
GET /api/v1/tree/view?viewport={
  "center_id": "uuid",
  "depth": 3,
  "direction": "ancestor|descendant|lateral",
  "relationships": ["spouse","parent","sibling"],
  "fields": ["basic","events","media"]
}
Response structure:

json
{
  "nodes": [
    { 
      "id": "uuid",
      "data": { /* condensed person data */ },
      "edges": ["uuid1", "uuid2"],
      "position": { "x": 0, "y": 0 } // calculated server-side
    }
  ],
  "links": [
    {
      "id": "uuid",
      "source": "uuid1",
      "target": "uuid2",
      "markers": ["end-arrow"],
      "type": "parent"
    }
  ],
  "pagination": {
    "has_more": true,
    "next_key": "base64encoded_cursor"
  }
}
Traversal Algorithms

Bidirectional BFS for ancestor/descendant paths

Modified A* algorithm for lateral relationship discovery

Bloom filter implementation for quick existence checks

3. Genealogy-Specific Features
Advanced Relationship Model

python
class Relationship(Model):
    REL_TYPES = Enum('REL_TYPES', [
        'BIOLOGICAL_PARENT', 
        'ADOPTIVE_PARENT',
        'STEP_PARENT',
        'FOSTER_PARENT',
        'SURROGATE_PARENT',
        'GUARDIAN',
        'SPOUSE_CURRENT',
        'SPOUSE_FORMER',
        'PARTNER',
        'SIBLING_FULL',
        'SIBLING_HALF'
    ])
    
    start_date = DateTime()
    end_date = DateTime()
    certainty_level = Integer(range=(1,5)) 
    sources = relationship('Citation')
Media Management

S3-compatible storage architecture:

Original files bucket (encrypted at rest)

Thumbnails bucket (multiple resolutions)

Metadata database with EXIF extraction

Media processing pipeline:

text
graph LR
Upload --> Validation --> VirusScan --> EXIF[EXIF Extraction] --> 
ThumbGen[Thumbnail Generation] --> Storage --> Indexing
4. Performance Optimization
Query Optimization Techniques

Pre-materialized ancestor/descendant paths using closure tables

Batch query processing using PostgreSQL array operators

Asynchronous write queue with Redis Streams:

text
XADD writes * operation "update" data "{json}"
XGROUP CREATE writes persist $
Indexing Strategy

Index Type	Columns	Usage Scenario
BRIN	birth_date, death_date	Temporal queries
GIN(JSONB)	custom_attributes	Flexible attribute search
SP-GiST	geography	Location-based queries
Partial	is_alive=true	Living people filters
5. Security & Compliance
JWT Authentication Flow

python
def generate_jwt(user):
    return jwt.encode({
        'sub': user.id,
        'exp': datetime.utcnow() + timedelta(minutes=30),
        '2fa': user.two_factor_enabled,
        'roles': user.roles,
        'tree_access': { /* encrypted ACL */ }
    }, key=SECRET, algorithm='HS512')
Audit System

Immutable audit trail using Merkle trees

Blockchain-style hashing for audit records

GDPR-compliant anonymization pipeline

Frontend Implementation Plan (Node.js/Vite)
1. Viewport Management System
View State Machine

typescript
interface ViewportState {
  centerNode: string;
  viewBounds: {
    x: [number, number];
    y: [number, number];
    zoom: number;
  };
  visibleNodes: string[];
  prefetchNodes: string[];
  layoutType: 'horizontal' | 'vertical' | 'radial';
}

class ViewportManager {
  private debouncedFetch = debounce(this.fetchViewportData, 300);
  
  handlePan(viewport: ViewportState) {
    if(this.needsNewData(viewport)) {
      this.debouncedFetch(viewport);
    }
  }
  
  private async fetchViewportData(state: ViewportState) {
    const response = await api.post('/tree/view', {
      center_id: state.centerNode,
      depth: this.calculateDepth(state.viewBounds),
      direction: this.getPanDirection(state)
    });
    
    this.diffUpdateNodes(response.nodes);
  }
}
2. Rendering Optimization
Virtualization System

tsx
const FamilyTreeCanvas = () => {
  const { nodes, edges } = useViewport();
  
  return (
    <ReactFlow 
      nodes={nodes}
      edges={edges}
      nodeRenderer={({ data }) => (
        <VirtualItem height={150} width={200}>
          <PersonNode {...data} />
        </VirtualItem>
      )}
    />
  );
};
Web Worker Architecture

text
src/workers/
├── layout.worker.ts – Handles node positioning calculations
├── prefetch.worker.ts – Manages data prefetching
└── cache.worker.ts – Manages local IndexedDB cache
3. Search Implementation
Search Query Processor

typescript
const searchProcessor = {
  parse(input: string): SearchQuery {
    // Convert natural language to structured query
    // Example: "born in New York before 1950" becomes
    return {
      filters: [
        { field: 'birth_place', operator: '~', value: 'New York' },
        { field: 'birth_date', operator: '<', value: '1950-01-01' }
      ],
      boost: ['name', 'events']
    };
  }
};
4. Performance Monitoring
Frontend Metrics Collection

typescript
const perfMonitor = new PerformanceMonitor({
  metrics: [
    'nodes-rendered',
    'data-fetch-latency',
    'frame-rate',
    'memory-usage'
  ],
  thresholds: {
    'frame-rate': { warn: 30, crit: 15 },
    'data-fetch-latency': { warn: 500, crit: 1000 }
  }
});
Ancestry Parity Features Implementation
1. Collaborative Editing
Operational Transformation System

python
class TreeOTProcessor:
    def apply_operation(self, current_state, operation):
        # Conflict-free replicated data type (CRDT) implementation
        if operation['type'] == 'add_node':
            return self._handle_add_node(current_state, operation)
        elif operation['type'] == 'update_property':
            return self._handle_property_update(current_state, operation)
2. Source Verification System
text
sequenceDiagram
    Researcher->>Backend: Submit source citation
    Backend->>Verifiers: Notify potential verifiers
    Verifier->>Backend: Submit verification vote
    Backend->>Researcher: Aggregate verification status
    Backend->>Blockchain: Store consensus result
Implementation Roadmap
Phase 1: Core Infrastructure (6 Weeks)
Database migration with zero-downtime strategy

Caching layer implementation

JWT authentication system

Basic tree traversal API

Phase 2: Ancestry Features (12 Weeks)
Media management pipeline

Advanced relationship modeling

Source verification system

GEDCOM import/export

Phase 3: Performance Optimization (8 Weeks)
Query optimizations

Viewport management system

Worker thread implementation

Final load testing