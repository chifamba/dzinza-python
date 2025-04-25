# TODO List

## Database
- [x] Update `docker-compose.yml` to use a PostgreSQL database image.
- [x] Configure `docker-compose.yml` to use a 10GB Persistent Volume Claim (PVC) for PostgreSQL data.
- [x] Remove Alembic configurations.
- [ ] Implement database replication to improve performance.

## Complex Operations
- [ ] Partial tree loading.
- [ ] Advanced search and filtering.
- [ ] Define functions to get the relationships and attributes of a person.
- [x] Tree Traversal:
    -   [x] `get_ancestors(db: Session, person_id: int, depth: int)`: Get the ancestors of a person up to a certain depth.
    -   [x] `get_descendants(db: Session, person_id: int, depth: int)`: Get the descendants of a person up to a certain depth.
    -   [x] `get_extended_family(db: Session, person_id: int, depth: int)`: Get the extended family of a person up to a certain depth (siblings, cousins, etc).
    -   [x] `get_related(db: Session, person_id: int, depth: int)`: Get the related people of a person up to a certain depth (in-laws, step-relations, etc).
- [ ] Partial tree loading.
- [ ] Advanced search and filtering.
- [ ] Define functions to get the relationships and attributes of a person.

## Enhanced Logging and Tracing
- [ ] Implement enhanced logging throughout the application.
- [ ] Enable tracing of application calls end-to-end using correlation IDs. 
- [ ] Support OpenTelemetry type metrics for monitoring.

## Security
- [ ] Implement JWT authentication.
- [ ] Implement Two-factor authentication.
- [ ] Implement Security audit logging.

## Frontend
- [ ] Redesign the dashboard:
    -   [ ] Create personalized dashboard with recent activity feed. <!-- Partially done: basic structure in place, but not the dynamic parts -->
    -   [ ] Implement quick access to favorites. <!-- Partially done: basic structure in place, but not the dynamic parts -->
    -   [ ] Add research suggestions section. <!-- Partially done: basic structure in place, but not the dynamic parts -->
    -   [ ] Create statistics overview for the tree. <!-- Partially done: basic structure in place, but not the dynamic parts -->
    -   [ ] Create tree health overview (e.g., data completeness). <!-- Partially done: basic structure in place, but not the dynamic parts -->
    -   [ ] Add the ability to search for people to create relationships with and create them if not found in search. <!-- Partially done: search bar in place, but not the dynamic parts -->
    -   [ ] Ensure that people at the same level are horizontally at the same level i.e. a husband and wife at the same level, but above all their children whom are also at the same level. <!-- Partially done: structure in place, but not the dynamic parts -->
- [ ] Implement Two-factor authentication.
- [ ] Implement Security audit logging.

## Frontend
- [ ] Redesign the dashboard:
    -   [ ] Create personalized dashboard with recent activity feed. <!-- Partially done: basic structure in place, but not the dynamic parts -->
    -   [ ] Implement quick access to favorites. <!-- Partially done: basic structure in place, but not the dynamic parts -->
    -   [ ] Add research suggestions section. <!-- Partially done: basic structure in place, but not the dynamic parts -->
    -   [ ] Create statistics overview for the tree. <!-- Partially done: basic structure in place, but not the dynamic parts -->
    -   [ ] Create tree health overview (e.g., data completeness). <!-- Partially done: basic structure in place, but not the dynamic parts -->
    -   [ ] Add the ability to search for people to create relationships with and create them if not found in search. <!-- Partially done: search bar in place, but not the dynamic parts -->
    -   [ ] Ensure that people at the same level are horizontally at the same level i.e. a husband and wife at the same level, but above all their children whom are also at the same level. <!-- Partially done: structure in place, but not the dynamic parts -->
- [ ] Implement tabbed interface for person details.
- [ ] Add fields for military service.
- [ ] Add fields for education history.
- [ ] Add fields for occupation history.
- [ ] Implement life event timeline tracking.
- [ ] Build timeline visualization component.
- [ ] Create media gallery with lightbox.
- [ ] Implement relationship view from person perspective.
- [ ] Create person merging capability for duplicate detection.
- [ ] Add confidence levels for biographical data.
- [ ] Create form validation library.
- [ ] Implement stepped forms for complex data entry.
- [ ] Add autosave functionality.
- [ ] Create reusable form components.
- [ ] Implement field-level validation and error handling.
- [ ] Build form state persistence.
- [ ] Implement advanced search form.
- [ ] Create filter panels for tree view.
- [ ] Add saved searches functionality.
- [ ] Implement search suggestions and autocomplete.
- [ ] Create relationships based on search results.
- [ ] Families or people with the same surname born in the same areas, might be related, offer the option to create a relationship between them.
- [ ] Optimize UI for mobile responsiveness.
- [ ] Test UI on different mobile devices.
- [ ] Optimize performance for mobile devices.

## Media management
- [ ] Create S3-compatible storage architecture.
- [ ] Build media upload functionality with drag-and-drop.
- [ ] Create media processing pipeline (validation, virus scan, EXIF extraction).
- [ ] Implement thumbnail generation for different resolutions.
- [ ] Build media gallery with lightbox.
- [ ] Create media organization tools.
- [ ] Add face recognition suggestion interface.
- [ ] Implement media tagging system.
- [ ] Create default image for men, women, boys and girls.

## GEDCOM support
- [ ] Add GEDCOM import capability.
- [ ] Implement GEDCOM export functionality.
- [ ] Create merge strategy for imported data.
- [ ] Add validation for GEDCOM format compliance.

## Collaboration
- [ ] Implement basic collaboration tools (e.g., shared view).
- [ ] Add user role and permissions management.
- [ ] Build collaboration history tracking.
- [ ] Create collaboration notifications.
- [ ] Research and implement advanced collaboration features (e.g., commenting, shared editing).
- [ ] Implement user profile management.
- [ ] Create user preferences for visualization.
- [ ] Add favorite/recent people tracking.
- [ ] Implement notification system for changes.
- [ ] Create activity feed for tree changes.
- [ ] Build user activity dashboard.
- [ ] Add email notifications for important changes.

## Data Export and Backup
- [ ] Create report builder interface.
- [ ] Implement print layouts for trees.
- [ ] Add PDF generation for family trees.
- [ ] Build custom report generation.
- [ ] Create sharing options for reports.
- [ ] Implement data export in multiple formats.

## API Enhancements and Integration
- [ ] Implement proper API versioning (/api/v1/...).
- [ ] Create OpenAPI/Swagger documentation.
- [ ] Add rate limiting and throttling.
- [ ] Implement proper error response structure.
- [ ] Create webhooks for external system integration.
- [ ] Add OAuth support for third-party authentication.
- [ ] Implement public API for approved partners.
- [ ] Create data sync capabilities.

## Database
- [x] Update app.py to connect to the database.
- [x] Create the database models.
- [x] Create the database schema programmatically in app.py.
- [x] Create an initial job to populate the database with the base schema and initial structure. This should run once only.
- [x] Add PostgreSQL as the database to the  
- [x] Create User CRUD API endpoints.
- [x] Create Person CRUD API endpoints.
- [x] Create PersonAttribute CRUD API endpoints.
- [x] Create Relationship CRUD API endpoints.
- [x] Create RelationshipAttribute CRUD API endpoints.
- [x] Create Media CRUD API endpoints.
- [x] Create Event CRUD API endpoints.
- [x] Create Source CRUD API endpoints.
- [x] Create Citation CRUD API endpoints.
## Testing and Reliability
- [ ] Create a comprehensive test suite with high coverage.
- [ ] Implement load testing scripts.
- [ ] Add automated integration testing.
- [ ] Create stress testing for large tree handling.

- [ ] Create a GitHub Actions workflow for CI/CD.
- [ ] Deploy the application to a scalable cloud hosting environment.

