# Project TODO List

## Core Functionality
- [x] Basic project structure setup (folders, main files)
- [x] `Person` class implementation (attributes: id, first_name, last_name, nickname, dob, dod, etc.)
- [x] `Relationship` class implementation (attributes: person1_id, person2_id, rel_type)
- [x] `FamilyTree` class core logic (add person, add relationship, find person)
- [x] Data persistence for family tree (e.g., JSON file using db_utils)
- [x] Implement editing a person's details (Backend + Web route)
- [x] Implement deleting a person (Backend + Web route)
- [x] Implement editing a relationship (Backend + Web route - Type only)
- [x] Implement deleting a relationship (Backend + Web route)
- [x] Add support for different relationship types (parent-child, spouse, sibling, etc.)
- [x] Implement search/filtering functionality (Basic name/nickname search implemented)
- [x] Implement advanced search/filtering (by date range implemented)
- [ ] Implement advanced search/filtering (by location etc.)

## User Management
- [x] `User` class implementation (attributes: id, username, password_hash)
- [x] User registration logic
- [x] User login logic
- [x] Password hashing (using bcrypt via encryption.py)
- [x] Data persistence for users (e.g., JSON file using UserManagement & db_utils)
- [ ] User roles/permissions (if needed, e.g., admin vs regular user)
- [ ] Password reset functionality

## Web Interface (Flask)
- [x] Basic Flask app setup (`app.py`)
- [x] Templates directory and basic HTML structure (`templates/index.html`)
- [x] Web interface for user registration
- [x] Web interface for user login
- [x] User session management (login/logout)
- [x] Web form for adding a new person to the tree
- [x] Web form for adding a new relationship between people
- [x] Display family tree data on the web page (list view for people & relationships)
- [x] Interface for editing people/relationships
- [x] Interface for deleting people/relationships
- [x] Protect family tree modification routes (require login)
- [x] Basic Search UI and Results Page (with DOB filter)
- [ ] Improve UI/UX (styling, layout, feedback messages)

## Data Management & Storage
- [x] Utility functions for loading/saving JSON data (`db_utils.py`)
- [ ] Consider switching to a database (SQLite, PostgreSQL) for larger trees
- [x] Data validation (Basic date logic, required fields, self-reference checks added)
- [ ] Implement more robust/complex data validation rules
- [ ] Backup and restore functionality

## Security
- [x] Password hashing
- [ ] Input validation and sanitization to prevent injection attacks (Minimal validation added)
- [x] Secure session management (e.g., Flask's secret key)
- [ ] CSRF protection for forms (Removed due to issues, needs revisit/re-implementation)

## Logging & Error Handling
- [x] Basic audit logging for user actions (registration, login, add/edit/delete person/relationship, search)
- [x] Expand audit logging for family tree modifications (Done for current CRUD)
- [ ] Implement robust error handling and user feedback (Basic Flask flashing added)

## Testing
- [x] Unit tests for `Person` class (File exists)
- [x] Unit tests for `Relationship` class (File exists)
- [x] Unit tests for `FamilyTree` class (File exists)
- [x] Unit tests for `User` class (File exists)
- [x] Unit tests for `UserManagement` (File exists)
- [ ] Integration tests for web endpoints
- [ ] Test edge cases and error conditions (Partially covered)
- [ ] Add tests for new features (Search, Relationship CRUD, Validation)

## Documentation
- [x] Basic `README.md` (File exists)
- [ ] Add usage instructions to `README.md`
- [ ] Document code with comments and docstrings (Partially done)
- [ ] User guide (optional)

## Deployment
- [ ] Choose a deployment platform (e.g., Heroku, PythonAnywhere)
- [ ] Configure production environment (e.g., Gunicorn, environment variables)
- [ ] Setup instructions for deployment
