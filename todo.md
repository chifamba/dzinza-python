# Project TODO List

## Features
- [x] Basic user authentication (login/logout)
- [x] Add person to family tree
- [x] Edit person details
- [x] Add relationships between people
- [x] View family tree structure (basic text representation)
- [ ] Visualize family tree (e.g., using a graph library)
- [x] User roles (Admin, User)
- [x] Admin user management panel
- [x] Search functionality for people
- [x] Password reset functionality
- [x] Audit logging for important actions

## Refactoring & Improvements
- [ ] Improve error handling and user feedback
- [ ] Refactor database interactions (potentially use a simple ORM or dedicated data layer)
- [ ] Enhance UI/UX design
- [ ] Add input validation for all forms
- [ ] Secure sensitive data (e.g., encryption for stored data beyond passwords)

## Testing
- [x] Unit tests for `Person` class (`test_person.py`)
- [x] Unit tests for `Relationship` class (`test_relationship.py`)
- [x] Unit tests for `User` class (`test_user.py`)
- [x] Unit tests for `FamilyTree` class (`test_family_tree.py`) - *Enhanced*
- [x] Unit tests for `UserManagement` (`test_user_management.py`) - *Enhanced*
- [x] Unit tests for `encryption` module (`test_encryption.py`)
- [x] Unit tests for `db_utils` module (`test_db_utils.py`)
- [x] Unit tests for `audit_log` module (`test_audit_log.py`)
- [x] Basic integration tests for Flask app (`test_app_integration.py`)
- [x] Basic tests for Flask app routes (`test_app.py`) - *Enhanced*
- [x] More comprehensive integration tests covering user workflows (`test_app_integration.py`) - *Enhanced*
- [ ] Test UI interactions (potentially using Selenium or similar)

## Documentation
- [x] Basic README.md
- [ ] Add detailed usage instructions
- [ ] Document code modules and functions (docstrings)
- [ ] Set up project documentation website (e.g., using Sphinx)

## Deployment
- [ ] Configure for production deployment (e.g., Gunicorn, Nginx)
- [ ] Set up database for production
- [ ] Containerize the application (Docker)
