# Family Tree Project - Organized Task List

## 1. Foundation & Infrastructure

### Database Setup
- [ ] Create migration scripts using Alembic
- [~] Implement database indexing for frequently queried fields (Some basic indexing in models)
- [ ] Design and implement caching strategy for frequently accessed data (Task 3.5)

### Core System Infrastructure
- [x] Add validation logic for all models (enums, required fields)
- [x] Add error handling for database constraints (utils._handle_sqlalchemy_error)
- [ ] Set up worker thread infrastructure for background tasks (Task 3.6 Celery)
- [x] Implement logging framework for system events (structlog)

## 2. Authentication & User Management

### User Model Implementation
- [~] Implement CRUD operations for User model (Register, Login, Get All, Delete, Update Role done. User self-update profile missing - Task 2.15)
- [~] Implement email verification logic (User.email_verified exists, set on pwd reset; no flow on registration)
- [ ] Add API endpoints to manage user preferences (User.preferences field exists; no endpoints - Task 2.15)
- [ ] Add functionality to deactivate users (User.is_active field exists; no service/endpoint)
- [ ] Implement profile image upload functionality (User.profile_image_path exists; no service/endpoint for user profile)
- [x] Add user session management (Flask session)

## 3. Tree Management

### Tree Core Functionality
- [~] Implement CRUD operations for the `Tree` model (Create, Get User Trees done. Update, Delete missing)
- [x] Add functionality to manage tree privacy levels (Tree.privacy_setting, Tree.default_privacy_level - Task 1.9)
- [x] Design and implement tree structure data model (Person, Relationship models)
- [ ] Implement advanced tree traversal algorithms

### Tree Access & Collaboration
- [~] Implement tree sharing using the `TreeAccess` model (Model exists, used in get_user_trees; no sharing/invite endpoints - Task 2.11)
- [ ] Implement functionality to manage access levels for users on specific trees (TreeAccess.access_level exists; no management endpoints - Task 2.11)
- [ ] Add support for collaborative editing of trees (Depends on sharing/access levels - Task 2.11)
- [ ] Log changes to tree access in the `ActivityLog` model

## 4. Core Entity Models

### Person Model
- [x] Implement CRUD operations for Person model
- [x] Add functionality to manage custom attributes for people (Person.custom_attributes, Person.custom_fields - Task 1.4)
- [~] Implement privacy level enforcement for people (Person.privacy_level exists; not fully enforced in GET operations)
- [x] Add logic to determine and update the `is_living` field
- [ ] Implement person merge functionality for duplicate management

### Relationship Model
- [x] Implement CRUD operations for Relationship model
- [x] Add functionality to manage the `certainty_level` field for relationships
- [x] Add functionality to manage custom attributes for relationships
- [~] Implement validation to ensure valid relationship types and prevent circular relationships (Enum, self-relation check done; deeper circular validation missing)
- [ ] Add relationship suggestion algorithm

### Event Model
- [x] Implement CRUD operations for Event model (Task 1.10)
- [x] Add functionality to handle events with date ranges
- [x] Add functionality to manage custom attributes for events
- [~] Implement privacy level enforcement for events (Event.privacy_level exists; not fully enforced in GET)
- [ ] Add support for recurrent events

## 5. Supporting Models

### Media Management
- [x] Implement functionality to upload and manage media files (Upload, Get, Delete for generic media, profile pics, tree covers - Tasks 2.2, 2.3, 2.4)
- [~] Add logic to extract metadata for uploaded media (Basic metadata stored; no advanced extraction e.g. EXIF)
- [ ] Implement thumbnail generation for media files (MediaItem.thumbnail_url is placeholder - Task 2.2 consideration)
- [ ] Enforce privacy levels for media files (No privacy_level field on MediaItem; access via linked entity)
- [x] Add support for different media types (images, documents, audio, video) (MediaTypeEnum)

### Citation Model
- [ ] Implement CRUD operations for Citation model (Model exists; no services/blueprints)
- [ ] Add functionality to manage the `confidence_level` field for citations (Field exists; no CRUD)
- [ ] Add functionality to manage custom attributes for citations (Field exists; no CRUD)
- [ ] Implement source validation functionality

### Activity Tracking
- [ ] Implement audit logging for all CRUD operations and significant actions (ActivityLog model/service exists; no logging calls in CRUD services - Task 2.10)
- [ ] Add functionality to track changes to entities (Depends on audit logging)
- [ ] Create user activity dashboard (Depends on audit logging)
- [ ] Implement notification system for collaborative activities (Tasks 2.8, 2.9 - Notification model/triggers not done)

## 6. Advanced Features

### Search & Discovery
- [~] Implement basic search functionality across all entities (Person search done - Task 2.5; others missing)
- [~] Extend search to include custom attributes, privacy levels, and living status (Person search: living status, custom_fields done - Task 2.6. Privacy level search missing)
- [ ] Add support for fuzzy matching in search
- [~] Implement advanced filtering options (Person filters for dates, gender, custom_fields done - Task 2.6)

### Data Import/Export
- [ ] Implement GEDCOM import functionality (Task 2.14)
- [ ] Implement GEDCOM export functionality (Task 2.13)
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
- [~] Optimize database queries for performance (Some indexing done; deeper optimization not assessed)
- [~] Implement database query monitoring (Basic setup in extensions.py; no specific monitoring tools visible)
- [ ] Add performance benchmarking tools

## 8. Final Steps

### Documentation
- [ ] Create API documentation (Task 5.1 OpenAPI/Swagger)
- [ ] Write user guides
- [~] Document database schema (Models defined; no schema diagram/docs)
- [ ] Create developer onboarding materials

### Deployment
- [ ] Configure deployment pipelines
- [ ] Set up monitoring and alerting
- [ ] Prepare rollback procedures
- [ ] Create maintenance plan

## 9. Code Review Additions
- [x] Implement to_dict method for Event, Media, Citation, and ActivityLog models (Event, MediaItem, ActivityLog done. Citation not applicable as no CRUD)
- [ ] Add unit tests for new decorators: require_auth, require_admin, require_tree_access
- [ ] Add audit logs to ActivityLog for all entity creation/update/delete (Same as item in Section 5)
- [ ] Implement email delivery logic for password reset (currently placeholder in user_service.py)
