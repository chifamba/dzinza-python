# Family Tree Project TODO List - Updated April 27, 2025

## General Tasks
- [ ] Implement database indexing for frequently queried fields.
- [ ] Add validation logic for all models (e.g., enums, required fields).
- [ ] Add error handling for database constraints.
- [ ] Create migration scripts using Alembic.
- [ ] Write unit and integration tests for all CRUD operations and model-specific functionality.

## User Model
- [ ] Implement profile image upload functionality.
- [ ] Add API endpoints to manage user preferences.
- [ ] Implement email verification logic.
- [ ] Add functionality to deactivate users.

## Tree Model
- [ ] Implement CRUD operations for the `Tree` model.
- [ ] Add functionality to manage tree privacy levels.
- [ ] Implement tree sharing using the `TreeAccess` model.
- [ ] Add support for collaborative editing of trees.

## TreeAccess Model
- [ ] Implement functionality to manage access levels for users on specific trees.
- [ ] Log changes to tree access in the `ActivityLog` model.

## Person Model
- [ ] Add functionality to manage custom attributes for people.
- [ ] Implement privacy level enforcement for people.
- [ ] Add logic to determine and update the `is_living` field.
- [ ] Extend search functionality to include custom attributes, privacy levels, and living status.

## Relationship Model
- [ ] Add functionality to manage the `certainty_level` field for relationships.
- [ ] Add functionality to manage custom attributes for relationships.
- [ ] Implement validation to ensure valid relationship types and prevent circular relationships.

## Event Model
- [ ] Add functionality to handle events with date ranges.
- [ ] Add functionality to manage custom attributes for events.
- [ ] Implement privacy level enforcement for events.

## Media Model
- [ ] Implement functionality to upload and manage media files.
- [ ] Add logic to extract metadata for uploaded media.
- [ ] Implement thumbnail generation for media files.
- [ ] Enforce privacy levels for media files.

## Citation Model
- [ ] Add functionality to manage the `confidence_level` field for citations.
- [ ] Add functionality to manage custom attributes for citations.

## ActivityLog Model
- [ ] Implement audit logging for all CRUD operations and significant actions.
- [ ] Add functionality to track changes to entities.

## Additional Tasks
- [ ] Implement advanced tree traversal algorithms for querying relationships.
- [ ] Add caching for frequently accessed data (e.g., tree structures, person details).
- [ ] Implement GEDCOM import/export functionality for tree data.
- [ ] Add support for worker threads to handle background tasks (e.g., media processing, email notifications).
- [ ] Perform final load testing and optimize database queries for performance.
