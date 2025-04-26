TODO List
Database
[x] Update docker-compose.yml to use a PostgreSQL database image.

[x] Configure docker-compose.yml to use a 10GB Persistent Volume Claim (PVC) for PostgreSQL data.

[x] Remove Alembic configurations.

[ ] Implement database replication to improve performance.

Complex Operations
[ ] Partial tree loading. (The get_partial_tree function in services.py is a placeholder.)

[ ] Advanced search and filtering. (The search_people function in services.py has basic filtering, but likely needs enhancement for "advanced" capabilities.)

[x] Define functions to get the relationships and attributes of a person. (The get_person_relationships_and_attributes function in services.py is implemented.)

[x] Tree Traversal:

[x] get_ancestors(db: Session, person_id: int, depth: int): Get the ancestors of a person up to a certain depth. (Implemented with iterative logic, returns list of dicts.)

[x] get_descendants(db: Session, person_id: int, depth: int): Get the descendants of a person up to a certain depth. (Implemented with iterative logic, returns list of dicts.)

[ ] get_extended_family(db: Session, person_id: int, depth: int): Get the extended family of a person up to a certain depth (siblings, cousins, etc). (Placeholder added in services.py.)

[ ] get_related(db: Session, person_id: int, depth: int): Get the related people of a person up to a certain depth (in-laws, step-relations, etc). (Placeholder added in services.py.)

Enhanced Logging and Tracing
[ ] Implement enhanced logging throughout the application. (Basic logging is present, but "enhanced" implies more structured/detailed logging.)

[ ] Enable tracing of application calls end-to-end using correlation IDs. (Not implemented.)

[ ] Support OpenTelemetry type metrics for monitoring. (Not implemented.)

Security
[ ] Implement JWT authentication. (Not implemented; currently uses Flask sessions.)

[ ] Implement Two-factor authentication. (Not implemented.)

[ ] Implement Security audit logging. (Basic file-based audit logging is implemented in src/audit_log.py, but "Security audit logging" might imply a more robust system.)

[x] Implement actual password hashing. (Implemented in user_management.py using bcrypt.)

[x] Implement actual password verification. (Implemented in user_management.py using bcrypt.)

Frontend
[ ] Redesign the dashboard:

[ ] Create personalized dashboard with recent activity feed.

[ ] Implement quick access to favorites.

[ ] Add research suggestions section.

[ ] Create statistics overview for the tree.

[ ] Create tree health overview (e.g., data completeness).

[ ] Add the ability to search for people to create relationships with and create them if not found in search.

[ ] Ensure that people at the same level are horizontally at the same level i.e. a husband and wife at the same level, but above all their children whom are also at the same level.

[ ] Implement tabbed interface for person details.

[ ] Add fields for military service.

[ ] Add fields for education history.

[ ] Add fields for occupation history.

[ ] Implement life event timeline tracking.

[ ] Build timeline visualization component.

[ ] Create media gallery with lightbox.

[ ] Implement relationship view from person perspective.

[ ] Create person merging capability for duplicate detection.

[ ] Add confidence levels for biographical data.

[ ] Create form validation library.

[ ] Implement stepped forms for complex data entry.

[ ] Add autosave functionality.

[ ] Create reusable form components.

[ ] Implement field-level validation and error handling.

[ ] Build form state persistence.

[ ] Implement advanced search form.

[ ] Create filter panels for tree view.

[ ] Add saved searches functionality.

[ ] Implement search suggestions and autocomplete.

[ ] Create relationships based on search results.

[ ] Families or people with the same surname born in the same areas, might be related, offer the option to create a relationship between them.

[ ] Optimize UI for mobile responsiveness.

[ ] Test UI on different mobile devices.

[ ] Optimize performance for mobile devices.

Media management
[ ] Create S3-compatible storage architecture.

[ ] Build media upload functionality with drag-and-drop.

[ ] Create media processing pipeline (validation, virus scan, EXIF extraction).

[ ] Implement thumbnail generation for different resolutions.

[ ] Build media gallery with lightbox.

[ ] Create media organization tools.

[ ] Add face recognition suggestion interface.

[ ] Implement media tagging system.

[ ] Create default image for men, women, boys and girls.

GEDCOM support
[ ] Add GEDCOM import capability. (Not implemented.)

[ ] Implement GEDCOM export functionality. (Not implemented.)

[ ] Create merge strategy for imported data. (Not implemented.)

[ ] Add validation for GEDCOM format compliance. (Not implemented.)

Collaboration
[ ] Implement basic collaboration tools (e.g., shared view). (Not implemented.)

[ ] Add user role and permissions management. (Basic role handling is in user_management.py and decorators in main.py, but full management UI/features are not implemented.)

[ ] Build collaboration history tracking. (Not implemented.)

[ ] Create collaboration notifications. (Not implemented.)

[ ] Research and implement advanced collaboration features (e.g., commenting, shared editing). (Not implemented.)

[ ] Implement user profile management. (Basic user details retrieval is in user_management.py, but full profile management is not implemented.)

[ ] Create user preferences for visualization. (Not implemented.)

[ ] Add favorite/recent people tracking. (Not implemented.)

[ ] Implement notification system for changes. (Not implemented.)

[ ] Create activity feed for tree changes. (Not implemented.)

[ ] Build user activity dashboard. (Not implemented.)

[ ] Add email notifications for important changes. (Not implemented.)

Data Export and Backup
[ ] Create report builder interface. (Not implemented.)

[ ] Implement print layouts for trees. (Not implemented.)

[ ] Add PDF generation for family trees. (Not implemented.)

[ ] Build custom report generation. (Not implemented.)

[ ] Create sharing options for reports. (Not implemented.)

[ ] Implement data export in multiple formats. (Not implemented.)

API Enhancements and Integration
[ ] Implement proper API versioning (/api/v1/...). (Not implemented.)

[ ] Create OpenAPI/Swagger documentation. (Not implemented.)

[ ] Add rate limiting and throttling. (Not implemented.)

[ ] Implement proper error response structure. (Basic Flask error handlers are present, but might need refinement for a consistent API structure.)

[ ] Create webhooks for external system integration. (Not implemented.)

[ ] Add OAuth support for third-party authentication. (Not implemented.)

[ ] Implement public API for approved partners. (Not implemented.)

[ ] Create data sync capabilities. (Not implemented.)

Database
[x] Update app.py to connect to the database. (Implemented.)

[x] Create the database models. (Models are defined in app/models.)

[x] Create the database schema programmatically in app.py. (Implemented using Base.metadata.create_all.)

[x] Create an initial job to populate the database with the base schema and initial structure. This should run once only. (Implemented in db_init.py, but uses placeholder password hashes.)

[x] Add PostgreSQL as the database to the (This task seems incomplete in its description, but PostgreSQL is configured in docker-compose.yml.)

[x] Create User CRUD API endpoints. (Basic GET endpoints are in main.py, but POST, PUT, DELETE are not fully implemented as endpoints.) (Implemented POST, PUT /users/{id}/role, and DELETE endpoints in main.py, calling UserManagement methods.)

[ ] Create Person CRUD API endpoints. (GET and POST endpoints are in main.py, but PUT and DELETE are not fully implemented as endpoints.)

[ ] Create PersonAttribute CRUD API endpoints. (GET endpoints are in main.py, but POST, PUT, DELETE are not fully implemented as endpoints.)

[ ] Create Relationship CRUD API endpoints. (GET endpoints are in main.py, but GET by ID, POST, PUT, DELETE are not fully implemented as endpoints.)

[ ] Create RelationshipAttribute CRUD API endpoints. (GET endpoints are in main.py, but GET by ID, POST, PUT, DELETE are not fully implemented as endpoints.)

[ ] Create Media CRUD API endpoints. (GET endpoints are in main.py, but GET by ID, POST, PUT, DELETE are not fully implemented as endpoints.)

[ ] Create Event CRUD API endpoints. (GET endpoints are in main.py, but GET by ID, POST, PUT, DELETE are not fully implemented as endpoints.)

[ ] Create Source CRUD API endpoints. (GET endpoints are in main.py, but GET by ID, POST, PUT, DELETE are not fully implemented as endpoints.)

[ ] Create Citation CRUD API endpoints. (GET endpoints are in main.py, but GET by ID, POST, PUT, DELETE are not fully implemented as endpoints.)

Backend Services
[x] Refactor db_utils.py to correctly use encryption functions. (Completed.)

[x] Implement get_all_events logic in services.py. (Implemented.)

[x] Implement get_event_by_id logic in services.py. (Implemented.)

[x] Implement create_event logic in services.py. (Implemented.)

[x] Implement update_event logic in services.py. (Implemented.)

[x] Implement delete_event logic in services.py. (Implemented.)

[x] Implement get_all_sources logic in services.py. (Implemented.)

[x] Implement get_source_by_id logic in services.py. (Implemented.)

[x] Implement create_source logic in services.py. (Implemented.)

[x] Implement update_source logic in services.py. (Implemented.)

[x] Implement delete_source logic in services.py. (Implemented.)

[x] Implement get_all_citations logic in services.py. (Implemented.)

[x] Implement get_citation_by_id logic in services.py. (Implemented.)

[x] Implement create_citation logic in services.py. (Implemented.)

[x] Implement update_citation logic in services.py. (Implemented.)

[x] Implement delete_citation logic in services.py. (Implemented.)

[x] Implement create_person_attribute logic in services.py. (Implemented.)

[x] Implement update_person_attribute logic in services.py. (Implemented.)

[x] Implement delete_person_attribute logic in services.py. (Implemented.)

[x] Implement get_relationship_by_id logic in services.py. (Implemented.)

[x] Implement create_relationship logic in services.py. (Implemented.)

[x] Implement update_relationship logic in services.py. (Implemented.)

[x] Implement delete_relationship logic in services.py. (Implemented.)

[x] Implement get_relationship_attribute logic in services.py. (Implemented.)

[x] Implement create_relationship_attribute logic in services.py. (Implemented.)

[x] Implement update_relationship_attribute logic in services.py. (Implemented.)

[x] Implement delete_relationship_attribute logic in services.py. (Implemented.)

[x] Implement get_all_media logic in services.py. (Implemented.)

[x] Implement get_media_by_id logic in services.py. (Implemented.)

[x] Implement create_media logic in services.py. (Implemented.)

[x] Implement update_media logic in services.py. (Implemented.)

[x] Implement delete_media logic in services.py. (Implemented.)

[ ] Implement get_partial_tree logic in services.py. (Placeholder.)

[ ] Implement get_extended_family logic in services.py. (Placeholder added.)

[ ] Implement get_related logic in services.py. (Placeholder added.)

Testing and Reliability
[ ] Create a comprehensive test suite with high coverage. (Tests exist, but coverage needs to be assessed.)

[ ] Implement load testing scripts. (Not implemented.)

[ ] Add automated integration testing. (Integration tests exist, but automation setup like CI/CD is pending.)

[ ] Create stress testing for large tree handling. (Not implemented.)

[ ] Create a GitHub Actions workflow for CI/CD. (Not implemented.)

[ ] Deploy the application to a scalable cloud hosting environment. (Not implemented.)
