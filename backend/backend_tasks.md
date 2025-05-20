# API Enhancement Plan for Family Tree Application

This plan outlines proposed enhancements to the backend API, focusing on new features, scalability for Kubernetes, security, and maintainability.

## I. Core API & Data Model Enhancements

This section focuses on enriching the existing data models and related API endpoints.

### A. Person Model Enhancements

- **DONE - Task 1.1: Add More Granular Location Data to Person Model**  
  Description: Add `place_of_birth` (String) and `place_of_death` (String) fields.  
  Files to Update: `models.py`, `services/person_service.py`, `blueprints/people.py`.  
  Action: Include database migration script (e.g., Alembic).

- **DONE - Task 1.2: Add Extended Biography to Person Model**  
  Description: Add a `biography` (Text type) field for detailed descriptions.  
  Files to Update: `models.py`, `services/person_service.py`, `blueprints/people.py`.  
  Action: Include database migration.

- **DONE - Task 1.3: Add Profile Picture URL to Person Model**  
  Description: Add `profile_picture_url` (String). Actual file upload is a separate feature (see II.A).  
  Files to Update: `models.py`, `services/person_service.py`, `blueprints/people.py`.  
  Action: Include database migration.

- **DONE - Task 1.4: Implement Custom Fields/Tags for Persons**  
  Description: Allow users to add custom key-value attributes to a person.  
  Design Choice: JSONB field in Person model or a separate PersonCustomField table.  
  Files to Update: `models.py`, `services/person_service.py`, `blueprints/people.py`.  
  Action: Include database migration.

### B. Relationship Model Enhancements

- **DONE - Task 1.5: Add Location to Relationship Model**  
  Description: Add `location` (String) field (e.g., place of marriage).  
  Files to Update: `models.py`, `services/relationship_service.py`, `blueprints/relationships.py`.  
  Action: Include database migration.

- **DONE - Task 1.6: Add Notes to Relationship Model**  
  Description: Add `notes` (Text type) field for details about the relationship.  
  Files to Update: `models.py`, `services/relationship_service.py`, `blueprints/relationships.py`.  
  Action: Include database migration.

- **DONE - Task 1.7: Expand Relationship Types**  
  Description: Support more granular relationship types (e.g., "ADOPTIVE_PARENT_OF", "STEP_PARENT_OF", "SIBLING", "HALF_SIBLING").  
  Files to Update: `models.py` (enum/choices), `services/relationship_service.py` (validation, inverse relationship logic).  
  Action: Ensure relationship_service can automatically create or suggest inverse relationships (e.g., if A is PARENT_OF B, B is CHILD_OF A).

### C. Tree Model Enhancements

- **Task 1.8: Add Cover Image URL to Tree Model**  
  Description: Add `cover_image_url` (String). File upload is separate (see II.A).  
  Files to Update: `models.py`, `services/tree_service.py`, `blueprints/trees.py`.  
  Action: Include database migration.

- **DONE - Task 1.9: Implement Tree Privacy Settings**  
  Description: Add `privacy_setting` (e.g., "PUBLIC", "PRIVATE_LINK_VIEW", "PRIVATE_LINK_EDIT", "PRIVATE_MEMBERS_ONLY") to Tree model.  
  Files to Update: `models.py`, `services/tree_service.py` (authorization logic), `decorators.py`, `blueprints/trees.py`.  
  Action: Include database migration.

### D. Event/Milestone System

- **DONE - Task 1.10: Design and Implement Event Model**  
  Description: Create an Event model (event_id, person_id (nullable), tree_id, event_type (e.g., "BIRTH", "DEATH", "MARRIAGE", "EDUCATION", "OCCUPATION", "MIGRATION", "RESIDENCE"), date_start, date_end (optional), location, description, related_person_ids (JSON/Array for multiple people in an event like marriage)).  
  Files to Create/Update: `models.py`, new `services/event_service.py`, new `blueprints/events.py`.  
  Action: Include database migration.

- **DONE - Task 1.11: API Endpoints for Linking Events**  
  Description: Endpoints to associate events with people and trees; list events for a person/tree.  
  Files to Update: `blueprints/people.py`, `blueprints/trees.py`, `blueprints/events.py`.

## II. User Experience & Feature Enhancements

This section focuses on features that directly improve user interaction and capabilities.

### A. Media/File Uploads

- **DONE - Task 2.1: Configure Object Storage**  
  Description: Integrate with an object storage solution (e.g., MinIO for self-hosting in Kubernetes, or AWS S3/Google Cloud Storage).  
  Files to Update: `config.py` (storage credentials, bucket names via env vars).

- **DONE - Task 2.2: Implement Profile Picture Upload**  
  Description: Endpoint in `blueprints/people.py` to upload a profile picture for a person. `person_service.py` to handle file stream, save to object storage, update `Person.profile_picture_url`.  
  Consideration: Image resizing/thumbnail generation (possibly via background task - see III.D).

- **DONE - Task 2.3: Implement Tree Cover Image Upload**  
  Description: Similar to profile pictures, for `blueprints/trees.py` and `services/tree_service.py`.

- **DONE - Task 2.4: Generic Document/Media Attachment System**  
  Description: Allow users to attach various media (photos, documents, videos) to People, Events, or Trees.  
  Model: New MediaItem model (media_id, uploader_user_id, file_name, file_type, storage_path, linked_entity_type (Person, Event, Tree), linked_entity_id, upload_date, caption, thumbnail_url).  
  Files to Create/Update: `models.py`, new `services/media_service.py`, new `blueprints/media.py`.

### B. Advanced Search & Filtering

- **Task 2.5: Full-Text Search for People**  
  Description: Implement search across names, notes, biography within a user's accessible trees.  
  Files to Update: `blueprints/people.py` (add search query params), `services/person_service.py` (use database FTS like PostgreSQL's tsvector or ILIKE).

- **Task 2.6: Advanced Filtering for People**  
  Description: Filter people by date ranges (birth, death), gender, custom fields, event participation.  
  Files to Update: `blueprints/people.py` (add filter params), `services/person_service.py`.

- **Task 2.7: (Optional) Dedicated Search Engine Integration**  
  Description: For very large datasets or complex queries, explore Elasticsearch/OpenSearch.  
  Action: This is a major sub-project involving data synchronization pipelines.

### C. Notifications & Activity Feed

- **Task 2.8: Implement Notification System**  
  Model: Notification (notification_id, recipient_user_id, type, message, related_entity_type, related_entity_id, is_read, created_at).  
  Files to Create/Update: `models.py`, new `services/notification_service.py`, new `blueprints/notifications.py` (fetch, mark read).

- **Task 2.9: Integrate Notification Triggers**  
  Description: Generate notifications for events like tree sharing, collaborator updates, significant person data changes (if desired).  
  Files to Update: `services/tree_service.py`, `services/person_service.py`, etc.

- **Task 2.10: Enhance Activity Feed**  
  Description: Expand `services/activity_service.py` to log more granular changes (e.g., person added/updated, relationship created, event logged) within a tree.  
  Files to Update: `blueprints/trees.py` (endpoint for tree-specific activity), `services/activity_service.py`.

### D. Collaboration & Sharing

- **Task 2.11: Implement Tree Sharing with Roles**  
  Model: TreeCollaborator (tree_id, user_id, role (e.g., "VIEWER", "SUGGESTER", "EDITOR", "ADMIN"), status (e.g., "PENDING", "ACCEPTED")).  
  Files to Create/Update: `models.py`, `services/tree_service.py` (invite, accept, manage collaborators, permission checks), `blueprints/trees.py` (collaboration endpoints).

- **Task 2.12: Refine Authorization Decorators**  
  Description: Update `decorators.py` to incorporate tree-level roles for fine-grained access control.

### E. Data Import/Export

- **Task 2.13: GEDCOM Export**  
  Description: Endpoint in `blueprints/trees.py` to export a family tree in GEDCOM format.  
  Files to Update: `services/tree_service.py` (complex logic to map internal data to GEDCOM). Consider as background task.

- **Task 2.14: (Advanced) GEDCOM Import**  
  Description: Endpoint for importing GEDCOM files. Extremely complex due to format variations and data mapping.  
  Action: Definitely a background task. Requires robust parsing and conflict resolution strategies.

### F. User Profile & Account Management

- **Task 2.15: Enhanced User Profile Management**  
  Description: API endpoints for users to update their profile (email, password, display name, profile settings).  
  Files to Update: `blueprints/auth.py` (or new profile.py), `services/user_service.py`.

## III. Scalability, Performance & Reliability (Kubernetes Focus)

This section addresses aspects crucial for running in a containerized, orchestrated environment.

### A. Statelessness & Configuration

- **Task 3.1: Environment Variable Configuration**  
  Description: Ensure all configurations (DB URLs, secrets, external service endpoints) are injectable via environment variables.  
  Files to Review/Update: `config.py`, deployment manifests.

- **Task 3.2: Distributed Session Management (if applicable)**  
  Description: If using server-side sessions, configure a distributed store (e.g., Redis) to maintain statelessness of app instances. JWTs are inherently stateless.  
  Files to Update: Flask app initialization in `main.py`, `config.py`.

### B. Database Optimization

- **Task 3.3: Indexing Strategy Review**  
  Description: Analyze common query patterns and add/optimize database indexes.  
  Files to Update: `models.py` (add indexes), database migration scripts.

- **Task 3.4: Connection Pooling**  
  Description: Verify effective database connection pooling by SQLAlchemy and the WSGI server (e.g., Gunicorn).  
  Files to Review/Update: `database.py`, WSGI server configuration.

### C. Caching Layer

- **Task 3.5: Implement Caching for Hot Data**  
  Description: Use a caching solution (e.g., Flask-Caching with Redis backend) for frequently accessed, rarely changing data (e.g., tree metadata, user profiles, public tree views).  
  Files to Update: `main.py` (init cache), `config.py` (cache settings), relevant service methods.

### D. Asynchronous Task Processing

- **Task 3.6: Integrate Task Queue (Celery)**  
  Description: Set up Celery with a broker (Redis or RabbitMQ) for background tasks.  
  Files to Create/Update: Celery app setup, `config.py` (broker URL), task definitions.

- **Task 3.7: Offload Long-Running Operations**  
  Description: Refactor services to use Celery for tasks like GEDCOM I/O, bulk updates, image processing, complex notification generation.

### E. Observability (Logging, Metrics, Tracing)

- **Task 3.8: Structured Logging**  
  Description: Implement JSON-formatted logging for easier aggregation in Kubernetes (e.g., ELK/EFK stack).  
  Files to Update: Logger configuration in `main.py` or `config.py`.

- **Task 3.9: Application Metrics (Prometheus)**  
  Description: Expose key application metrics (request rates, error counts, latencies) via a /metrics endpoint compatible with Prometheus.  
  Action: Use a library like `prometheus_flask_exporter`.

- **Task 3.10: Distributed Tracing (Optional but Recommended)**  
  Description: Integrate OpenTelemetry for tracing requests, especially if planning microservices or complex interactions.  
  Action: Instrument Flask app and key service calls.

### F. Kubernetes Health Probes

- **Task 3.11: Enhance Health Checks**  
  Description: Ensure /health (from `blueprints/health.py`) is suitable for liveness probes. Create a more comprehensive readiness probe endpoint that checks critical dependencies (DB, cache).  
  Files to Update: `blueprints/health.py`.

## IV. Security Enhancements

Focusing on hardening the API against common threats.

### A. Input Validation and Sanitization

- **Task 4.1: Standardize Request/Response Validation**  
  Description: Use a library like Marshmallow or Pydantic across all blueprints for robust input validation and response serialization.  
  Files to Update: All blueprint files (`people.py`, `trees.py`, etc.).

### B. Authentication & Authorization

- **Task 4.2: Implement Rate Limiting**  
  Description: Protect sensitive endpoints (login, register, password reset, resource creation) against abuse.  
  Action: Use a library like `Flask-Limiter` with Redis.

- **Task 4.3: JWT Refresh Token Mechanism**  
  Description: Implement refresh tokens for more secure and longer user sessions.  
  Files to Update: `blueprints/auth.py`, `services/user_service.py`.

- **Task 4.4: Review Password Policies**  
  Description: Enforce strong password complexity, consider password expiry if required by policy.  
  Files to Update: `services/user_service.py`.

- **Task 4.5: (Advanced) Two-Factor Authentication (2FA)**  
  Description: Implement 2FA (e.g., TOTP). This is a significant feature.  
  Files to Update: `models.py` (User model), `blueprints/auth.py`, `services/user_service.py`.

### C. API Security Best Practices

- **Task 4.6: Security Headers**  
  Description: Configure appropriate HTTP security headers (HSTS, X-Content-Type-Options, CSP, etc.).  
  Action: Implement as middleware or via WSGI server config.

## V. Developer Experience & Maintainability

Improving the development lifecycle and code quality.

### A. API Documentation

- **Task 5.1: OpenAPI/Swagger Documentation**  
  Description: Generate interactive API documentation from code annotations.  
  Action: Use Flask-RESTx, Flask-Smorest, or apispec with Swagger UI/ReDoc.

### B. Testing

- **Task 5.2: Increase Test Coverage**  
  Description: Write more unit tests for services and integration tests for API endpoints.  
  Files to Update/Create: Expand `tests/` directory.

- **Task 5.3: CI/CD Pipeline**  
  Description: Set up a CI/CD pipeline (e.g., GitHub Actions, GitLab CI) for automated testing, linting, and potentially deployment.

### C. API Versioning

- **Task 5.4: Implement API Versioning Strategy**  
  Description: Introduce API versioning (e.g., `/api/v1/...` in URL, or header-based) for managing breaking changes.  
  Action: Update blueprint registrations in `main.py`.

This plan provides a roadmap for significant enhancements. Tasks should be prioritized based on project goals and available resources.
