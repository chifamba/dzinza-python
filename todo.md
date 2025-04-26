TODO List
# Family Tree Project TODO List
## General Assumptions

*   **Single File Backend:** All Python backend code will reside in a single file (`app.py`) initially for simplicity. This may be refactored later for better organization.
*   **Frontend:** The frontend is a separate React application.
*   **Database:** PostgreSQL is the chosen database.
*   **Encryption:** Encryption is used for sensitive data at rest.
*   **Authentication:** JWT will be used for authentication, and password hashing is implemented with bcrypt.
*   **Data Models:** Data models are defined as Python classes and are reflected in the database schema.

## Data Models

Each data model must have well-defined attributes, relationships, and validation rules. The tasks below ensure each model is fully implemented and tested.

### User Data Model

*   [ ] Define User data model:    *   Attributes: `user_id` (INT, PK), `username` (VARCHAR, UNIQUE), `email` (VARCHAR, UNIQUE), `password_hash` (VARCHAR), `role` (ENUM: 'user', 'admin'), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP), `last_login` (TIMESTAMP), `is_active` (BOOLEAN).
    *   Relationships: One-to-many with audit logs (user performing actions).
    *   Validation: Username and email uniqueness, password complexity rules.
    *   Encryption: The `password_hash` field stores securely hashed passwords using bcrypt.
*   [ ] Implement User CRUD operations (Create, Read, Update, Delete) via API endpoints.
*   [ ] Implement User registration and authentication.
*   [ ] Implement User role management (admin can modify user roles).

### Person Data Model

*   [ ] Define Person data model:    
    *   Attributes: `person_id` (INT, PK), `first_name` (VARCHAR), `last_name` (VARCHAR), `middle_name` (VARCHAR, nullable), `birth_date` (DATE, nullable), `death_date` (DATE, nullable), `birth_location` (VARCHAR, nullable), `death_location` (VARCHAR, nullable), `gender` (ENUM: 'male', 'female', 'other', nullable), `profile_picture` (VARCHAR, nullable - URL to media), `bio` (TEXT, nullable), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP).
    *   Relationships:
        *   One-to-many with PersonAttribute.
        *   One-to-many with Relationships (as subject and object).
        *   One-to-many with Media.
        *   One-to-many with Events.
    *   Validation: Date format, valid gender values.
*   [ ] Implement Person CRUD operations via API endpoints.
*   [ ] Implement advanced search and filtering for people.

### PersonAttribute Data Model

*   [ ] Define PersonAttribute data model:    
    *   Attributes: `person_attribute_id` (INT, PK), `person_id` (INT, FK to Person), `attribute_type` (VARCHAR), `attribute_value` (TEXT), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP).
    *   Relationships: Many-to-one with Person.
    *   Validation: `attribute_type` must be a valid, predefined type (e.g., 'occupation', 'education').
*   [ ] Implement PersonAttribute CRUD operations via API endpoints.

### Relationship Data Model

*   [ ] Define Relationship data model:    
    *   Attributes: `relationship_id` (INT, PK), `subject_id` (INT, FK to Person), `object_id` (INT, FK to Person), `relationship_type` (VARCHAR), `start_date` (DATE, nullable), `end_date` (DATE, nullable), `description` (TEXT, nullable), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP).
    *   Relationships:
        *   Many-to-one with Person (subject).
        *   Many-to-one with Person (object).
        *   One-to-many with RelationshipAttribute.
    *   Validation: `relationship_type` must be a valid, predefined type (e.g., 'parent', 'child', 'spouse'). Subject and object must be different.
*   [ ] Implement Relationship CRUD operations via API endpoints.

### RelationshipAttribute Data Model

*   [ ] Define RelationshipAttribute data model:    
    *   Attributes: `relationship_attribute_id` (INT, PK), `relationship_id` (INT, FK to Relationship), `attribute_type` (VARCHAR), `attribute_value` (TEXT), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP).
    *   Relationships: Many-to-one with Relationship.
    *   Validation: `attribute_type` must be a valid, predefined type (e.g., 'location', 'notes').
*   [ ] Implement RelationshipAttribute CRUD operations via API endpoints.

### Media Data Model

*   [ ] Define Media data model:    
    *   Attributes: `media_id` (INT, PK), `file_name` (VARCHAR), `file_path` (VARCHAR), `file_type` (VARCHAR), `upload_date` (TIMESTAMP), `description` (TEXT, nullable), `uploader_id` (INT, FK to User), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP).
    *   Relationships:
        *   One-to-many with Person.
        *   Many-to-one with User (uploader).
    *   Validation: `file_type` must be a valid media type (image, video, audio).
*   [ ] Implement Media CRUD operations via API endpoints.
*   [ ] Implement media upload functionality with validation and virus scanning.
*   [ ] Integrate with S3-compatible storage.
*   [ ] Implement thumbnail generation.

### Event Data Model

*   [ ] Define Event data model:    
    *   Attributes: `event_id` (INT, PK), `event_type` (VARCHAR), `event_date` (DATE, nullable), `event_location` (VARCHAR, nullable), `description` (TEXT, nullable), `person_id` (INT, FK to Person), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP).
    *   Relationships: Many-to-one with Person.
    *   Validation: `event_type` must be a valid, predefined type (e.g., 'birth', 'marriage', 'death').
*   [ ] Implement Event CRUD operations via API endpoints.

### Source Data Model

*   [ ] Define Source data model:    
    *   Attributes: `source_id` (INT, PK), `title` (VARCHAR), `author` (VARCHAR, nullable), `publication_date` (DATE, nullable), `location` (VARCHAR, nullable), `source_url` (VARCHAR, nullable), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP).
    *   Relationships: One-to-many with Citation.
    *   Validation: None specific.
*   [ ] Implement Source CRUD operations via API endpoints.

### Citation Data Model

*   [ ] Define Citation data model:    
    *   Attributes: `citation_id` (INT, PK), `source_id` (INT, FK to Source), `person_id` (INT, FK to Person), `citation_text` (TEXT, nullable), `page_number` (VARCHAR, nullable), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP).
    *   Relationships:
        *   Many-to-one with Source.
        *   Many-to-one with Person.
    *   Validation: None specific.
*   [ ] Implement Citation CRUD operations via API endpoints.

## Database

*   [ ] Update docker-compose.yml to use a PostgreSQL database image.
*   [ ] Configure docker-compose.yml to use a 10GB Persistent Volume Claim (PVC) for PostgreSQL data.
*   [ ] Remove Alembic configurations.
*   [ ] Implement database replication to improve performance and availability.  Consider using streaming replication for PostgreSQL.
*   [ ] Update app.py to connect to the database. (Implemented.)
*   [ ] Create the database models. (Models are defined in app/models.)
*   [ ] Create the database schema programmatically in app.py. (Implemented using Base.metadata.create_all.)
*   [ ] Create an initial job to populate the database with the base schema and initial structure. This should run once only. (Implemented in db_init.py, but uses placeholder password hashes.)
*   [ ] Add PostgreSQL as the database to the (This task seems incomplete in its description, but PostgreSQL is configured in docker-compose.yml.)
*   [ ] Create User CRUD API endpoints. (Basic GET endpoints are in main.py, but POST, PUT, DELETE are not fully implemented as endpoints.) (Implemented POST, PUT /users/{id}/role, and DELETE endpoints in main.py, calling UserManagement methods.)
*   [ ] Create Person CRUD API endpoints. (GET and POST endpoints are in main.py, but PUT and DELETE are not fully implemented as endpoints.)
*   [ ] Create PersonAttribute CRUD API endpoints. (GET endpoints are in main.py, but POST, PUT, DELETE are not fully implemented as endpoints.)
*   [ ] Create Relationship CRUD API endpoints. (GET endpoints are in main.py, but GET by ID, POST, PUT, DELETE are not fully implemented as endpoints.)
*   [ ] Create RelationshipAttribute CRUD API endpoints. (GET endpoints are in main.py, but GET by ID, POST, PUT, DELETE are not fully implemented as endpoints.)
*   [ ] Create Media CRUD API endpoints. (GET endpoints are in main.py, but GET by ID, POST, PUT, DELETE are not fully implemented as endpoints.)
*   [ ] Create Event CRUD API endpoints. (GET endpoints are in main.py, but GET by ID, POST, PUT, DELETE are not fully implemented as endpoints.)
*   [ ] Create Source CRUD API endpoints. (GET endpoints are in main.py, but POST, PUT, DELETE are not fully implemented as endpoints.)
*   [ ] Create Citation CRUD API endpoints. (GET endpoints are in main.py, but GET by ID, POST, PUT, DELETE are not fully implemented as endpoints.)

## Complex Operations

*   [ ] Partial tree loading. (The get_partial_tree function in services.py is a placeholder.) Implement efficient loading of tree fragments for performance.
*   [ ] Advanced search and filtering. (The search_people function in services.py has basic filtering, but likely needs enhancement for "advanced" capabilities.) Implement advanced search features, including phonetic search, fuzzy matching, and boolean operators.
*   [ ] Define functions to get the relationships and attributes of a person. (The get_person_relationships_and_attributes function in services.py is implemented.)
*   [ ] Tree Traversal:
    *   [ ] get_ancestors(db: Session, person_id: int, depth: int): Get the ancestors of a person up to a certain depth. (Implemented with iterative logic, returns list of dicts.)
    *   [ ] get_descendants(db: Session, person_id: int, depth: int): Get the descendants of a person up to a certain depth. (Implemented with iterative logic, returns list of dicts.)
    *   [ ] get_extended_family(db: Session, person_id: int, depth: int): Get the extended family of a person up to a certain depth (siblings, cousins, etc). (Placeholder added in services.py.)
    *   [ ] get_related(db: Session, person_id: int, depth: int): Get the related people of a person up to a certain depth (in-laws, step-relations, etc). (Placeholder added in services.py.)

## Enhanced Logging and Tracing

*   [ ] Implement enhanced logging throughout the application. (Basic logging is present, but "enhanced" implies more structured/detailed logging.) Use a structured logging format (e.g., JSON) and include contextual information like user ID and request ID.
*   [ ] Enable tracing of application calls end-to-end using correlation IDs. (Not implemented.) Implement tracing using a library like OpenTracing or OpenTelemetry.
*   [ ] Support OpenTelemetry type metrics for monitoring. (Not implemented.) Integrate metrics collection using OpenTelemetry to track performance and resource utilization.

## Security

*   [ ] Implement JWT authentication. (Not implemented; currently uses Flask sessions.)  Store JWTs in HttpOnly cookies.    
    *   [ ] Implement token refresh mechanism.
    *   [ ] Implement token revocation.
*   [ ] Implement Two-factor authentication. (Not implemented.)
    *   [ ] Support TOTP (Time-based One-Time Password) or SMS-based 2FA.
*   [ ] Implement Security audit logging. (Basic file-based audit logging is implemented in src/audit_log.py, but "Security audit logging" might imply a more robust system.) Log security-related events, such as login attempts, permission changes, and data access.
*   [ ] Implement actual password hashing. (Implemented in user_management.py using bcrypt.)
*   [ ] Implement actual password verification. (Implemented in user_management.py using bcrypt.)
*   [ ] Implement encryption for sensitive data at rest. Use a library like `cryptography` for encryption. Consider encrypting personal details like names, dates, and locations.
*   [ ] Implement protection against common web vulnerabilities (e.g., XSS, CSRF, SQL injection). Use appropriate security headers and input validation.
*   [ ] Regularly update dependencies to patch security vulnerabilities.
*   [ ] Implement rate limiting to prevent abuse.

## Frontend

*   [ ] Redesign the dashboard:
    *   [ ] Create personalized dashboard with recent activity feed.
    *   [ ] Implement quick access to favorites.
    *   [ ] Add research suggestions section.
    *   [ ] Create statistics overview for the tree.
    *   [ ] Create tree health overview (e.g., data completeness).
*   [ ] Add the ability to search for people to create relationships with and create them if not found in search.
*   [ ] Ensure that people at the same level are horizontally at the same level i.e. a husband and wife at the same level, but above all their children whom are also at the same level.
*   [ ] Implement tabbed interface for person details.
*   [ ] Add fields for military service.
*   [ ] Add fields for education history.
*   [ ] Add fields for occupation history.
*   [ ] Implement life event timeline tracking.
*   [ ] Build timeline visualization component.
*   [ ] Create media gallery with lightbox.
*   [ ] Implement relationship view from person perspective.
*   [ ] Create person merging capability for duplicate detection.
*   [ ] Add confidence levels for biographical data.
*   [ ] Create form validation library.
*   [ ] Implement stepped forms for complex data entry.
*   [ ] Add autosave functionality.
*   [ ] Create reusable form components.
*   [ ] Implement field-level validation and error handling.
*   [ ] Build form state persistence.
*   [ ] Implement advanced search form.
*   [ ] Create filter panels for tree view.
*   [ ] Add saved searches functionality.
*   [ ] Implement search suggestions and autocomplete.
*   [ ] Create relationships based on search results.
    *   [ ] Families or people with the same surname born in the same areas, might be related, offer the option to create a relationship between them.
*   [ ] Optimize UI for mobile responsiveness.
*   [ ] Test UI on different mobile devices.
*   [ ] Optimize performance for mobile devices.

## Media management

*   [ ] Create S3-compatible storage architecture.
*   [ ] Build media upload functionality with drag-and-drop.
*   [ ] Create media processing pipeline (validation, virus scan, EXIF extraction).
*   [ ] Implement thumbnail generation for different resolutions.
*   [ ] Build media gallery with lightbox.
*   [ ] Create media organization tools.
*   [ ] Add face recognition suggestion interface.
*   [ ] Implement media tagging system.
*   [ ] Create default image for men, women, boys and girls.

## GEDCOM support

*   [ ] Add GEDCOM import capability. (Not implemented.)
*   [ ] Implement GEDCOM export functionality. (Not implemented.)
*   [ ] Create merge strategy for imported data. (Not implemented.)
*   [ ] Add validation for GEDCOM format compliance. (Not implemented.)

## Collaboration

*   [ ] Implement basic collaboration tools (e.g., shared view). (Not implemented.)
*   [ ] Add user role and permissions management. (Basic role handling is in user_management.py and decorators in main.py, but full management UI/features are not implemented.)
*   [ ] Build collaboration history tracking. (Not implemented.)
*   [ ] Create collaboration notifications. (Not implemented.)
*   [ ] Research and implement advanced collaboration features (e.g., commenting, shared editing). (Not implemented.)
*   [ ] Implement user profile management. (Basic user details retrieval is in user_management.py, but full profile management is not implemented.)
*   [ ] Create user preferences for visualization. (Not implemented.)
*   [ ] Add favorite/recent people tracking. (Not implemented.)
*   [ ] Implement notification system for changes. (Not implemented.)
*   [ ] Create activity feed for tree changes. (Not implemented.)
*   [ ] Build user activity dashboard. (Not implemented.)
*   [ ] Add email notifications for important changes. (Not implemented.)

## Data Export and Backup

*   [ ] Create report builder interface. (Not implemented.)
*   [ ] Implement print layouts for trees. (Not implemented.)
*   [ ] Add PDF generation for family trees. (Not implemented.)
*   [ ] Build custom report generation. (Not implemented.)
*   [ ] Create sharing options for reports. (Not implemented.)
*   [ ] Implement data export in multiple formats. (Not implemented.)

## API Enhancements and Integration

*   [ ] Implement proper API versioning (/api/v1/...). (Not implemented.)
*   [ ] Create OpenAPI/Swagger documentation. (Not implemented.)
*   [ ] Add rate limiting and throttling. (Not implemented.)
*   [ ] Implement proper error response structure. (Basic Flask error handlers are present, but might need refinement for a consistent API structure.)
*   [ ] Create webhooks for external system integration. (Not implemented.)
*   [ ] Add OAuth support for third-party authentication. (Not implemented.)
*   [ ] Implement public API for approved partners. (Not implemented.)
*   [ ] Create data sync capabilities. (Not implemented.)

## Backend Services

*   [ ] Refactor db_utils.py to correctly use encryption functions. (Completed.)
*   [ ] Implement get_all_events logic in services.py. (Implemented.)
*   [ ] Implement get_event_by_id logic in services.py. (Implemented.)
*   [ ] Implement create_event logic in services.py. (Implemented.)
*   [ ] Implement update_event logic in services.py. (Implemented.)
*   [ ] Implement delete_event logic in services.py. (Implemented.)
*   [ ] Implement get_all_sources logic in services.py. (Implemented.)
*   [ ] Implement get_source_by_id logic in services.py. (Implemented.)
*   [ ] Implement create_source logic in services.py. (Implemented.)
*   [ ] Implement update_source logic in services.py. (Implemented.)
*   [ ] Implement delete_source logic in services.py. (Implemented.)
*   [ ] Implement get_all_citations logic in services.py. (Implemented.)
*   [ ] Implement get_citation_by_id logic in services.py. (Implemented.)
*   [ ] Implement create_citation logic in services.py. (Implemented.)
*   [ ] Implement update_citation logic in services.py. (Implemented.)
*   [ ] Implement delete_citation logic in services.py. (Implemented.)
*   [ ] Implement create_person_attribute logic in services.py. (Implemented.)
*   [ ] Implement update_person_attribute logic in services.py. (Implemented.)
*   [ ] Implement delete_person_attribute logic in services.py. (Implemented.)
*   [ ] Implement get_relationship_by_id logic in services.py. (Implemented.)
*   [ ] Implement create_relationship logic in services.py. (Implemented.)
*   [ ] Implement update_relationship logic in services.py. (Implemented.)
*   [ ] Implement delete_relationship logic in services.py. (Implemented.)
*   [ ] Implement get_relationship_attribute logic in services.py. (Implemented.)
*   [ ] Implement create_relationship_attribute logic in services.py. (Implemented.)
*   [ ] Implement update_relationship_attribute logic in services.py. (Implemented.)
*   [ ] Implement delete_relationship_attribute logic in services.py. (Implemented.)
*   [ ] Implement get_all_media logic in services.py. (Implemented.)
*   [ ] Implement get_media_by_id logic in services.py. (Implemented.)
*   [ ] Implement create_media logic in services.py. (Implemented.)
*   [ ] Implement update_media logic in services.py. (Implemented.)
*   [ ] Implement delete_media logic in services.py. (Implemented.)
*   [ ] Implement get_partial_tree logic in services.py. (Placeholder.)
*   [ ] Implement get_extended_family logic in services.py. (Placeholder added.)
*   [ ] Implement get_related logic in services.py. (Placeholder added.)

## Testing and Reliability

*   [ ] Create a comprehensive test suite with high coverage. (Tests exist, but coverage needs to be assessed.) Use pytest for unit and integration tests. Aim for >80% coverage.
*   [ ] Implement load testing scripts. (Not implemented.) Use Locust or JMeter to simulate concurrent users and measure performance.
*   [ ] Add automated integration testing. (Integration tests exist, but automation setup like CI/CD is pending.) Set up a CI/CD pipeline using GitHub Actions to run tests automatically on every commit.
*   [ ] Create stress testing for large tree handling. (Not implemented.)
*   [ ] Create a GitHub Actions workflow for CI/CD. (Not implemented.)
*   [ ] Deploy the application to a scalable cloud hosting environment. (Not implemented.)  Consider using AWS, Google Cloud, or Azure. Use Docker containers for deployment. 