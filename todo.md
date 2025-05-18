# Family Tree Project - Organized Task List

## 1. Foundation & Infrastructure

### Database Setup
- [ ] Create migration scripts using Alembic
- [ ] Implement database indexing for frequently queried fields
- [ ] Design and implement caching strategy for frequently accessed data

### Core System Infrastructure
- [x] Add validation logic for all models (enums, required fields)
- [x] Add error handling for database constraints
- [ ] Set up worker thread infrastructure for background tasks
- [x] Implement logging framework for system events

## 2. Authentication & User Management

### User Model Implementation
- [x] Implement CRUD operations for User model
- [x] Implement email verification logic
- [x] Add API endpoints to manage user preferences
- [x] Add functionality to deactivate users
- [x] Implement profile image upload functionality
- [x] Add user session management

## 3. Tree Management

### Tree Core Functionality
- [x] Implement CRUD operations for the `Tree` model
- [x] Add functionality to manage tree privacy levels
- [x] Design and implement tree structure data model
- [ ] Implement advanced tree traversal algorithms

### Tree Access & Collaboration
- [x] Implement tree sharing using the `TreeAccess` model
- [x] Implement functionality to manage access levels for users on specific trees
- [x] Add support for collaborative editing of trees
- [ ] Log changes to tree access in the `ActivityLog` model

## 4. Core Entity Models

### Person Model
- [x] Implement CRUD operations for Person model
- [x] Add functionality to manage custom attributes for people
- [x] Implement privacy level enforcement for people
- [x] Add logic to determine and update the `is_living` field
- [ ] Implement person merge functionality for duplicate management

### Relationship Model
- [x] Implement CRUD operations for Relationship model
- [x] Add functionality to manage the `certainty_level` field for relationships
- [x] Add functionality to manage custom attributes for relationships
- [x] Implement validation to ensure valid relationship types and prevent circular relationships
- [ ] Add relationship suggestion algorithm

### Event Model
- [x] Implement CRUD operations for Event model
- [x] Add functionality to handle events with date ranges
- [x] Add functionality to manage custom attributes for events
- [x] Implement privacy level enforcement for events
- [ ] Add support for recurrent events

## 5. Supporting Models

### Media Management
- [x] Implement functionality to upload and manage media files
- [x] Add logic to extract metadata for uploaded media
- [ ] Implement thumbnail generation for media files
- [x] Enforce privacy levels for media files
- [x] Add support for different media types (images, documents, audio, video)

### Citation Model
- [x] Implement CRUD operations for Citation model
- [x] Add functionality to manage the `confidence_level` field for citations
- [x] Add functionality to manage custom attributes for citations
- [ ] Implement source validation functionality

### Activity Tracking
- [ ] Implement audit logging for all CRUD operations and significant actions
- [ ] Add functionality to track changes to entities
- [ ] Create user activity dashboard
- [ ] Implement notification system for collaborative activities

## 6. Advanced Features

### Search & Discovery
- [ ] Implement basic search functionality across all entities
- [ ] Extend search to include custom attributes, privacy levels, and living status
- [ ] Add support for fuzzy matching in search
- [ ] Implement advanced filtering options

### Data Import/Export
- [ ] Implement GEDCOM import functionality
- [ ] Implement GEDCOM export functionality
- [ ] Add support for CSV import/export
- [ ] Create backup and restore functionality

## 7. Testing & Optimization

### Testing
- [ ] Write unit tests for all models
- [ ] Write integration tests for all CRUD operations
- [ ] Create end-to-end tests for critical user journeys
- [ ] Implement automated test suite

### Performance & Optimization
- [ ] Perform load testing
- [ ] Optimize database queries for performance
- [x] Implement database query monitoring
- [ ] Add performance benchmarking tools

## 8. Final Steps

### Documentation
- [ ] Create API documentation
- [ ] Write user guides
- [ ] Document database schema
- [ ] Create developer onboarding materials

### Deployment
- [ ] Configure deployment pipelines
- [ ] Set up monitoring and alerting
- [ ] Prepare rollback procedures
- [ ] Create maintenance plan

## 9. Code Review Additions
- [ ] Implement to_dict method for Event, Media, Citation, and ActivityLog models
- [ ] Add unit tests for new decorators: require_auth, require_admin, require_tree_access
- [ ] Add audit logs to ActivityLog for all entity creation/update/delete
- [ ] Implement email delivery logic for password reset (currently placeholder)
