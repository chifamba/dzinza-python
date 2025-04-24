# TODO List

## Feature 1: Dashboard Redesign

-   [ ] Create personalized dashboard with recent activity feed.
-   [ ] Implement quick access to favorites.
-   [ ] Add research suggestions section.
-   [ ] Create statistics overview for the tree.
-   [ ] Create tree health overview (e.g., data completeness).
-   [ ] Add the ability to search for people to create relationship with and create them if not found in search.
-   [ ] Ensure that people at the same level are hoizontally at the same level i.e. a husband and wife at the same level, but above all thier children whom are also at the same level.

## Feature 2: Person Detail View

-   [ ] Implement tabbed interface for person details.
-   [ ] Add fields for military service.
-   [ ] Add fields for education history.
-   [ ] Add fields for occupation history.
-   [ ] Implement life event timeline tracking.
-   [ ] Build timeline visualization component.
-   [ ] Create media gallery with lightbox.
-   [ ] Implement relationship view from person perspective.
-   [ ] Create person merging capability for duplicate detection.
-   [ ] Add confidence levels for biographical data.

## Feature 3: Form Components

-   [ ] Create form validation library.
-   [ ] Implement stepped forms for complex data entry.
-   [ ] Add autosave functionality.
-   [ ] Create reusable form components.
-   [ ] Implement field-level validation and error handling.
-   [ ] Build form state persistence.

## Feature 4: Search & Filter Interface

-   [ ] Implement advanced search form.
-   [ ] Create filter panels for tree view.
-   [ ] Add saved searches functionality.
-   [ ] Implement search suggestions and autocomplete.
-   [ ] create relationships based on search results
-   [ ] families or people with the same surname born in the same areas, might be related, offer the option to create a relationship between them.


## Feature 5: Media Management

-   [ ] Create S3-compatible storage architecture.
-   [ ] Build media upload functionality with drag-and-drop.
-   [ ] Create media processing pipeline (validation, virus scan, EXIF extraction).
-   [ ] Implement thumbnail generation for different resolutions.
-   [ ] Build media gallery with lightbox.
-   [ ] Create media organization tools.
-   [ ] Add face recognition suggestion interface.
-   [ ] Implement media tagging system.
-   [ ] Create default image for men, women, boys and girls.

## Feature 6: Collaboration Tools

-   [ ] Implement basic collaboration tools (e.g., shared view).
-   [ ] Add user role and permissions management.
-   [ ] Build collaboration history tracking.
-   [ ] Create collaboration notifications.
-   [ ] Research and implement advanced collaboration features (e.g., commenting, shared editing).

## Feature 6.3: Reports & Exports

-   [ ] Create report builder interface.
-   [ ] Implement print layouts for trees.
-   [ ] Add PDF generation for family trees.
-   [ ] Build custom report generation.
-   [ ] Create sharing options for reports.
-   [ ] Implement data export in multiple formats.

## Feature 7: User Experience & Mobile Support

-   [ ] Implement user profile management.
-   [ ] Create user preferences for visualization.
-   [ ] Add favorite/recent people tracking.
-   [ ] Implement notification system for changes.
-   [ ] Create activity feed for tree changes.
-   [ ] Build user activity dashboard.
-   [ ] Add email notifications for important changes.
-   [ ] Create guided tours for new users.
-   [ ] Implement contextual help system.
-   [ ] Add tooltips for complex features.
-   [ ] Create knowledge base and FAQ.
-   [ ] Build help content management system.

## Feature 7.3: Mobile Optimization
- [ ] Optimize UI for mobile responsiveness.
- [ ] Test UI on different mobile devices.
- [ ] optimize performance for mobile devices.

## Feature 8: PostgreSQL Database (Completed)

-   [x] Update `docker-compose.yml` to use a PostgreSQL database image.
-   [x] Configure `docker-compose.yml` to use a 10GB Persistent Volume Claim (PVC) for PostgreSQL data.
-   [x] Remove alembic configurations.
-   [ ] Implement database replication to improve performance.
-   [x] Update app.py to connect to the database.
-   [x] Create the database models in app.py.
-   [x] Create the database schema programatically in app.py.
-   [x] Create an initial job to populate the database with the base schema and initial structure. this should run once only.
- [x] Add PostgreSQL as the database to the backend.
