# Project TODO List

## Core Functionality
- [x] Basic project structure setup (folders, main files)
- [x] `Person` class implementation (attributes: id, name, dob, dod, etc.)
- [x] `Relationship` class implementation (attributes: id, person1_id, person2_id, type)
- [x] `FamilyTree` class core logic (add person, add relationship, find person)
- [x] Data persistence for family tree (e.g., JSON file)
- [ ] Implement editing a person's details
- [ ] Implement deleting a person
- [ ] Implement editing a relationship
- [ ] Implement deleting a relationship
- [ ] Add support for different relationship types (parent-child, spouse, sibling) - *Partially done in `Relationship` class, needs explicit handling/validation*
- [ ] Implement search/filtering functionality (by name, date range, etc.)
- [ ] Visualization of the family tree (optional, advanced)

## User Management
- [x] `User` class implementation (attributes: id, username, password_hash)
- [x] User registration logic
- [x] User login logic
- [x] Password hashing (e.g., using bcrypt)
- [x] Data persistence for users (e.g., JSON file)
- [ ] User roles/permissions (if needed, e.g., admin vs regular user)
- [ ] Password reset functionality

## Web Interface (Flask)
- [x] Basic Flask app setup (`app.py`)
- [x] Templates directory and basic HTML structure (`templates/index.html`)
- [x] Web interface for user registration
- [x] Web interface for user login
- [x] User session management (login/logout) - *Basic logout exists, needs secure session key*
- [ ] Web form for adding a new person to the tree
- [ ] Web form for adding a new relationship between people
- [ ] Display family tree data on the web page (list view initially)
- [ ] Interface for editing people/relationships
- [ ] Interface for deleting people/relationships
- [ ] Protect family tree modification routes (require login)
- [ ] Improve UI/UX (styling, layout, feedback messages)

## Data Management & Storage
- [x] Utility functions for loading/saving JSON data (`db_utils.py`)
- [ ] Consider switching to a database (SQLite, PostgreSQL) for larger trees
- [ ] Data validation (e.g., date formats, required fields)
- [ ] Backup and restore functionality

## Security
- [x] Password hashing
- [ ] Input validation and sanitization to prevent injection attacks
- [ ] Secure session management (e.g., Flask's secret key) - *Needs implementation*
- [ ] CSRF protection for forms

## Logging & Error Handling
- [x] Basic audit logging for user actions (registration, login)
- [ ] Expand audit logging for family tree modifications
- [ ] Implement robust error handling and user feedback

## Testing
- [x] Unit tests for `Person` class
- [x] Unit tests for `Relationship` class
- [x] Unit tests for `FamilyTree` class
- [x] Unit tests for `User` class
- [x] Unit tests for `UserManagement`
- [ ] Integration tests for web endpoints
- [ ] Test edge cases and error conditions

## Documentation
- [x] Basic `README.md`
- [ ] Add usage instructions to `README.md`
- [ ] Document code with comments and docstrings
- [ ] User guide (optional)

## Deployment
- [ ] Choose a deployment platform (e.g., Heroku, PythonAnywhere)
- [ ] Configure production environment (e.g., Gunicorn, environment variables)
- [ ] Setup instructions for deployment
