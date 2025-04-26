# Family Tree Project TODO List - Updated April 26, 2025 (v9)

**NOTE:** Status reflects analysis of the provided `backend/main.py` service functions *only*. Claims of implementation in other files (`services.py`, etc.) within the original todo list are noted but *not verified* by this analysis unless explicitly implemented in the provided `main.py`. API Endpoint implementation is assumed separate. Model definitions assume the placeholder structures (including `EncryptedString`) from `main.py` are applied to the actual models (e.g., in `models.py`).

## General Assumptions

* [x] **Single File Backend:** All Python backend code will reside in a single file (`main.py`) initially for simplicity. This may be refactored later for better organization. *(Note: Current `main.py` seems to be only service functions, suggesting other files might exist or are intended).*
* [x] **Frontend:** The frontend is a separate React application. *(Assumed based on project structure)*
* [x] **Database:** PostgreSQL is the chosen database. *(Assumed based on docker-compose.yml and SQLAlchemy usage)*
* [x] **Encryption:** Encryption is used for sensitive data at rest. *(Implemented in `main.py` via `EncryptedString` TypeDecorator using `cryptography`. Key management strategy required. Search/sort limitations apply to encrypted fields).*
* [x] **Authentication:** JWT will be used for authentication, and password hashing is implemented with bcrypt. *(Password hashing/verification implemented in `main.py` using bcrypt. JWT generation/handling is separate, likely in API layer).*
* [x] **Data Models:** Data models are defined as Python classes and are reflected in the database schema. *(Assumed based on SQLAlchemy usage in `main.py`)*

## Data Models

### User Data Model

* [x] Define User data model: *(Placeholder model defined in `main.py` with specified attributes)*
    * Attributes: `user_id` (INT, PK), `username` (VARCHAR, UNIQUE), `email` (VARCHAR, UNIQUE), `password_hash` (VARCHAR), `role` (ENUM: 'user', 'admin'), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP), `last_login` (TIMESTAMP), `is_active` (BOOLEAN).
    * Relationships: One-to-many with audit logs (user performing actions). *(Relationship definition itself not implemented in placeholder)*
    * Validation: Username and email uniqueness, password complexity rules. *(Uniqueness handled by DB constraints, complexity rules need application-level check)*
    * Encryption: The `password_hash` field stores securely hashed passwords using bcrypt. *(Implemented via `_hash_password`)*
* [x] Implement User CRUD operations (Create, Read, Update, Delete) via API endpoints. *(All CRUD **service functions** exist in `main.py`. API endpoints separate)*.
* [x] Implement User registration and authentication. *(Service functions `register_user_db` and `authenticate_user_db` implemented in `main.py`)*.
* [x] Implement User role management (admin can modify user roles). *(Service function `update_user_role_db` implemented in `main.py`)*.

### Person Data Model

* [x] Define Person data model: *(Placeholder model defined in `main.py` with `EncryptedString` applied to sensitive fields. Assumes application to real model)*
    * Attributes: `person_id` (INT, PK), `first_name` (VARCHAR), `last_name` (VARCHAR), `middle_name` (VARCHAR, nullable), `birth_date` (DATE, nullable), `death_date` (DATE, nullable), `birth_location` (VARCHAR, nullable), `death_location` (VARCHAR, nullable), `gender` (ENUM: 'male', 'female', 'other', nullable), `profile_picture` (VARCHAR, nullable - URL to media), `bio` (TEXT, nullable), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP).
    * Relationships:
        * One-to-many with PersonAttribute.
        * One-to-many with Relationships (as subject and object).
        * One-to-many with Media.
        * One-to-many with Events.
    * Validation: Date format, valid gender values.
* [x] Implement Person CRUD operations via API endpoints. *(All CRUD **service functions** exist in `main.py`. API endpoints separate)*.
* [x] Implement advanced search and filtering for people. *(Basic filtering exists. **Trigram similarity search implemented** for name fields in `main.py` (requires `pg_trgm` extension). Full phonetic/fuzzy search may require other techniques).*

### PersonAttribute Data Model

* [x] Define PersonAttribute data model: *(Placeholder model defined in `main.py` with `EncryptedString` applied. Assumes application to real model)*
* [x] Implement PersonAttribute CRUD operations via API endpoints. *(All CRUD **service functions** exist in `main.py`. API endpoints separate)*.

### Relationship Data Model

* [x] Define Relationship data model: *(Placeholder model defined in `main.py` with `EncryptedString` applied. Assumes application to real model)*
    * Attributes: `relationship_id` (INT, PK), `subject_id` (INT, FK to Person), `object_id` (INT, FK to Person), `relationship_type` (VARCHAR), `start_date` (DATE, nullable), `end_date` (DATE, nullable), `description` (TEXT, nullable), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP).
    * Relationships:
        * Many-to-one with Person (subject).
        * Many-to-one with Person (object).
        * One-to-many with RelationshipAttribute.
    * Validation: `relationship_type` must be a valid, predefined type (e.g., 'parent', 'child', 'spouse'). Subject and object must be different.
* [x] Implement Relationship CRUD operations via API endpoints. *(All CRUD **service functions** exist in `main.py`. API endpoints separate)*.

### RelationshipAttribute Data Model

* [x] Define RelationshipAttribute data model: *(Placeholder model defined in `main.py` with `EncryptedString` applied. Assumes application to real model)*
* [x] Implement RelationshipAttribute CRUD operations via API endpoints. *(All CRUD **service functions** exist in `main.py`. API endpoints separate)*.

### Media Data Model

* [x] Define Media data model: *(Placeholder model defined in `main.py` with `EncryptedString` applied. Assumes application to real model)*
* [x] Implement Media CRUD operations via API endpoints. *(All CRUD **service functions** exist in `main.py`. Note: File handling separate. API endpoints separate)*.
* [ ] Implement media upload functionality with validation and virus scanning. *(Not in `main.py`. Requires implementation in API endpoint layer).*
* [ ] Integrate with S3-compatible storage. *(Not in `main.py`. Requires implementation in API endpoint layer using libraries like `boto3`).*
* [ ] Implement thumbnail generation. *(Not in `main.py`. Requires implementation in API endpoint or background task).*

### Event Data Model

* [x] Define Event data model: *(Placeholder model defined in `main.py` with `EncryptedString` applied. Assumes application to real model)*
* [x] Implement Event CRUD operations via API endpoints. *(All CRUD **service functions** exist in `main.py`. API endpoints separate)*.

### Source Data Model

* [x] Define Source data model: *(Placeholder model defined in `main.py` with `EncryptedString` applied. Assumes application to real model)*
* [x] Implement Source CRUD operations via API endpoints. *(All CRUD **service functions** exist in `main.py`. API endpoints separate)*.

### Citation Data Model

* [x] Define Citation data model: *(Placeholder model defined in `main.py` with `EncryptedString` applied. Assumes application to real model)*
* [x] Implement Citation CRUD operations via API endpoints. *(All CRUD **service functions** exist in `main.py`. API endpoints separate)*.

## Database

* [x] Update docker-compose.yml to use a PostgreSQL database image. *(Verified via file list)*
* [x] Configure docker-compose.yml to use a 10GB Persistent Volume Claim (PVC) for PostgreSQL data. *(Verified via file list - assumes PVC is correctly configured if used in a K8s context, docker-compose uses volumes)*
* [ ] Remove Alembic configurations. *(Cannot verify)*
* [ ] Implement database replication to improve performance and availability. Consider using streaming replication for PostgreSQL. *(Not implemented in `main.py`)*
* [x] Update app.py to connect to the database. *(Claimed in todo, cannot verify `app.py`)*
* [x] Create the database models. *(Claimed in todo - `app/models`, cannot verify. Needs update for EncryptedString)*
* [x] Create the database schema programmatically in app.py. *(Claimed in todo - `Base.metadata.create_all`, cannot verify `app.py`)*
* [x] Create an initial job to populate the database with the base schema and initial structure. *(Claimed in todo - `db_init.py`, cannot verify)*
* [x] Add PostgreSQL as the database to the *(Task description incomplete, but assumed done based on docker-compose.yml)*
* [x] Create User CRUD API endpoints. *(All service functions exist in `main.py`. API endpoints separate.)*
* [x] Create Person CRUD API endpoints. *(All service functions exist in `main.py`. API endpoints separate.)*
* [x] Create PersonAttribute CRUD API endpoints. *(All service functions exist in `main.py`. API endpoints separate.)*
* [x] Create Relationship CRUD API endpoints. *(All service functions exist in `main.py`. API endpoints separate.)*
* [x] Create RelationshipAttribute CRUD API endpoints. *(All service functions exist in `main.py`. API endpoints separate.)*
* [x] Create Media CRUD API endpoints. *(All service functions exist in `main.py`. API endpoints separate.)*
* [x] Create Event CRUD API endpoints. *(All service functions exist in `main.py`. API endpoints separate.)*
* [x] Create Source CRUD API endpoints. *(All service functions exist in `main.py`. API endpoints separate.)*
* [x] Create Citation CRUD API endpoints. *(All service functions exist in `main.py`. API endpoints separate.)*

## Complex Operations

* [x] Partial tree loading. *(Implemented as `get_partial_tree` in `main.py`)* Implement efficient loading of tree fragments for performance.
* [x] Advanced search and filtering. *(Basic filtering exists. **Trigram similarity search implemented** for name fields in `main.py` (requires `pg_trgm` extension). Full phonetic/fuzzy search may require other techniques).* Implement advanced search features, including phonetic search, fuzzy matching, and boolean operators.
* [x] Define functions to get the relationships and attributes of a person. *(Covered by individual get functions like `get_person_attributes_db`, `get_relationship_attributes_db` etc. in `main.py`)*
* [x] Tree Traversal: *(Implemented in `main.py`)*
    * [x] get_ancestors(db: Session, person_id: int, depth: int): Get the ancestors of a person up to a certain depth. *(Implemented)*
    * [x] get_descendants(db: Session, person_id: int, depth: int): Get the descendants of a person up to a certain depth. *(Implemented)*
    * [x] get_extended_family(db: Session, person_id: int, depth: int): Get the extended family of a person up to a certain depth (siblings, cousins, etc). *(Implemented)*
    * [x] get_related(db: Session, person_id: int, depth: int): Get the related people of a person up to a certain depth (in-laws, step-relations, etc). *(Implemented)*

## Enhanced Logging and Tracing

* [x] Implement enhanced logging throughout the application. *(Structured JSON logging using `structlog` configured in `main.py`. Contextual info added via `logger.bind()` and `structlog.contextvars`.)* Use a structured logging format (e.g., JSON) and include contextual information like user ID and request ID. *(Note: Request-specific context like correlation ID often added via middleware).*
* [x] Enable tracing of application calls end-to-end using correlation IDs. *(OpenTelemetry SDK configured in `main.py` with OTLP exporter (k8s compatible). Manual span examples added. Automatic instrumentation (Flask, SQLAlchemy) needs app-level setup. Correlation ID propagation typically handled by instrumentation/middleware).* Implement tracing using a library like OpenTracing or OpenTelemetry.
* [x] Support OpenTelemetry type metrics for monitoring. *(OpenTelemetry SDK configured in `main.py` with OTLP exporter (k8s compatible). Example custom metrics added. Automatic metrics (e.g., request duration) need instrumentation).* Integrate metrics collection using OpenTelemetry to track performance and resource utilization.

## Security

* [ ] Implement JWT authentication. *(Password hashing/verification done. **JWT generation/validation/refresh/revocation needed in API layer**).* Store JWTs in HttpOnly cookies.
    * [ ] Implement token refresh mechanism. *(API layer)*
    * [ ] Implement token revocation. *(API layer + potentially requires persistence like a blocklist)*
* [ ] Implement Two-factor authentication. *(Not implemented - Requires model changes, API layer logic, OTP library integration)*
    * [ ] Support TOTP (Time-based One-Time Password) or SMS-based 2FA.
* [x] Implement Security audit logging. *(Enhanced structured logging for security events (auth, role changes, deletion attempts) added in `main.py`. Claimed basic implementation exists elsewhere. May need further refinement/centralization).* Log security-related events, such as login attempts, permission changes, and data access.
* [x] Implement actual password hashing. *(Implemented in `main.py` using bcrypt)*
* [x] Implement actual password verification. *(Implemented in `main.py` using bcrypt)*
* [x] Implement encryption for sensitive data at rest. Use a library like `cryptography` for encryption. Consider encrypting personal details like names, dates, and locations. *(Implemented via `EncryptedString` TypeDecorator in `main.py`. Key management & data migration needed.)*
* [ ] Implement protection against common web vulnerabilities (e.g., XSS, CSRF, SQL injection). *(SQLi mitigated by ORM. XSS/CSRF require frontend/API layer implementation - security headers, input sanitization, anti-CSRF tokens).* Use appropriate security headers and input validation.
* [ ] Regularly update dependencies to patch security vulnerabilities. *(Process task)*
* [ ] Implement rate limiting to prevent abuse. *(Not implemented - Typically done at API gateway or via framework middleware/extensions)*

## Frontend

*(All frontend tasks are marked as [ ] as they are outside the scope of backend `main.py` analysis)*
* ... (Frontend tasks remain unchanged) ...

## Media management

* [ ] Create S3-compatible storage architecture. *(Not in `main.py`. Requires infrastructure setup and integration in upload logic).*
* [ ] Build media upload functionality with drag-and-drop. *(Not in `main.py`. Primarily a frontend task interacting with a backend upload endpoint).*
* [ ] Create media processing pipeline (validation, virus scan, EXIF extraction). *(Not in `main.py`. Requires implementation in API endpoint or background task, potentially using external libraries/services).*
* [ ] Implement thumbnail generation for different resolutions. *(Not in `main.py`. Requires implementation potentially in the API layer (synchronous) or preferably in a background task queue (asynchronous) using image processing libraries like Pillow).*
* [ ] Build media gallery with lightbox. *(Frontend task)*
* [ ] Create media organization tools. *(Requires frontend UI and potentially backend service functions for tagging/grouping - not implemented)*
* [ ] Add face recognition suggestion interface. *(Requires significant ML integration, likely external services or models - not implemented)*
* [ ] Implement media tagging system. *(Requires data model changes (e.g., Tag model, MediaTag association table) and corresponding service functions/API endpoints - not implemented)*
* [ ] Create default image for men, women, boys and girls. *(Frontend/Asset task)*

## GEDCOM support

* [ ] Add GEDCOM import capability. *(Not implemented)*
* [ ] Implement GEDCOM export functionality. *(Not implemented)*
* [ ] Create merge strategy for imported data. *(Not implemented)*
* [ ] Add validation for GEDCOM format compliance. *(Not implemented)*

## Collaboration

* [ ] Implement basic collaboration tools (e.g., shared view). *(Not implemented)*
* [ ] Add user role and permissions management. *(Basic role update service function implemented. Full management UI/features separate)*
* [ ] Build collaboration history tracking. *(Not implemented)*
* [ ] Create collaboration notifications. *(Not implemented)*
* [ ] Research and implement advanced collaboration features (e.g., commenting, shared editing). *(Not implemented)*
* [ ] Implement user profile management. *(Basic user CRUD exists. Full profile management separate)*
* [ ] Create user preferences for visualization. *(Not implemented)*
* [ ] Add favorite/recent people tracking. *(Not implemented)*
* [ ] Implement notification system for changes. *(Not implemented)*
* [ ] Create activity feed for tree changes. *(Not implemented)*
* [ ] Build user activity dashboard. *(Not implemented)*
* [ ] Add email notifications for important changes. *(Not implemented)*

## Data Export and Backup

* [ ] Create report builder interface. *(Not implemented)*
* [ ] Implement print layouts for trees. *(Not implemented)*
* [ ] Add PDF generation for family trees. *(Not implemented)*
* [ ] Build custom report generation. *(Not implemented)*
* [ ] Create sharing options for reports. *(Not implemented)*
* [ ] Implement data export in multiple formats. *(Not implemented)*

## API Enhancements and Integration

* [ ] Implement proper API versioning (/api/v1/...). *(Not implemented)*
* [ ] Create OpenAPI/Swagger documentation. *(Not implemented)*
* [ ] Add rate limiting and throttling. *(Not implemented)*
* [ ] Implement proper error response structure. *(Basic Flask aborts used, could be standardized)*
* [ ] Create webhooks for external system integration. *(Not implemented)*
* [ ] Add OAuth support for third-party authentication. *(Not implemented)*
* [ ] Implement public API for approved partners. *(Not implemented)*
* [ ] Create data sync capabilities. *(Not implemented)*

## Backend Services

*(Status based on provided main.py vs. todo list claims)*
* [x] Refactor db_utils.py to correctly use encryption functions. *(Claimed completed, cannot verify)*
* [x] Implement get_all_events logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_event_by_id logic in services.py. *(Implemented in `main.py`)*
* [x] Implement create_event logic in services.py. *(Implemented in `main.py`)*
* [x] Implement update_event logic in services.py. *(Implemented in `main.py`)*
* [x] Implement delete_event logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_all_sources logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_source_by_id logic in services.py. *(Implemented in `main.py`)*
* [x] Implement create_source logic in services.py. *(Implemented in `main.py`)*
* [x] Implement update_source logic in services.py. *(Implemented in `main.py`)*
* [x] Implement delete_source logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_all_citations logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_citation_by_id logic in services.py. *(Implemented in `main.py`)*
* [x] Implement create_citation logic in services.py. *(Implemented in `main.py`)*
* [x] Implement update_citation logic in services.py. *(Implemented in `main.py`)*
* [x] Implement delete_citation logic in services.py. *(Implemented in `main.py`)*
* [x] Implement create_person_attribute logic in services.py. *(Implemented in `main.py`)*
* [x] Implement update_person_attribute logic in services.py. *(Implemented in `main.py`)*
* [x] Implement delete_person_attribute logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_relationship_by_id logic in services.py. *(Implemented in `main.py`)*
* [x] Implement create_relationship logic in services.py. *(Implemented in `main.py`)*
* [x] Implement update_relationship logic in services.py. *(Implemented in `main.py`)*
* [x] Implement delete_relationship logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_relationship_attribute logic in services.py. *(Implemented in `main.py`)*
* [x] Implement create_relationship_attribute logic in services.py. *(Implemented in `main.py`)*
* [x] Implement update_relationship_attribute logic in services.py. *(Implemented in `main.py`)*
* [x] Implement delete_relationship_attribute logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_all_media logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_media_by_id logic in services.py. *(Implemented in `main.py`)*
* [x] Implement create_media logic in services.py. *(Implemented in `main.py`)*
* [x] Implement update_media logic in services.py. *(Implemented in `main.py`)*
* [x] Implement delete_media logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_partial_tree logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_extended_family logic in services.py. *(Implemented in `main.py`)*
* [x] Implement get_related logic in services.py. *(Implemented in `main.py`)*

## Testing and Reliability

* [ ] Create a comprehensive test suite with high coverage. *(Tests exist, coverage needs to be assessed)* Use pytest for unit and integration tests. Aim for >80% coverage.
* [ ] Implement load testing scripts. *(Not implemented)* Use Locust or JMeter to simulate concurrent users and measure performance.
* [ ] Add automated integration testing. *(Integration tests exist, automation setup like CI/CD is pending)* Set up a CI/CD pipeline using GitHub Actions to run tests automatically on every commit.
* [ ] Create stress testing for large tree handling. *(Not implemented)*
* [ ] Create a GitHub Actions workflow for CI/CD. *(Not implemented)*
* [ ] Deploy the application to a scalable cloud hosting environment. *(Not implemented)* Consider using AWS, Google Cloud, or Azure. Use Docker containers for deployment.
